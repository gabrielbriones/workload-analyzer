"""Response models for API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .job_models import JobDetail, JobRequest
from .platform_models import Platform


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=1000)
    total_pages: int = Field(..., ge=0)
    has_next: bool = False
    has_previous: bool = False
    continuation_token: Optional[str] = Field(None, description="Token for next page of results")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: Optional[str] = None
    uptime_seconds: Optional[float] = None

    # Service status
    iss_api_status: str = "unknown"
    bedrock_status: str = "unknown"
    file_service_status: str = "unknown"

    # Performance metrics
    response_time_ms: Optional[float] = None
    active_connections: Optional[int] = None
    memory_usage_mb: Optional[float] = None

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class JobListResponse(BaseModel):
    """Response for job list endpoint."""

    jobs: List[JobRequest] = Field(default_factory=list)
    meta: PaginationMeta
    filters_applied: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "desc"


class JobDetailResponse(BaseModel):
    """Response for job detail endpoint."""

    job: JobDetail





class PlatformListResponse(BaseModel):
    """Response for platform list endpoint."""

    platforms: List[Platform] = Field(default_factory=list)


class PlatformDetailResponse(BaseModel):
    """Response for platform detail endpoint."""

    platform: Platform


class FileListResponse(BaseModel):
    """Response for file list endpoint."""

    files: List[str] = Field(default_factory=list)
    total_files: int = 0
    job_id: Optional[str] = None



