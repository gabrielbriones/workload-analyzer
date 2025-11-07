"""Test utilities and helpers."""

import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response


def mock_http_response(status_code: int = 200, json_data: Dict[str, Any] = None, text: str = None) -> Response:
    """Create a mock HTTP response."""
    response = MagicMock(spec=Response)
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text or ""
    response.headers = {}
    return response


def create_mock_job_response(job_count: int = 5) -> Dict[str, Any]:
    """Create mock job response data."""
    jobs = []
    for i in range(job_count):
        jobs.append({
            "job_id": f"a{i:08d}-1234-5678-9012-123456789012",
            "name": f"Mock Job {i+1}",
            "job_type": "IWPS",
            "status": "Completed" if i % 4 != 0 else "Failed",
            "platform_id": f"platform-{i % 2 + 1:03d}",
            "created_at": datetime.utcnow().isoformat(),
            "actual_runtime_minutes": 30 + (i * 10),
            "peak_cpu_usage_percent": 60 + (i * 5)
        })
    
    return {"jobs": jobs}


def create_mock_platform_response(platform_count: int = 3) -> Dict[str, Any]:
    """Create mock platform response data."""
    platforms = []
    for i in range(platform_count):
        platforms.append({
            "platform_id": f"platform-{i+1:03d}",
            "name": f"Mock Platform {i+1}",
            "platform_type": "Simulation",
            "is_active": True,
            "is_available": i % 2 == 0,  # Alternate availability
            "max_cpu_count": 32 + (i * 16),
            "max_memory_gb": 128.0 + (i * 64),
            "created_at": datetime.utcnow().isoformat()
        })
    
    return {"platforms": platforms}


def create_mock_instance_response(instance_count: int = 4) -> Dict[str, Any]:
    """Create mock instance response data."""
    instances = []
    for i in range(instance_count):
        instances.append({
            "instance_id": f"instance-{i+1:03d}",
            "name": f"Mock Instance {i+1}",
            "platform_id": f"platform-{(i % 2) + 1:03d}",
            "status": "Running",
            "is_active": True,
            "is_available": i % 3 != 0,  # Some unavailable
            "in_use": i % 4 == 0,  # Some in use
            "allocated_cpu_count": 8 + (i * 4),
            "allocated_memory_gb": 32.0 + (i * 16),
            "current_cpu_usage_percent": 20 + (i * 15),
            "health_status": "Healthy",
            "created_at": datetime.utcnow().isoformat()
        })
    
    return {"instances": instances}


class MockISSClient:
    """Mock ISS client for testing."""
    
    def __init__(self, settings=None, auth_service=None):
        self.settings = settings
        self.auth_service = auth_service
        self._closed = False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._closed = True
    
    async def get_jobs(self, **kwargs):
        """Mock get_jobs method."""
        from workload_analyzer.models.job_models import JobRequest, JobType, JobStatus
        
        jobs_data = create_mock_job_response()["jobs"]
        jobs = []
        
        for job_data in jobs_data:
            # Apply filters
            if kwargs.get("status") and JobStatus(job_data["status"]) != kwargs["status"]:
                continue
            if kwargs.get("job_type") and JobType(job_data["job_type"]) != kwargs["job_type"]:
                continue
            if kwargs.get("platform_id") and job_data["platform_id"] != kwargs["platform_id"]:
                continue
            
            job = JobRequest(**job_data)
            jobs.append(job)
            
            # Apply limit
            if kwargs.get("limit") and len(jobs) >= kwargs["limit"]:
                break
        
        return jobs
    
    async def get_job(self, job_id: str):
        """Mock get_job method."""
        from workload_analyzer.models.job_models import JobDetail
        
        job_data = {
            "job_id": job_id,
            "name": f"Mock Job for {job_id}",
            "job_type": "IWPS",
            "status": "Completed",
            "platform_id": "platform-001",
            "instance_id": "instance-001",
            "created_at": datetime.utcnow().isoformat(),
            "actual_runtime_minutes": 45.5,
            "peak_cpu_usage_percent": 75.0,
            "peak_memory_usage_gb": 16.0
        }
        
        return JobDetail(**job_data)
    
    async def get_platforms(self, **kwargs):
        """Mock get_platforms method."""
        from workload_analyzer.models.platform_models import Platform
        
        platforms_data = create_mock_platform_response()["platforms"]
        platforms = []
        
        for platform_data in platforms_data:
            # Apply filters
            if kwargs.get("is_available") is not None and platform_data["is_available"] != kwargs["is_available"]:
                continue
            
            platform = Platform(**platform_data)
            platforms.append(platform)
            
            # Apply limit
            if kwargs.get("limit") and len(platforms) >= kwargs["limit"]:
                break
        
        return platforms
    
    async def get_platform(self, platform_id: str):
        """Mock get_platform method."""
        from workload_analyzer.models.platform_models import Platform
        
        platform_data = {
            "platform_id": platform_id,
            "name": f"Mock Platform {platform_id}",
            "platform_type": "Simulation",
            "is_active": True,
            "is_available": True,
            "max_cpu_count": 64,
            "max_memory_gb": 256.0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return Platform(**platform_data)
    
    async def get_instances(self, **kwargs):
        """Mock get_instances method."""
        from workload_analyzer.models.platform_models import Instance
        
        instances_data = create_mock_instance_response()["instances"]
        instances = []
        
        for instance_data in instances_data:
            # Apply filters
            if kwargs.get("platform_id") and instance_data["platform_id"] != kwargs["platform_id"]:
                continue
            if kwargs.get("is_available") is not None and instance_data["is_available"] != kwargs["is_available"]:
                continue
            
            instance = Instance(**instance_data)
            instances.append(instance)
            
            # Apply limit
            if kwargs.get("limit") and len(instances) >= kwargs["limit"]:
                break
        
        return instances
    
    async def get_instance(self, instance_id: str):
        """Mock get_instance method."""
        from workload_analyzer.models.platform_models import Instance
        
        instance_data = {
            "instance_id": instance_id,
            "name": f"Mock Instance {instance_id}",
            "platform_id": "platform-001",
            "status": "Running",
            "is_active": True,
            "is_available": True,
            "allocated_cpu_count": 16,
            "allocated_memory_gb": 64.0,
            "health_status": "Healthy",
            "created_at": datetime.utcnow().isoformat()
        }
        
        return Instance(**instance_data)
    
    async def get_job_schema(self):
        """Mock get_job_schema method."""
        return {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "name": {"type": "string"},
                "job_type": {"type": "string", "enum": ["IWPS", "ISIM", "Coho"]},
                "status": {"type": "string", "enum": ["Pending", "Running", "Completed", "Failed"]}
            },
            "required": ["name", "job_type"]
        }


