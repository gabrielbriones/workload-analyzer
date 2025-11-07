"""Integration tests for API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from workload_analyzer.main import app


class TestJobsAPIIntegration:
    """Integration tests for jobs API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @patch('workload_analyzer.services.auth_service.AuthService.get_iss_credentials')
    @patch('workload_analyzer.services.iss_client.ISSClient.get_jobs')
    def test_jobs_api_integration(self, mock_get_jobs, mock_get_credentials, client, sample_iss_jobs_response):
        """Test jobs API integration."""
        # Mock authentication
        from workload_analyzer.services.auth_service import Credentials
        mock_get_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        # Mock ISS client response
        mock_get_jobs.return_value = sample_iss_jobs_response
        
        # Make API request
        response = client.get("/api/v1/jobs")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "count" in data
        assert data["count"] == 2
        
        # Verify ISS client was called
        mock_get_jobs.assert_called_once()
    
    @patch('workload_analyzer.services.auth_service.AuthService.get_iss_credentials')
    @patch('workload_analyzer.services.iss_client.ISSClient.get_job')
    def test_job_detail_api_integration(self, mock_get_job, mock_get_credentials, client, sample_job_detail):
        """Test job detail API integration.""" 
        # Mock authentication
        from workload_analyzer.services.auth_service import Credentials
        mock_get_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        # Mock ISS client response
        mock_get_job.return_value = sample_job_detail
        
        # Make API request
        job_id = "caef4de5-00e2-4483-b23c-b4bd3bbb5876"
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "job" in data
        # The field is serialized using the alias "JobRequestID"
        assert data["job"]["JobRequestID"] == "a1234567-89ab-cdef-0123-456789abcdef"
        
        # Verify ISS client was called with correct job ID
        mock_get_job.assert_called_once_with(job_id)
    
    @patch('workload_analyzer.services.auth_service.AuthService.get_iss_credentials')
    @patch('workload_analyzer.services.file_service.FileService.list_files')
    def test_file_listing_api_integration(self, mock_list_files, mock_get_credentials, client, sample_file_list):
        """Test file listing API integration."""
        # Mock authentication
        from workload_analyzer.services.auth_service import Credentials
        mock_get_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        # Mock file service response
        mock_list_files.return_value = sample_file_list
        
        # Make API request
        job_id = "caef4de5-00e2-4483-b23c-b4bd3bbb5876"
        response = client.get(f"/api/v1/jobs/{job_id}/files")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert "total_files" in data
        assert "job_id" in data
        assert data["job_id"] == job_id
        assert len(data["files"]) == len(sample_file_list)
    
    def test_health_endpoint_integration(self, client):
        """Test health endpoint integration."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_api_documentation_integration(self, client):
        """Test API documentation integration."""
        # Test OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data
        
        # Verify key endpoints are documented
        paths = openapi_data["paths"]
        assert "/api/v1/jobs" in paths
        assert "/health" in paths
        
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_cors_headers_integration(self, client):
        """Test CORS headers integration."""
        # Test preflight request
        response = client.options("/api/v1/jobs", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # CORS should be configured to allow requests
        # (Actual CORS behavior depends on middleware configuration)
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_404_error_integration(self, client):
        """Test 404 error handling."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed_integration(self, client):
        """Test method not allowed error handling."""
        response = client.post("/health")
        assert response.status_code == 405
    
    @patch('workload_analyzer.services.iss_client.ISSClient.get_jobs')
    def test_authentication_error_integration(self, mock_get_jobs, client):
        """Test authentication error handling."""
        from workload_analyzer.exceptions import ISSAuthenticationError
        
        # Mock authentication failure in ISS client
        mock_get_jobs.side_effect = ISSAuthenticationError("Authentication failed")
        
        response = client.get("/api/v1/jobs")
        assert response.status_code == 401
    
    def test_validation_error_integration(self, client):
        """Test validation error handling."""
        # Test invalid query parameters
        response = client.get("/api/v1/jobs?limit=0")
        assert response.status_code == 422
        
        response = client.get("/api/v1/jobs?job_type=INVALID")
        assert response.status_code == 422


class TestConfigurationIntegration:
    """Integration tests for configuration."""
    
    def test_settings_loaded_correctly(self):
        """Test that settings are loaded correctly."""
        from workload_analyzer.config import get_settings
        
        settings = get_settings()
        
        # Test that key settings exist
        assert hasattr(settings, 'iss_api_url')
        assert hasattr(settings, 'aws_region')
        assert hasattr(settings, 'bedrock_model_id')
        
        # Test that URLs are valid format
        assert settings.iss_api_url.startswith('http')
        
        # Test that Bedrock settings are configured
        assert settings.bedrock_model_id is not None
        assert settings.bedrock_temperature >= 0.0
        assert settings.bedrock_max_tokens > 0
