"""API endpoint tests."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from workload_analyzer.main import app


class TestJobsAPI:
    """Test jobs API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_list_jobs_success(self, client, sample_iss_jobs_response):
        """Test successful jobs listing."""
        from workload_analyzer.api.jobs import get_iss_client
        from workload_analyzer.main import app
        
        # Create mock client
        mock_iss_client = AsyncMock()
        mock_iss_client.get_jobs.return_value = sample_iss_jobs_response
        
        # Override the dependency
        app.dependency_overrides[get_iss_client] = lambda: mock_iss_client
        
        try:
            response = client.get("/api/v1/jobs")
            
            assert response.status_code == 200
            data = response.json()
            assert "jobs" in data
            assert "count" in data
            assert len(data["jobs"]) == 2
            assert data["count"] == 2
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    def test_get_job_detail_success(self, client, sample_job_data):
        """Test successful job detail retrieval."""
        from workload_analyzer.api.jobs import get_iss_client
        from workload_analyzer.main import app
        
        # Create mock client
        mock_iss_client = AsyncMock()
        mock_iss_client.get_job.return_value = sample_job_data.model_dump(by_alias=True)
        
        # Override the dependency
        app.dependency_overrides[get_iss_client] = lambda: mock_iss_client
        
        try:
            job_id = "a1234567-89ab-cdef-0123-456789abcdef"
            response = client.get(f"/api/v1/jobs/{job_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert "job" in data
            assert data["job"]["JobRequestID"] == job_id
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    def test_list_job_files_success(self, client, sample_file_list, sample_job_detail):
        """Test successful job files listing."""
        from workload_analyzer.api.jobs import get_file_service, get_iss_client
        
        # Use sample job detail which already has all required fields
        # Ensure tenant_id is set explicitly
        mock_job = sample_job_detail
        if not hasattr(mock_job, 'tenant_id') or mock_job.tenant_id is None:
            mock_job.tenant_id = "test-tenant"
        
        # Create mock ISS client
        mock_iss_client = AsyncMock()
        mock_iss_client.get_job.return_value = mock_job
        mock_iss_client.__aenter__.return_value = mock_iss_client
        mock_iss_client.__aexit__.return_value = None
        
        # Create mock file service
        mock_file_service = AsyncMock()
        mock_file_service.list_files.return_value = sample_file_list
        mock_file_service.__aenter__.return_value = mock_file_service
        mock_file_service.__aexit__.return_value = None
        
        # Override both dependencies
        app.dependency_overrides[get_iss_client] = lambda: mock_iss_client
        app.dependency_overrides[get_file_service] = lambda: mock_file_service
        
        try:
            job_id = "caef4de5-00e2-4483-b23c-b4bd3bbb5876"
            response = client.get(f"/api/v1/jobs/{job_id}/files")
            
            assert response.status_code == 200
            data = response.json()
            assert "files" in data
            assert "total_files" in data
            assert "job_id" in data
            assert len(data["files"]) == len(sample_file_list)
            assert data["job_id"] == job_id
            assert data["total_files"] == len(sample_file_list)
            
            # Verify the calls were made with correct parameters
            mock_iss_client.get_job.assert_called_once_with(job_id)
            mock_file_service.list_files.assert_called_once_with(
                tenant="test-tenant", job_id=job_id, path=""
            )
        finally:
            # Clean up
            app.dependency_overrides.clear()


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_docs_endpoint(self, client):
        """Test OpenAPI documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_json(self, client):
        """Test OpenAPI JSON schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
