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
    
    def test_list_job_files_success(self, client, sample_file_list):
        """Test successful job files listing."""
        from workload_analyzer.api.jobs import get_file_service
        
        mock_file_service = AsyncMock()
        mock_file_service.list_files.return_value = sample_file_list
        
        # Override the dependency
        client.app.dependency_overrides[get_file_service] = lambda: mock_file_service
        
        job_id = "a1234567-89ab-cdef-0123-456789abcdef"
        response = client.get(f"/api/v1/jobs/{job_id}/files")
        
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert "total_files" in data
        assert "job_id" in data
        assert len(data["files"]) == len(sample_file_list)
        assert data["job_id"] == job_id
        assert data["total_files"] == len(sample_file_list)
        
        # Clean up
        client.app.dependency_overrides.clear()


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
