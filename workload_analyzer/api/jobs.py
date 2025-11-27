"""Job management API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..exceptions import (
    FileServiceError,
    ISSAuthenticationError,
    ISSClientError,
    ISSNotFoundError,
)
from ..models.job_models import JobDetail, JobRequest, JobStatus, JobType, ISSJobsResponse
from ..models.response_models import (
    ErrorResponse,
    FileListResponse,
    JobDetailResponse,
)
from ..services.file_service import FileService
from ..services.iss_client import ISSClient
from ..utils.response_summarizer import summarize_jobs_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def get_bearer_token(authorization: str = Header(...)) -> str:
    """Extract and validate bearer token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Bearer token
        
    Raises:
        HTTPException: If token format is invalid
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )
    return authorization[7:]  # Remove "Bearer " prefix


async def get_iss_client(
    bearer_token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings)
) -> ISSClient:
    """Dependency to get ISS client with bearer token."""
    return ISSClient(settings, bearer_token)


async def get_file_service(
    bearer_token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings),
    iss_client: ISSClient = Depends(get_iss_client)
) -> FileService:
    """Dependency to get file service with bearer token."""
    return FileService(settings, bearer_token, iss_client)


@router.get(
    "",
    response_model=ISSJobsResponse,
    summary="List jobs",
    description="Get a paginated list of jobs with ISS API compatible parameters.",
)
async def list_jobs(
    limit: int = Query(100, ge=1, le=100, description="Maximum number of jobs to return"),
    job_status: Optional[JobStatus] = Query(None, alias="status", description="Filter by job status"),
    job_request_id: Optional[str] = Query(None, description="Filter by specific job request ID"),
    job_type: Optional[str] = Query(
        None, 
        description="Filter jobs by type (comma-separated for multiple). "
                   "Valid values: IWPS, ISIM, Coho, NovaCoho, Instance, WorkloadJob, WorkloadJobROI, Custom"
    ),
    queue: Optional[str] = Query(None, description="Filter jobs by queue"),
    requested_by: Optional[str] = Query(None, description="Filter jobs by requesting user"),
    parent_instance_id: Optional[str] = Query(None, description="Filter jobs by parent instance ID"),
    workload_job_roi_id: Optional[str] = Query(None, description="Filter jobs by workload job ROI ID"),
    continuation_token: Optional[str] = Query(None, description="Token for pagination continuation"),
    summarize: bool = Query(False, description="If true, return summarized job data (reduced context for LLM)"),
    iss_client: ISSClient = Depends(get_iss_client),
):
    """List jobs with filtering and pagination matching ISS API spec."""
    logger.info(f"📋 Listing jobs: limit={limit}, status={job_status}, job_type={job_type}, queue={queue}, summarize={summarize}")
    
    try:
        # Validate job_type parameter if provided
        if job_type:
            job_types = [jt.strip() for jt in job_type.split(',') if jt.strip()]
            valid_job_types = [jt.value for jt in JobType]
            invalid_types = [jt for jt in job_types if jt not in valid_job_types]
            
            if invalid_types:
                logger.warning(f"Invalid job types provided: {invalid_types}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid job type(s): {', '.join(invalid_types)}. "
                           f"Valid types are: {', '.join(valid_job_types)}"
                )
        async with iss_client:
            iss_response = await iss_client.get_jobs(
                limit=limit,
                status=job_status,
                job_request_id=job_request_id,
                job_type=job_type,
                queue=queue,
                requested_by=requested_by,
                parent_instance_id=parent_instance_id,
                workload_job_roi_id=workload_job_roi_id,
                continuation_token=continuation_token,
            )

        # Optionally summarize response for LLM context efficiency
        if summarize:
            logger.info(f"Summarizing {len(iss_response.jobs)} jobs for LLM context efficiency")
            summarized = summarize_jobs_response(
                {
                    'jobs': [job.dict() for job in iss_response.jobs],
                    'continuation_token': iss_response.continuation_token
                },
                max_jobs=50
            )
            # Convert back to ISSJobsResponse
            iss_response = ISSJobsResponse(
                jobs=[JobRequest(**job) for job in summarized['jobs']],
                count=summarized['count'],
                continuation_token=summarized.get('continuation_token')
            )

        # Return the ISS API response
        return iss_response

    except ISSAuthenticationError as e:
        logger.error(f"Authentication error listing jobs: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except HTTPException:
        # Re-raise HTTPException without modification
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="Get job details",
    description="Get detailed information about a specific job.",
)
async def get_job(
    job_id: str,
    iss_client: ISSClient = Depends(get_iss_client),
):
    """Get detailed job information."""
    logger.info(f"🔍 Getting job details: {job_id}")
    try:
        async with iss_client:
            # Get main job details
            job = await iss_client.get_job(job_id)

            # Initialize response
            response = JobDetailResponse(job=job)

        return response

    except ISSNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )
    except ISSAuthenticationError as e:
        logger.error(f"Authentication error getting job {job_id}: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error getting job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except HTTPException:
        # Re-raise HTTPException without modification
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{job_id}/files",
    response_model=FileListResponse,
    summary="List job files",
    description="Get a list of files associated with a job.",
)
async def list_job_files(
    job_id: str,
    file_service: FileService = Depends(get_file_service),
    iss_client: ISSClient = Depends(get_iss_client),
):
    """List files for a specific job."""
    logger.info(f"📁 Listing files for job: {job_id}")
    try:
        # Keep ISS client open for the entire operation to obtain the tenant_id.
        # The ISS client connection is kept alive during file_service operations
        # for consistency and potential future enhancements to connection pooling.
        async with iss_client:
            job = await iss_client.get_job(job_id)
            
            async with file_service:
                files = await file_service.list_files(
                    tenant=job.tenant_id, job_id=job_id, path=""
                )

        return FileListResponse(
            files=files,
            total_files=len(files),
            job_id=job_id,
        )

    except FileServiceError as e:
        logger.error(f"File service error listing files for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"File service error: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing files for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{job_id}/files/{filename}",
    summary="Download job file",
    description="Download a specific file from a job.",
)
async def download_job_file(
    job_id: str,
    filename: str,
    file_service: FileService = Depends(get_file_service),
    iss_client: ISSClient = Depends(get_iss_client),
):
    """Download a file from a job."""
    logger.info(f"⬇️ Downloading file: {filename} from job: {job_id}")
    try:
        # Keep ISS client open for the entire operation to obtain the tenant_id.
        # The ISS client connection is kept alive during file_service operations
        # to support connection pooling and in case file_service needs to query ISS
        # (e.g., in get_artifact_type() for determining job classification).
        async with iss_client:
            job = await iss_client.get_job(job_id)
            
            async with file_service:
                # Generate download URL (redirect to file service)
                response = await file_service.download_file(
                    tenant=job.tenant_id,
                    job_id=job_id,
                    file_path=filename,
                )

                if type(response) == bytes:
                    response = {"file_content": response.decode('utf-8')}
                
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=response,
                )

    except FileServiceError as e:
        logger.error(
            f"File service error downloading {filename} for job {job_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"File service error: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error downloading {filename} for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
