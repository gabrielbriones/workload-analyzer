"""Platform management API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status

from ..config import Settings, get_settings
from ..exceptions import (
    ISSAuthenticationError,
    ISSClientError,
    ISSNotFoundError,
)
from ..models.platform_models import Platform
from ..models.response_models import (
    PlatformDetailResponse,
    PlatformListResponse,
)
from ..services.iss_client import ISSClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platforms", tags=["platforms"])


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


@router.get(
    "",
    response_model=PlatformListResponse,
    summary="Get list of platforms",
    description="Retrieve a list of hardware platforms based on user permissions and filters",
)
async def list_platforms(
    PlatformType: Optional[str] = Query(
        None, description="Filter platforms by platform type", example="Simics"
    ),
    PlatformName: Optional[str] = Query(
        None, description="Filter platforms by exact platform name", example="cwf-ap"
    ),
    IWPS: Optional[bool] = Query(None, description="Filter platforms that support IWPS workloads"),
    ISIM: Optional[bool] = Query(None, description="Filter platforms that support ISIM workloads"),
    NovaIWPS: Optional[bool] = Query(None, description="Filter platforms that support Nova IWPS workloads"),
    Traces: Optional[bool] = Query(None, description="Filter platforms that support trace collection"),
    Instance: Optional[bool] = Query(None, description="Filter platforms that support instance workloads (non-IWPS)"),
    IWPSEnabled: Optional[bool] = Query(None, description="Filter platforms with IWPS support enabled"),
    NovaCoho: Optional[bool] = Query(None, description="Filter platforms that support Nova Coho workloads"),
    iss_client: ISSClient = Depends(get_iss_client),
):
    """Retrieve a list of hardware platforms based on user permissions and filters."""
    try:
        # Build query parameters to pass through to ISS API
        query_params = {}
        
        # Add ISS API query parameters if provided
        if PlatformType is not None:
            query_params["PlatformType"] = PlatformType
        if PlatformName is not None:
            query_params["PlatformName"] = PlatformName
        if IWPS is not None:
            query_params["IWPS"] = IWPS
        if ISIM is not None:
            query_params["ISIM"] = ISIM
        if NovaIWPS is not None:
            query_params["NovaIWPS"] = NovaIWPS
        if Traces is not None:
            query_params["Traces"] = Traces
        if Instance is not None:
            query_params["Instance"] = Instance
        if IWPSEnabled is not None:
            query_params["IWPSEnabled"] = IWPSEnabled
        if NovaCoho is not None:
            query_params["NovaCoho"] = NovaCoho

        async with iss_client:
            # Pass all query parameters through to ISS API
            response = await iss_client.get_platforms(query_params)
            logger.debug(f"Response keys: {response.keys()}")

        # Handle different response formats from ISS API
        platforms_data = response.get("Platforms", response.get("platforms", []))
        
        # Process platforms data to ensure it matches our Platform model
        processed_platforms = []
        for platform_data in platforms_data:
            try:
                if isinstance(platform_data, dict):
                    # Map ISS API field names to our model field names
                    mapped_data = {}
                    
                    # Required field mappings
                    mapped_data["platform_id"] = platform_data.get("PlatformID", "")
                    mapped_data["name"] = platform_data.get("PlatformName", "")
                    
                    # Map platform type from ISS to our enum
                    iss_platform_type = platform_data.get("PlatformType", "")
                    if iss_platform_type == "Simics":
                        mapped_data["platform_type"] = "Simulation"
                    else:
                        # Default mapping for unknown types
                        mapped_data["platform_type"] = "Virtual"
                    
                    # Optional field mappings
                    mapped_data["description"] = platform_data.get("Description")
                    mapped_data["version"] = platform_data.get("SimicsPlatformVersion") or platform_data.get("SimicsPlatformRelease")
                    
                    # Map features if available
                    if "Features" in platform_data:
                        features = platform_data["Features"]
                        mapped_data["is_available"] = True  # Default to available
                        # Map IWPS enabled status
                        if "iwps_enabled" in features:
                            mapped_data["tags"] = {"iwps_enabled": str(features["iwps_enabled"])}
                    
                    # Memory mapping
                    if "PlatformMemorySize" in platform_data:
                        mapped_data["max_memory_gb"] = float(platform_data["PlatformMemorySize"])
                    
                    # Set reasonable defaults for required fields
                    mapped_data.setdefault("is_active", True)
                    mapped_data.setdefault("is_available", True)
                    mapped_data.setdefault("maintenance_mode", False)
                    
                    platform = Platform(**mapped_data)
                    processed_platforms.append(platform)
                else:
                    # If already a Platform instance, use it directly
                    processed_platforms.append(platform_data)
            except Exception as e:
                logger.warning(f"Failed to process platform data from {platform_data}: {e}")
                continue
        
        # Return ISS response structure
        return PlatformListResponse(
            platforms=processed_platforms,
        )

    except ISSAuthenticationError as e:
        logger.error(f"Authentication error listing platforms: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error listing platforms: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error listing platforms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{platform_id}",
    response_model=PlatformDetailResponse,
    summary="Get platform details",
    description="Get detailed information about a specific platform.",
)
async def get_platform(
    platform_id: str,
    iss_client: ISSClient = Depends(get_iss_client),
):
    """Get detailed platform information."""
    try:
        async with iss_client:
            # Get main platform details
            platform = await iss_client.get_platform(platform_id)

            # Return basic platform response
            return PlatformDetailResponse(platform=platform)

    except ISSNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform {platform_id} not found",
        )
    except ISSAuthenticationError as e:
        logger.error(f"Authentication error getting platform {platform_id}: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error getting platform {platform_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error getting platform {platform_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
