"""Platform-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class PlatformType(str, Enum):
    """Supported platform types."""

    SIMULATION = "Simulation"
    EMULATION = "Emulation"
    HARDWARE = "Hardware"
    VIRTUAL = "Virtual"
    HYBRID = "Hybrid"


class TraceConfig(BaseModel):
    """Trace configuration for platform."""

    enabled: bool = False
    trace_type: Optional[str] = None
    sampling_rate: Optional[float] = Field(None, ge=0, le=1)
    buffer_size_mb: Optional[int] = Field(None, gt=0)
    output_format: Optional[str] = "json"

    class Config:
        extra = "allow"


class FuseConfig(BaseModel):
    """FUSE configuration for platform."""

    enabled: bool = False
    mount_point: Optional[str] = None
    cache_size_mb: Optional[int] = Field(None, gt=0)
    cache_timeout_seconds: Optional[int] = Field(None, gt=0)

    class Config:
        extra = "allow"


class PlatformDefaults(BaseModel):
    """Default configuration values for platform."""

    default_timeout_minutes: Optional[int] = Field(None, gt=0)
    default_memory_gb: Optional[float] = Field(None, gt=0)
    default_cpu_count: Optional[int] = Field(None, gt=0)
    default_disk_gb: Optional[float] = Field(None, gt=0)

    # Boot configuration
    default_boot_profile: Optional[str] = None
    boot_timeout_minutes: Optional[int] = Field(None, gt=0)

    # Networking
    default_network_config: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class PlatformFeatures(BaseModel):
    """Platform feature capabilities."""

    # Simulation features
    supports_checkpoint: bool = False
    supports_migration: bool = False
    supports_scaling: bool = False
    supports_snapshots: bool = False

    # Hardware features
    supports_gpu: bool = False
    supports_fpga: bool = False
    supports_networking: bool = False
    supports_storage: bool = False

    # Virtualization features
    supports_containers: bool = False
    supports_vms: bool = False
    supports_nested_virtualization: bool = False

    # Debugging features
    supports_debugging: bool = False
    supports_profiling: bool = False
    supports_tracing: bool = False

    # Custom features
    custom_features: Optional[Dict[str, bool]] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class BootProfile(BaseModel):
    """Boot profile configuration."""

    name: str
    description: Optional[str] = None
    boot_sequence: Optional[List[str]] = Field(default_factory=list)
    kernel_version: Optional[str] = None
    initrd_path: Optional[str] = None
    kernel_args: Optional[List[str]] = Field(default_factory=list)

    # Boot timing
    boot_timeout_minutes: Optional[int] = Field(None, gt=0)
    expected_boot_time_seconds: Optional[int] = Field(None, gt=0)

    # Boot verification
    boot_verification_command: Optional[str] = None
    boot_success_pattern: Optional[str] = None

    class Config:
        extra = "allow"


class Platform(BaseModel):
    """Platform definition model."""

    # Basic information
    platform_id: str = Field(..., description="Unique platform identifier")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    platform_type: PlatformType
    version: Optional[str] = None

    # Status and availability
    is_active: bool = True
    is_available: bool = True
    maintenance_mode: bool = False

    # Resource specifications
    max_cpu_count: Optional[int] = Field(None, gt=0)
    max_memory_gb: Optional[float] = Field(None, gt=0)
    max_disk_gb: Optional[float] = Field(None, gt=0)
    max_gpu_count: Optional[int] = Field(None, ge=0)
    max_concurrent_jobs: Optional[int] = Field(None, gt=0)

    # Configuration
    features: Optional[PlatformFeatures] = None
    defaults: Optional[PlatformDefaults] = None
    boot_profiles: Optional[List[BootProfile]] = Field(default_factory=list)

    # Advanced configuration
    trace_config: Optional[TraceConfig] = None
    fuse_config: Optional[FuseConfig] = None

    # Metadata
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)
    owner: Optional[str] = None
    created_by: Optional[str] = None

    # Timing information
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    last_used: Optional[datetime] = None

    # Location and access
    location: Optional[str] = None
    access_url: Optional[str] = None
    documentation_url: Optional[str] = None

    @validator("platform_id")
    def validate_platform_id(cls, v):
        # Allow alphanumeric characters with hyphens, underscores, and dots
        # This supports ISS API platform IDs that include version numbers with dots
        if not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError(
                "Platform ID must be alphanumeric with hyphens, underscores, and dots"
            )
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


class Instance(BaseModel):
    """Platform instance model."""

    # Basic information
    instance_id: str = Field(..., description="Unique instance identifier")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    platform_id: str
    platform_name: Optional[str] = None

    # Status information
    status: str = "Unknown"
    is_active: bool = True
    is_available: bool = True
    in_use: bool = False

    # Resource allocation
    allocated_cpu_count: Optional[int] = Field(None, gt=0)
    allocated_memory_gb: Optional[float] = Field(None, gt=0)
    allocated_disk_gb: Optional[float] = Field(None, gt=0)
    allocated_gpu_count: Optional[int] = Field(None, ge=0)

    # Current usage
    current_cpu_usage_percent: Optional[float] = Field(None, ge=0, le=100)
    current_memory_usage_gb: Optional[float] = Field(None, ge=0)
    current_disk_usage_gb: Optional[float] = Field(None, ge=0)

    # Configuration
    boot_profile: Optional[str] = None
    network_config: Optional[Dict[str, Any]] = None
    storage_config: Optional[Dict[str, Any]] = None

    # Job assignment
    current_job_id: Optional[str] = None
    current_job_name: Optional[str] = None
    job_count_today: Optional[int] = Field(None, ge=0)
    job_count_total: Optional[int] = Field(None, ge=0)

    # Timing information
    created_at: Optional[datetime] = None
    last_boot_time: Optional[datetime] = None
    last_used: Optional[datetime] = None
    uptime_hours: Optional[float] = Field(None, ge=0)

    # Health and monitoring
    health_status: Optional[str] = "Unknown"
    last_health_check: Optional[datetime] = None
    error_message: Optional[str] = None

    # Access information
    access_url: Optional[str] = None
    ssh_endpoint: Optional[str] = None
    vnc_endpoint: Optional[str] = None

    # Metadata
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)
    owner: Optional[str] = None

    @validator("instance_id")
    def validate_instance_id(cls, v):
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Instance ID must be alphanumeric with hyphens/underscores"
            )
        return v

    class Config:
        extra = "allow"
        json_encoders = {datetime: lambda dt: dt.isoformat()}
