"""Job-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class JobType(str, Enum):
    """Supported job types in ISS."""

    IWPS = "IWPS"
    ISIM = "ISIM"
    COHO = "Coho"
    NOVA_COHO = "NovaCoho"
    INSTANCE = "Instance"
    WORKLOAD_JOB = "WorkloadJob"
    WORKLOAD_JOB_ROI = "WorkloadJobROI"
    CUSTOM = "Custom"


class JobStatus(str, Enum):
    """Job request status values as defined by ISS API."""

    REQUESTED = "requested"
    QUEUED = "queued"
    ALLOCATING = "allocating"
    ALLOCATED = "allocated"
    BOOTING = "booting"
    INPROGRESS = "inprogress"
    CHECKPOINTING = "checkpointing"
    DONE = "done"
    ERROR = "error"
    RELEASING = "releasing"
    RELEASED = "released"
    COMPLETE = "complete"


class SubStates(BaseModel):
    """Job sub-states for detailed status tracking."""

    state: Optional[str] = None
    sub_state: Optional[str] = None
    detailed_state: Optional[str] = None
    progress_percentage: Optional[float] = Field(None, ge=0, le=100)

    class Config:
        extra = "allow"


class Authentication(BaseModel):
    """Authentication configuration for job execution."""

    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    auth_type: Optional[str] = "password"

    class Config:
        extra = "allow"


class Cumulus(BaseModel):
    """Cumulus configuration for job execution."""

    enabled: bool = False
    config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(None, ge=1, le=10)

    class Config:
        extra = "allow"


class Allocation(BaseModel):
    """Resource allocation configuration."""

    cpu_count: Optional[int] = Field(None, gt=0)
    memory_gb: Optional[float] = Field(None, gt=0)
    disk_gb: Optional[float] = Field(None, gt=0)
    gpu_count: Optional[int] = Field(None, ge=0)
    node_count: Optional[int] = Field(None, gt=0)

    class Config:
        extra = "allow"


class Execution(BaseModel):
    """Job execution configuration."""

    timeout_minutes: Optional[int] = Field(None, gt=0)
    retry_count: Optional[int] = Field(None, ge=0)
    environment_variables: Optional[Dict[str, str]] = None
    working_directory: Optional[str] = None
    command_line_args: Optional[List[str]] = None

    class Config:
        extra = "allow"


class ExecutionParameters(BaseModel):
    """Comprehensive execution parameters for jobs."""

    allocation: Optional[Allocation] = None
    execution: Optional[Execution] = None
    cumulus: Optional[Cumulus] = None
    authentication: Optional[Authentication] = None
    custom_parameters: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class TestCase(BaseModel):
    """Test case configuration for workload jobs."""

    name: str
    description: Optional[str] = None
    test_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    expected_runtime_minutes: Optional[int] = Field(None, gt=0)

    class Config:
        extra = "allow"


class Workload(BaseModel):
    """Workload definition with test cases."""

    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    test_cases: List[TestCase] = Field(default_factory=list)
    global_parameters: Optional[Dict[str, Any]] = None

    @validator("test_cases")
    def validate_test_cases(cls, v):
        if not v:
            raise ValueError("At least one test case is required")
        return v

    class Config:
        extra = "allow"


class JobRequest(BaseModel):
    """Base job request model."""

    job_id: Optional[str] = Field(None, alias="JobRequestID", description="Unique job identifier")
    name: str = Field(..., alias="Name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    job_type: JobType = Field(..., alias="Type")
    platform_id: Optional[str] = Field(None, alias="PlatformID")
    instance_id: Optional[str] = None

    # Status information
    status: Optional[JobStatus] = Field(None, alias="JobRequestStatus")

    # Job configuration
    workload: Optional[Workload] = None
    execution_parameters: Optional[ExecutionParameters] = None

    # Metadata
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)
    priority: Optional[int] = Field(1, ge=1, le=10)
    owner: Optional[str] = None
    project: Optional[str] = None

    # Scheduling
    scheduled_start: Optional[datetime] = None
    max_runtime_minutes: Optional[int] = Field(None, gt=0)

    @validator("job_id")
    def validate_job_id(cls, v):
        # Job IDs are UUIDs and don't need to start with 'a'
        return v

    @validator("tags")
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError("Maximum 20 tags allowed")
        for key, value in (v or {}).items():
            if len(key) > 50 or len(value) > 200:
                raise ValueError("Tag key max 50 chars, value max 200 chars")
        return v

    class Config:
        extra = "allow"
        json_encoders = {datetime: lambda dt: dt.isoformat()}
        allow_population_by_field_name = True


class JobDetail(JobRequest):
    """Detailed job information including runtime data."""

    # Status information
    status: JobStatus = Field(..., alias="JobRequestStatus")
    sub_states: Optional[SubStates] = Field(None, alias="SubStates")

    # Timing information  
    created_at: Optional[datetime] = Field(None, alias="RequestedOn")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: Optional[datetime] = Field(None, alias="LastUpdatedOn")

    # Execution details
    actual_runtime_minutes: Optional[float] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = Field(None, alias="JobRequestStatusDetails")

    # Resource usage
    actual_allocation: Optional[Allocation] = Field(None, alias="Allocation")
    peak_memory_usage_gb: Optional[float] = None
    peak_cpu_usage_percent: Optional[float] = Field(None, ge=0, le=100)

    # File references
    input_files: Optional[List[str]] = Field(default_factory=list)
    output_files: Optional[List[str]] = Field(default_factory=list)
    log_files: Optional[List[str]] = Field(default_factory=list)

    # Platform information
    platform_name: Optional[str] = Field(None, alias="PlatformName")
    instance_name: Optional[str] = None
    node_assignments: Optional[List[str]] = Field(default_factory=list)

    class Config:
        extra = "allow"
        json_encoders = {datetime: lambda dt: dt.isoformat()}
        allow_population_by_field_name = True


class ISSJobsResponse(BaseModel):
    """Response from ISS API jobs endpoint."""

    jobs: List[JobRequest]
    count: int
    continuation_token: Optional[str] = None

    class Config:
        extra = "allow"