class MockFileService:
    """Mock file service for testing."""
    
    def __init__(self, settings=None):
        self.settings = settings
        self._closed = False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._closed = True
    
    async def list_files(self, tenant: str, job_id: str, path: str = "", recursive: bool = False):
        """Mock list_files method."""
        from workload_analyzer.models.response_models import FileInfo
        
        files = [
            FileInfo(
                name="output.log",
                path="output.log",
                size_bytes=2048,
                file_type="text/plain",
                is_directory=False,
                download_url=f"https://mock-files.intel.com/{tenant}/jobs/{job_id}/output.log"
            ),
            FileInfo(
                name="results",
                path="results",
                size_bytes=None,
                is_directory=True
            ),
            FileInfo(
                name="results/summary.json",
                path="results/summary.json",
                size_bytes=512,
                file_type="application/json",
                is_directory=False,
                download_url=f"https://mock-files.intel.com/{tenant}/jobs/{job_id}/results/summary.json"
            )
        ]
        
        if not recursive:
            # Filter out subdirectory files
            files = [f for f in files if "/" not in f.path or f.is_directory]
        
        return files
    
    async def get_file_info(self, tenant: str, job_id: str, file_path: str):
        """Mock get_file_info method."""
        from workload_analyzer.models.response_models import FileInfo
        
        return FileInfo(
            name=file_path.split("/")[-1],
            path=file_path,
            size_bytes=1024,
            file_type="text/plain",
            download_url=f"https://mock-files.intel.com/{tenant}/jobs/{job_id}/{file_path}"
        )
    
    async def file_exists(self, tenant: str, job_id: str, file_path: str):
        """Mock file_exists method."""
        return True
    
    async def get_download_url(self, tenant: str, job_id: str, file_path: str, expires_in_seconds: int = 3600):
        """Mock get_download_url method."""
        return f"https://mock-files.intel.com/{tenant}/jobs/{job_id}/{file_path}?token=mock-token&expires={expires_in_seconds}"


def assert_response_structure(response_data: Dict[str, Any], expected_keys: List[str]):
    """Assert that response has expected structure."""
    for key in expected_keys:
        assert key in response_data, f"Missing key '{key}' in response"


def assert_pagination_meta(meta: Dict[str, Any], expected_page: int = 1, expected_page_size: int = 50):
    """Assert pagination metadata structure."""
    required_keys = ["total", "page", "page_size", "total_pages", "has_next", "has_previous"]
    for key in required_keys:
        assert key in meta, f"Missing pagination key '{key}'"
    
    assert meta["page"] == expected_page
    assert meta["page_size"] == expected_page_size
    assert isinstance(meta["total"], int)
    assert isinstance(meta["total_pages"], int)
    assert isinstance(meta["has_next"], bool)
    assert isinstance(meta["has_previous"], bool)


@pytest.fixture
def mock_iss_client_class():
    """Fixture that provides the MockISSClient class."""
    return MockISSClient


@pytest.fixture
def mock_file_service_class():
    """Fixture that provides the MockFileService class."""
    return MockFileService