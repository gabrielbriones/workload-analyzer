"""
Configuration management for Workload Analyzer.

This module handles all configuration settings, environment variables,
and application initialization parameters.
"""

import os
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # Application Settings
    app_name: str = Field(default="Workload Analyzer", env="APP_NAME")
    app_version: str = Field(default="0.1.0", env="APP_VERSION")
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")

    # API Configuration
    api_prefix: str = Field(default="/api", env="API_PREFIX")
    api_version: str = Field(default="v1", env="API_VERSION")

    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # ISS API Configuration
    iss_base_url: str = Field(
        default="https://api-test.workloadmgr.intel.com", env="ISS_BASE_URL"
    )
    iss_api_url: str = Field(
        default="https://api-test.workloadmgr.intel.com", env="ISS_API_URL"
    )
    iss_file_service_url: str = Field(
        default="https://gw-extval-test.workloadmgr.intel.com",
        env="ISS_FILE_SERVICE_URL",
    )
    iss_secret_name: str = Field(
        default="workload-analyzer/iss-credentials", env="ISS_SECRET_NAME"
    )
    auth_domain: str = Field(default="your-auth-domain.intel.com", env="AUTH_DOMAIN")
    tenant_id: str = Field(default="extval", env="TENANT_ID")
    default_tenant: Optional[str] = Field(default=None, env="DEFAULT_TENANT")
    iss_timeout_seconds: int = Field(default=30, env="ISS_TIMEOUT_SECONDS")
    file_service_timeout_seconds: int = Field(default=30, env="FILE_SERVICE_TIMEOUT_SECONDS")

    # AWS Configuration for ISS
    client_secret_name: str = Field(
        default="iss/workload-analyzer/credentials", env="CLIENT_SECRET_NAME"
    )
    aws_access_key_id_iss: Optional[str] = Field(
        default=None, env="AWS_ACCESS_KEY_ID_ISS"
    )
    aws_secret_access_key_iss: Optional[str] = Field(
        default=None, env="AWS_SECRET_ACCESS_KEY_ISS"
    )
    aws_region_iss: str = Field(default="us-west-2", env="AWS_REGION_ISS")

    # AWS Configuration for Bedrock
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(
        default=None, env="AWS_SECRET_ACCESS_KEY"
    )
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")

    # Bedrock AI Configuration
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0", env="BEDROCK_MODEL_ID"
    )
    bedrock_temperature: float = Field(default=0.7, env="BEDROCK_TEMPERATURE")
    bedrock_max_tokens: int = Field(default=4096, env="BEDROCK_MAX_TOKENS")
    bedrock_system_prompt: Optional[str] = Field(
        default=None, env="BEDROCK_SYSTEM_PROMPT"
    )
    bedrock_allowed_paths: Union[List[str], str] = Field(
        default=[
            "/api/v1/platforms",
            "/api/v1/jobs",
            "/api/v1/instances",
        ]
    )
    bedrock_excluded_paths: Union[List[str], str] = Field(
        default=[
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/chat",
            "/ws",
            "/api/chat"
        ]
    )
    bedrock_max_tool_calls: int = Field(default=10, env="BEDROCK_MAX_TOOL_CALLS")
    bedrock_timeout: int = Field(default=30, env="BEDROCK_TIMEOUT")
    bedrock_max_sessions: int = Field(default=1000, env="BEDROCK_MAX_SESSIONS")
    bedrock_session_timeout: int = Field(default=3600, env="BEDROCK_SESSION_TIMEOUT")

    # Bedrock UI Configuration
    bedrock_ui_title: str = Field(default="AI Assistant", env="BEDROCK_UI_TITLE")
    bedrock_ui_welcome_message: str = Field(
        default="Welcome! I'm your AI assistant. I can help you interact with the API endpoints. Try asking me to retrieve data, create resources, or explain what operations are available.",
        env="BEDROCK_UI_WELCOME_MESSAGE"
    )

    # Security Configuration
    jwt_secret_key: str = Field(
        default="your-secret-key-here-change-in-production", env="JWT_SECRET_KEY"
    )
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    force_https: bool = Field(default=False, env="FORCE_HTTPS")

    # CORS Configuration
    allowed_origins: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    allowed_methods: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS", env="ALLOWED_METHODS"
    )
    allowed_headers: str = Field(default="*", env="ALLOWED_HEADERS")
    allowed_hosts: Union[List[str], str] = Field(
        default=["localhost", "127.0.0.1"], description="Allowed host headers for CORS"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    request_logging: bool = Field(default=True, env="REQUEST_LOGGING")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")

    # Intel Workload Specific Settings
    default_platform: str = Field(default="Intel-SPR-8380", env="DEFAULT_PLATFORM")
    default_simulation_timeout: int = Field(
        default=24, env="DEFAULT_SIMULATION_TIMEOUT"
    )
    cache_results_ttl: int = Field(default=168, env="CACHE_RESULTS_TTL")
    max_concurrent_simulations: int = Field(default=5, env="MAX_CONCURRENT_SIMULATIONS")
    max_simulations_per_tenant: int = Field(
        default=100, env="MAX_SIMULATIONS_PER_TENANT"
    )
    tenant_storage_limit_gb: int = Field(default=1000, env="TENANT_STORAGE_LIMIT_GB")

    # File Service Configuration
    file_download_timeout: int = Field(default=300, env="FILE_DOWNLOAD_TIMEOUT")
    max_file_size_mb: int = Field(default=500, env="MAX_FILE_SIZE_MB")
    cache_files_locally: bool = Field(default=True, env="CACHE_FILES_LOCALLY")
    file_service_tenant_urls: dict = Field(default={})

    # Development Settings
    enable_docs: bool = Field(default=True, env="ENABLE_DOCS")
    dev_mode: bool = Field(default=True, env="DEV_MODE")
    mock_iss_api: bool = Field(default=False, env="MOCK_ISS_API")
    maintenance_mode: bool = Field(default=False, env="MAINTENANCE_MODE")

    @field_validator("iss_file_service_url", mode="before")
    @classmethod
    def validate_file_service_url(cls, v):
        """Build file service URL based on tenant_id if not explicitly set."""
        # Note: In Pydantic v2, we can't access other field values in before mode
        # This validation is simplified for now
        return v

    @field_validator("aws_access_key_id_iss", mode="before")
    @classmethod
    def default_iss_access_key(cls, v):
        """Default ISS access key to main AWS access key if not set."""
        import os
        
        # If explicitly set via environment variable, use that
        if v is not None:
            return v
            
        # Otherwise, try to get the main AWS access key
        main_aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        if main_aws_key:
            return main_aws_key
            
        return None

    @field_validator("aws_secret_access_key_iss", mode="before")
    @classmethod
    def default_iss_secret_key(cls, v):
        """Default ISS secret key to main AWS secret key if not set."""
        import os
        
        # If explicitly set via environment variable, use that
        if v is not None:
            return v
            
        # Otherwise, try to get the main AWS secret key
        main_aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        if main_aws_secret:
            return main_aws_secret
            
        return None

    @field_validator("bedrock_allowed_paths", mode="before")
    @classmethod
    def parse_allowed_paths(cls, v):
        """Parse comma-separated allowed paths from environment or default."""
        import os

        env_val = os.getenv("BEDROCK_ALLOWED_PATHS")
        if env_val:
            if isinstance(env_val, str):
                return [path.strip() for path in env_val.split(",") if path.strip()]
        if isinstance(v, str):
            return [path.strip() for path in v.split(",") if path.strip()]
        return v

    @field_validator("bedrock_excluded_paths", mode="before")
    @classmethod
    def parse_excluded_paths(cls, v):
        """Parse comma-separated excluded paths from environment or default."""
        import os

        env_val = os.getenv("BEDROCK_EXCLUDED_PATHS")
        if env_val:
            if isinstance(env_val, str):
                return [path.strip() for path in env_val.split(",") if path.strip()]
        if isinstance(v, str):
            return [path.strip() for path in v.split(",") if path.strip()]
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Parse comma-separated allowed origins from environment or default."""
        import os

        env_val = os.getenv("ALLOWED_ORIGINS")
        if env_val:
            if isinstance(env_val, str):
                return [
                    origin.strip() for origin in env_val.split(",") if origin.strip()
                ]
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v, values):
        """Parse comma-separated allowed hosts."""
        # Check environment variable first
        import os

        env_val = os.getenv("ALLOWED_HOSTS")
        if env_val:
            if not env_val.strip():  # Handle empty string
                return ["localhost", "127.0.0.1"]  # Default values
            return [host.strip() for host in env_val.split(",") if host.strip()]

        # Otherwise use the provided value
        if isinstance(v, str):
            if not v.strip():  # Handle empty string
                return ["localhost", "127.0.0.1"]  # Default values
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @field_validator("file_service_tenant_urls", mode="before")
    @classmethod
    def parse_tenant_urls(cls, v):
        """Parse tenant URLs from environment or default."""
        import json
        import os

        env_val = os.getenv("FILE_SERVICE_TENANT_URLS")
        if env_val:
            try:
                return json.loads(env_val)
            except (json.JSONDecodeError, TypeError):
                return {}
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {}
        return v or {}

    @property
    def is_development(self) -> bool:
        """Check if the application is running in development mode."""
        return self.app_env.lower() in ["development", "dev", "test"]

    def get_file_service_url(self, tenant: str = None) -> str:
        """Get file service URL for specified tenant.

        Args:
            tenant: Tenant identifier (optional, uses default if not provided)

        Returns:
            File service base URL for the tenant
        """
        effective_tenant = tenant or self.get_effective_tenant()
        
        # Check if there's a specific URL for this tenant
        if effective_tenant in self.file_service_tenant_urls:
            return self.file_service_tenant_urls[effective_tenant]
        
        # Otherwise use the default ISS file service URL
        return self.iss_file_service_url

    def get_effective_tenant(self) -> str:
        """Get the effective tenant ID (default_tenant or tenant_id)."""
        return self.default_tenant or self.tenant_id

    def get_bedrock_system_prompt(self) -> str:
        """Get the effective system prompt for Bedrock AI."""
        if self.bedrock_system_prompt:
            return self.bedrock_system_prompt

        return f"""You are an expert Intel simulation workload analyst. 
Help users optimize their IWPS, ISIM, and Coho simulation jobs. 
You have read-only access to Intel Simulation Service (ISS) APIs and file services. 
Job IDs are UUIDs with 'a' prefix (e.g., a2290337-a3d4-40db-904d-79222997688f). 
Focus on performance analysis, configuration guidance, and troubleshooting. 
Always explain your reasoning and cite specific data when available.

Current configuration:
- Tenant: {self.get_effective_tenant()}
- Default Platform: {self.default_platform}
- Model: {self.bedrock_model_id}
"""


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings
