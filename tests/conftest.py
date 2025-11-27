"""Test configuration and fixtures."""

import asyncio
import logging
import pytest
import warnings
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

# Suppress logging errors that occur during test teardown from third-party libraries
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("auto_bedrock_chat_fastapi").setLevel(logging.CRITICAL)

from workload_analyzer.main import app
from workload_analyzer.config import Settings
from workload_analyzer.models.job_models import JobDetail, JobRequest, JobStatus, JobType, ISSJobsResponse
from workload_analyzer.models.response_models import JobDetailResponse, FileListResponse


@pytest.fixture
def mock_settings() -> Settings:
    """Mock settings for testing."""
    return Settings(
        # ISS API Configuration
        iss_api_url="https://api-test.workloadmgr.intel.com",
        iss_environment="test",
        auth_domain="https://azad.auth.us-west-2.amazoncognito.com/oauth2/token",
        client_secret_name="test/cognito/client_creds/services-backend",
        
        # AWS Configuration
        aws_access_key_id_iss="AKIA_TEST_ISS",
        aws_secret_access_key_iss="test-secret-iss",
        aws_region_iss="us-west-2",
        aws_access_key_id="AKIA_TEST_BEDROCK",
        aws_secret_access_key="test-secret-bedrock",
        aws_region="us-east-1",
        
        # Bedrock Configuration
        bedrock_model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        bedrock_temperature=0.7,
        bedrock_max_tokens=4096,
        bedrock_timeout=180,
        bedrock_system_prompt="Test system prompt",
        bedrock_allowed_paths=["/api/v1/jobs", "/health"],
        bedrock_excluded_paths=["/bedrock-chat", "/docs"],
        bedrock_max_tool_calls=10,
        bedrock_max_sessions=100,
        bedrock_session_timeout=3600,
        
        # Application Configuration
        app_env="test",
        api_version="v1",
        api_prefix="/api",
        
        # CORS Configuration  
        allowed_origins=["http://localhost:8000"],
        allowed_methods="GET,POST",
        allowed_headers="*",
        
        # Logging Configuration
        log_level="DEBUG",
        request_logging=True,
        enable_metrics=True,
        
        # Security Configuration
        jwt_secret_key="test-secret-key",
        rate_limit_per_minute=60,
        force_https=False,
        
        # Development Configuration
        debug=True,
        enable_docs=True,
        dev_mode=True,
        mock_iss_api=True,
    )


@pytest.fixture
def app_client() -> TestClient:
    """Test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def async_app_client():
    """Async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_job_data() -> JobRequest:
    """Sample job data for testing."""
    return JobRequest(
        JobRequestID="a1234567-89ab-cdef-0123-456789abcdef",
        Name="Test IWPS Job",
        description="A test job for unit testing",
        Type=JobType.IWPS,
        JobRequestStatus=JobStatus.INPROGRESS,
        PlatformID="test-platform-001",
        owner="test-user@intel.com",
        priority=5,
        tags={"environment": "test", "team": "validation"},
        max_runtime_minutes=120,
        project="test-project"
    )


@pytest.fixture
def sample_iss_jobs_response() -> dict:
    """Sample ISS jobs response for API testing."""
    return {
        "jobs": [
            {
                "JobRequestID": "a1234567-89ab-cdef-0123-456789abcdef",
                "Name": "Test IWPS Job",
                "Type": "IWPS",
                "JobRequestStatus": "inprogress",
                "RequestedOn": datetime.utcnow().isoformat(),
                "owner": "test-user@intel.com"
            },
            {
                "JobRequestID": "b1234567-89ab-cdef-0123-456789abcdef",
                "Name": "Test ISIM Job", 
                "Type": "ISIM",
                "JobRequestStatus": "inprogress",
                "RequestedOn": datetime.utcnow().isoformat(),
                "owner": "test-user2@intel.com"
            }
        ],
        "count": 2,
        "continuation_token": "2025-11-06T07:24:51.298Z..."
    }


@pytest.fixture
def sample_file_list() -> List[str]:
    """Sample file list for testing."""
    return [
        "sim.bbprofile",
        "sim.branchprofile",
        "sim.funcprofile", 
        "sim.insprofile",
        "sim.memprofile",
        "sim.out",
        "sim.stdout",
        "sim.summary.profile"
    ]


@pytest.fixture
def sample_instance_data() -> Dict[str, Any]:
    """Sample instance data for testing."""
    return {
        "instance_id": "instance-001",
        "name": "Test Instance 1",
        "description": "Test instance for unit testing",
        "platform_id": "platform-001",
        "platform_name": "Test Simulation Platform",
        "status": "Running",
        "is_active": True,
        "is_available": True,
        "in_use": False,
        "allocated_cpu_count": 16,
        "allocated_memory_gb": 64.0,
        "current_cpu_usage_percent": 25.5,
        "current_memory_usage_gb": 32.1,
        "health_status": "Healthy",
        "created_at": datetime.utcnow().isoformat(),
        "last_health_check": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_job_detail() -> JobDetail:
    """Sample job detail object for testing."""
    return JobDetail(
        JobRequestID="a1234567-89ab-cdef-0123-456789abcdef",
        Name="Test IWPS Job", 
        description="A test job for unit testing",
        Type=JobType.IWPS,
        JobRequestStatus=JobStatus.INPROGRESS,
        PlatformID="test-platform-001",
        owner="test-user@intel.com",
        priority=5,
        tags={"environment": "test", "team": "validation"},
        max_runtime_minutes=120,
        project="test-project",
        # Additional JobDetail-specific fields
        RequestedOn=datetime.utcnow().isoformat(),
        LastUpdatedOn=datetime.utcnow().isoformat(),
        actual_runtime_minutes=45.5,
        exit_code=0,
        tenant_id="test-tenant"  # Tenant ID for multi-tenant support
    )


@pytest.fixture
def mock_auth_service():
    """Mock authentication service."""
    mock = AsyncMock()
    from workload_analyzer.services.auth_service import Credentials
    mock.get_iss_credentials.return_value = Credentials(
        client_id="test_client",
        client_secret="test_secret"
    )
    mock.authenticate.return_value = True
    return mock


@pytest.fixture
def mock_iss_client(sample_iss_jobs_response, sample_job_data):
    """Mock ISS client for testing."""
    mock = AsyncMock()
    
    # Mock job operations  
    mock.get_jobs.return_value = sample_iss_jobs_response
    mock.get_job.return_value = sample_job_data
    mock.get_job_schema.return_value = {"type": "object", "properties": {}}
    
    # Mock context manager
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = None
    
    return mock


@pytest.fixture  
def mock_file_service(sample_file_list):
    """Mock file service for testing."""
    mock = AsyncMock()
    
    mock.list_files.return_value = sample_file_list
    mock.download_file.return_value = b"test file content"
    mock.file_exists.return_value = True
    
    # Mock context manager
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = None
    
    return mock


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client for testing."""
    mock = AsyncMock()
    
    mock.chat_completion.return_value = {
        "content": "Test AI response about workload analysis",
        "tool_calls": [],
        "metadata": {"model": "claude-4.5", "usage": {"tokens": 100}}
    }
    
    mock.health_check.return_value = {
        "status": "healthy",
        "model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    }
    
    return mock


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_jobs_list(sample_job_data) -> List[JobDetail]:
    """Sample list of jobs for testing."""
    jobs = []
    for i in range(5):
        job_data = sample_job_data.copy()
        job_data["job_id"] = f"a{i:08d}-1234-5678-9012-123456789012"
        job_data["name"] = f"Test Job {i+1}"
        job_data["actual_runtime_minutes"] = 30 + (i * 10)
        job_data["peak_cpu_usage_percent"] = 60 + (i * 5)
        jobs.append(JobDetail(**job_data))
    return jobs


@pytest.fixture(scope="session", autouse=True)
def cleanup_asyncio():
    """Clean up asyncio resources after test session."""
    yield
    # Suppress ResourceWarnings for unclosed aiohttp sessions from third-party libraries
    warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*ClientSession.*")
    warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*event loop.*")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()