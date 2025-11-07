"""Instance management API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import Settings, get_settings
from ..exceptions import (
    ISSAuthenticationError,
    ISSClientError,
    ISSNotFoundError,
)
from ..models.response_models import (
    InstanceDetailResponse,
    InstanceListResponse,
    PaginationMeta,
)
from ..services.iss_client import ISSClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instances", tags=["instances"])


async def get_iss_client(settings: Settings = Depends(get_settings)) -> ISSClient:
    """Dependency to get ISS client."""
    from ..services.auth_service import AuthService

    auth_service = AuthService(settings)
    return ISSClient(settings, auth_service)


@router.get(
    "",
    response_model=InstanceListResponse,
    summary="List instances",
    description="Get a list of instances with optional filtering and pagination.",
)
async def list_instances(
    platform_id: Optional[str] = Query(None, description="Filter by platform ID"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    in_use: Optional[bool] = Query(None, description="Filter by usage status"),
    health_status: Optional[str] = Query(None, description="Filter by health status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    iss_client: ISSClient = Depends(get_iss_client),
):
    """List instances with filtering and pagination."""
    try:
        offset = (page - 1) * page_size

        async with iss_client:
            instances = await iss_client.get_instances(
                platform_id=platform_id,
                is_available=is_available,
                limit=page_size,
                offset=offset,
            )

        # Apply client-side filtering for fields not supported by ISS API
        if is_active is not None:
            instances = [i for i in instances if i.is_active == is_active]
        if in_use is not None:
            instances = [i for i in instances if i.in_use == in_use]
        if health_status:
            instances = [i for i in instances if i.health_status == health_status]

        # Calculate pagination metadata
        total = (
            len(instances) + offset
            if len(instances) == page_size
            else len(instances) + offset
        )
        total_pages = (total + page_size - 1) // page_size

        meta = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

        # Build filters applied
        filters_applied = {}
        if platform_id:
            filters_applied["platform_id"] = platform_id
        if is_available is not None:
            filters_applied["is_available"] = is_available
        if is_active is not None:
            filters_applied["is_active"] = is_active
        if in_use is not None:
            filters_applied["in_use"] = in_use
        if health_status:
            filters_applied["health_status"] = health_status

        # Calculate summary statistics
        available_count = len([i for i in instances if i.is_available])

        # Group instances by platform for summary
        platform_summary = {}
        if instances:
            platforms = {}
            for instance in instances:
                pid = instance.platform_id
                if pid not in platforms:
                    platforms[pid] = {
                        "platform_id": pid,
                        "platform_name": instance.platform_name,
                        "total_instances": 0,
                        "available_instances": 0,
                        "in_use_instances": 0,
                    }
                platforms[pid]["total_instances"] += 1
                if instance.is_available:
                    platforms[pid]["available_instances"] += 1
                if instance.in_use:
                    platforms[pid]["in_use_instances"] += 1

            platform_summary = {
                "platforms": list(platforms.values()),
                "total_platforms": len(platforms),
            }

        return InstanceListResponse(
            instances=instances,
            meta=meta,
            filters_applied=filters_applied if filters_applied else None,
            available_count=available_count,
            platform_summary=platform_summary,
        )

    except ISSAuthenticationError as e:
        logger.error(f"Authentication error listing instances: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error listing instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error listing instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{instance_id}",
    response_model=InstanceDetailResponse,
    summary="Get instance details",
    description="Get detailed information about a specific instance.",
)
async def get_instance(
    instance_id: str,
    include_platform: bool = Query(True, description="Include platform information"),
    include_current_job: bool = Query(True, description="Include current job details"),
    include_recent_jobs: bool = Query(True, description="Include recent job history"),
    include_metrics: bool = Query(True, description="Include performance metrics"),
    iss_client: ISSClient = Depends(get_iss_client),
):
    """Get detailed instance information."""
    try:
        async with iss_client:
            # Get main instance details
            instance = await iss_client.get_instance(instance_id)

            # Initialize response
            response = InstanceDetailResponse(instance=instance)

            # Get additional information if requested
            if include_platform and instance.platform_id:
                try:
                    platform = await iss_client.get_platform(instance.platform_id)
                    response.platform_info = platform
                except ISSNotFoundError:
                    logger.warning(
                        f"Platform {instance.platform_id} not found for instance {instance_id}"
                    )

            if include_current_job and instance.current_job_id:
                try:
                    current_job = await iss_client.get_job(instance.current_job_id)
                    response.current_job = current_job
                except ISSNotFoundError:
                    logger.warning(
                        f"Current job {instance.current_job_id} not found for instance {instance_id}"
                    )

            if include_recent_jobs:
                try:
                    # Get recent jobs that ran on this instance
                    # Note: This would require additional ISS API support for instance-specific job history
                    # For now, we'll get recent jobs from the same platform
                    recent_jobs = await iss_client.get_jobs(
                        platform_id=instance.platform_id, limit=10
                    )
                    # Filter to jobs that might have run on this instance (simplified)
                    response.recent_jobs = [
                        j for j in recent_jobs if j.instance_id == instance_id
                    ][:5]
                except Exception as e:
                    logger.warning(
                        f"Failed to get recent jobs for instance {instance_id}: {e}"
                    )

            if include_metrics:
                # Build performance metrics from instance data
                metrics = {
                    "current_status": instance.status,
                    "health_status": instance.health_status,
                    "uptime_hours": instance.uptime_hours,
                    "job_count_today": instance.job_count_today,
                    "job_count_total": instance.job_count_total,
                }

                # Resource utilization metrics
                if instance.allocated_cpu_count and instance.current_cpu_usage_percent:
                    metrics["cpu_utilization"] = {
                        "allocated_cores": instance.allocated_cpu_count,
                        "usage_percent": instance.current_cpu_usage_percent,
                        "available_cores": instance.allocated_cpu_count
                        * (100 - instance.current_cpu_usage_percent)
                        / 100,
                    }

                if instance.allocated_memory_gb and instance.current_memory_usage_gb:
                    metrics["memory_utilization"] = {
                        "allocated_gb": instance.allocated_memory_gb,
                        "used_gb": instance.current_memory_usage_gb,
                        "usage_percent": (
                            instance.current_memory_usage_gb
                            / instance.allocated_memory_gb
                        )
                        * 100,
                        "available_gb": instance.allocated_memory_gb
                        - instance.current_memory_usage_gb,
                    }

                if instance.allocated_disk_gb and instance.current_disk_usage_gb:
                    metrics["disk_utilization"] = {
                        "allocated_gb": instance.allocated_disk_gb,
                        "used_gb": instance.current_disk_usage_gb,
                        "usage_percent": (
                            instance.current_disk_usage_gb / instance.allocated_disk_gb
                        )
                        * 100,
                        "available_gb": instance.allocated_disk_gb
                        - instance.current_disk_usage_gb,
                    }

                # Availability metrics
                if instance.last_health_check:
                    from datetime import datetime, timezone

                    now = datetime.now(timezone.utc)
                    time_since_check = (
                        now - instance.last_health_check
                    ).total_seconds() / 60
                    metrics["health_check"] = {
                        "last_check_minutes_ago": time_since_check,
                        "status": instance.health_status,
                        "is_recent": time_since_check < 10,  # Less than 10 minutes ago
                    }

                response.performance_metrics = metrics

        return response

    except ISSNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )
    except ISSAuthenticationError as e:
        logger.error(f"Authentication error getting instance {instance_id}: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error getting instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error getting instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{instance_id}/jobs",
    summary="List instance jobs",
    description="Get job history for a specific instance.",
)
async def list_instance_jobs(
    instance_id: str,
    status: Optional[str] = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    iss_client: ISSClient = Depends(get_iss_client),
):
    """List jobs that have run on a specific instance."""
    try:
        async with iss_client:
            # Verify instance exists
            try:
                instance = await iss_client.get_instance(instance_id)
            except ISSNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Instance {instance_id} not found",
                )

            # Get jobs for the platform (ISS API doesn't support instance-specific filtering)
            from ..models.job_models import JobStatus

            job_status = JobStatus(status) if status else None

            all_jobs = await iss_client.get_jobs(
                platform_id=instance.platform_id,
                status=job_status,
                limit=200,  # Get more to filter
            )

            # Filter to jobs that ran on this specific instance
            instance_jobs = [j for j in all_jobs if j.instance_id == instance_id]

            # Apply pagination
            offset = (page - 1) * page_size
            jobs = instance_jobs[offset : offset + page_size]

        # Calculate pagination metadata
        total = len(instance_jobs)
        total_pages = (total + page_size - 1) // page_size

        meta = PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

        # Build filters applied
        filters_applied = {"instance_id": instance_id}
        if status:
            filters_applied["status"] = status

        from ..models.response_models import JobListResponse

        return JobListResponse(
            jobs=jobs,
            meta=meta,
            filters_applied=filters_applied,
            sort_by="created_at",
            sort_order="desc",
        )

    except HTTPException:
        raise
    except ISSAuthenticationError as e:
        logger.error(
            f"Authentication error listing jobs for instance {instance_id}: {e}"
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error listing jobs for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error listing jobs for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
