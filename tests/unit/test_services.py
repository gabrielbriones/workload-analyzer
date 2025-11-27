"""Unit tests for service classes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from workload_analyzer.services.iss_client import ISSClient
from workload_analyzer.services.file_service import FileService
from workload_analyzer.services.auth_service import AuthService, Credentials
from workload_analyzer.exceptions import ISSClientError, FileServiceError, ISSAuthenticationError
from workload_analyzer.models.job_models import ISSJobsResponse, JobStatus


class TestAuthService:
    """Test authentication service."""
    
    @pytest.mark.asyncio
    async def test_get_iss_credentials_success(self, mock_settings):
        """Test successful ISS credentials retrieval."""
        auth_service = AuthService(mock_settings)
        
        # Mock the AWS Secrets Manager get_secret_value method
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': '{"client_id": "test_client_id", "client_secret": "test_client_secret"}'
        }
        
        # Set the mock client as the internal client
        auth_service._client = mock_client
        
        credentials = await auth_service.get_iss_credentials()
        
        assert credentials.client_id == "test_client_id"
        assert credentials.client_secret == "test_client_secret"

    @pytest.mark.asyncio
    async def test_get_iss_credentials_failure(self, mock_settings):
        """Test ISS credentials retrieval failure."""
        auth_service = AuthService(mock_settings)
        
        # Mock the AWS Secrets Manager client to raise an exception
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = Exception("Secrets Manager error")
        
        # Set the mock client as the internal client
        auth_service._client = mock_client
        
        with pytest.raises(Exception):
            await auth_service.get_iss_credentials()


class TestISSClient:
    """Test ISS client."""
    
    @pytest.mark.asyncio
    async def test_get_jobs_success(self, mock_settings, sample_iss_jobs_response):
        """Test successful jobs retrieval."""
        auth_service = AsyncMock()
        from workload_analyzer.services.auth_service import Credentials
        auth_service.get_iss_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )

        iss_client = ISSClient(mock_settings, auth_service)

        # Mock both POST (OAuth2) and request (main API)
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.request') as mock_request:

            # Mock OAuth2 token response (POST)
            mock_token_response = AsyncMock()
            mock_token_response.status = 200
            mock_token_response.json.return_value = {"access_token": "test_token"}
            mock_token_response.text.return_value = '{"access_token": "test_token"}'
            mock_post.return_value.__aenter__.return_value = mock_token_response

            # Convert sample response to match ISS API format (capital keys)
            iss_api_response = {
                "Jobs": sample_iss_jobs_response["jobs"],  # jobs -> Jobs
                "Count": sample_iss_jobs_response["count"],  # count -> Count
                "ContinuationToken": sample_iss_jobs_response["continuation_token"]  # continuation_token -> ContinuationToken
            }

            # Mock jobs API response (request)
            mock_jobs_response = AsyncMock()
            mock_jobs_response.status = 200
            mock_jobs_response.json.return_value = iss_api_response
            mock_request.return_value.__aenter__.return_value = mock_jobs_response

            result = await iss_client.get_jobs()

            # Verify the result is an ISSJobsResponse object with correct structure
            assert isinstance(result, ISSJobsResponse)
            assert result.count == sample_iss_jobs_response["count"]
            assert result.continuation_token == sample_iss_jobs_response["continuation_token"]
            assert len(result.jobs) == len(sample_iss_jobs_response["jobs"])

            # Verify job details match
            for i, job in enumerate(result.jobs):
                expected_job = sample_iss_jobs_response["jobs"][i]
                assert job.job_id == expected_job["JobRequestID"]
                assert job.name == expected_job["Name"]
                assert job.job_type.value == expected_job["Type"]
                assert job.status.value == expected_job["JobRequestStatus"]
                assert job.owner == expected_job["owner"]

    @pytest.mark.asyncio 
    async def test_get_jobs_with_filters(self, mock_settings):
        """Test jobs retrieval with filters."""
        auth_service = AsyncMock()
        from workload_analyzer.services.auth_service import Credentials
        auth_service.get_iss_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        iss_client = ISSClient(mock_settings, auth_service)
        
        # Mock both POST (OAuth2) and request (main API)
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.request') as mock_request:
            
            # Mock OAuth2 token response (POST)
            mock_token_response = AsyncMock()
            mock_token_response.status = 200
            mock_token_response.json.return_value = {"access_token": "test_token"}
            mock_token_response.text.return_value = '{"access_token": "test_token"}'
            mock_post.return_value.__aenter__.return_value = mock_token_response
            
            # Mock jobs API response (request)
            mock_jobs_response = AsyncMock()
            mock_jobs_response.status = 200
            mock_jobs_response.json.return_value = {
                "Jobs": [],
                "Count": 0,
                "ContinuationToken": None
            }
            mock_request.return_value.__aenter__.return_value = mock_jobs_response
            
            await iss_client.get_jobs(
                job_type="IWPS",
                status=JobStatus.COMPLETE,
                limit=50
            )
            
            # Verify the request was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            
            # Check method and URL
            # The request method uses keyword arguments, not positional
            assert call_args.kwargs['method'] == 'GET'
            # The URL is built using get_iss_url() + /v1/ + endpoint
            expected_url = f"{mock_settings.get_iss_url()}/v1/jobs"
            assert call_args.kwargs['url'] == expected_url
            
            # Check parameters
            params = call_args.kwargs['params']
            assert params['Type'] == 'IWPS'
            assert params['JobRequestStatus'] == 'complete'
            assert params['Limit'] == 50
    
    @pytest.mark.asyncio
    async def test_get_job_success(self, mock_settings, sample_job_data):
        """Test successful single job retrieval."""
        auth_service = AsyncMock()
        from workload_analyzer.services.auth_service import Credentials
        auth_service.get_iss_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        iss_client = ISSClient(mock_settings, auth_service)
        
        # Convert JobRequest object to dictionary format for API response
        job_data_dict = sample_job_data.dict(by_alias=True)
        
        # Mock both POST (OAuth2) and request (main API)
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.request') as mock_request:
            
            # Mock OAuth2 token response (POST)
            mock_token_response = AsyncMock()
            mock_token_response.status = 200
            mock_token_response.json.return_value = {"access_token": "test_token"}
            mock_token_response.text.return_value = '{"access_token": "test_token"}'
            mock_post.return_value.__aenter__.return_value = mock_token_response
            
            # Mock job API response (request)
            mock_job_response = AsyncMock()
            mock_job_response.status = 200
            mock_job_response.json.return_value = job_data_dict
            mock_request.return_value.__aenter__.return_value = mock_job_response
            
            job_id = "test-job-id"
            result = await iss_client.get_job(job_id)
            
            # Verify the request was made to the correct endpoint
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            # The URL is built using get_iss_url() + /v1/ + endpoint
            expected_url = f"{mock_settings.get_iss_url()}/v1/jobs/job/{job_id}"
            assert call_args.kwargs['url'] == expected_url
            
            assert result.job_id == sample_job_data.job_id
    
    @pytest.mark.asyncio
    async def test_get_jobs_authentication_error(self, mock_settings):
        """Test authentication error handling."""
        auth_service = AsyncMock()
        auth_service.get_iss_credentials.side_effect = ISSAuthenticationError("Authentication failed")
        
        iss_client = ISSClient(mock_settings, auth_service)
        
        with pytest.raises(ISSClientError):
            await iss_client.get_jobs()
    
    @pytest.mark.asyncio
    async def test_get_jobs_client_error(self, mock_settings):
        """Test client error handling."""
        auth_service = AsyncMock()
        from workload_analyzer.services.auth_service import Credentials
        auth_service.get_iss_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        iss_client = ISSClient(mock_settings, auth_service)
        
        # Mock both POST (OAuth2) and request (main API)
        with patch('aiohttp.ClientSession.post') as mock_post, \
             patch('aiohttp.ClientSession.request') as mock_request:
            
            # Mock OAuth2 token response (POST)
            mock_token_response = AsyncMock()
            mock_token_response.status = 200
            mock_token_response.json.return_value = {"access_token": "test_token"}
            mock_token_response.text.return_value = '{"access_token": "test_token"}'
            mock_post.return_value.__aenter__.return_value = mock_token_response
            
            # Mock jobs API response with error (request)
            mock_jobs_response = AsyncMock()
            mock_jobs_response.status = 500
            mock_jobs_response.text.return_value = "Internal Server Error"
            mock_request.return_value.__aenter__.return_value = mock_jobs_response
            
            with pytest.raises(ISSClientError):
                await iss_client.get_jobs()


class TestFileService:
    """Test file service."""
    
    @pytest.mark.asyncio
    async def test_list_files_success(self, mock_settings, sample_file_list):
        """Test successful file listing."""
        auth_service = AsyncMock()
        from workload_analyzer.services.auth_service import Credentials
        auth_service.get_iss_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        file_service = FileService(mock_settings, auth_service)
        
        # Mock the _request method directly since it returns an async context manager
        with patch.object(file_service, '_request') as mock_request:
            # Mock response that acts as async context manager
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"files": sample_file_list}
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            # The _request method returns the response directly
            mock_request.return_value = mock_response
            
            result = await file_service.list_files("test", "test-job-id")
            
            assert result == sample_file_list
            
            # Verify the request was made
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, mock_settings):
        """Test successful file download."""
        auth_service = AsyncMock()
        from workload_analyzer.services.auth_service import Credentials
        auth_service.get_iss_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        file_service = FileService(mock_settings, auth_service)
        
        # Mock file content
        test_content = b"test file content"
        
        # Mock the _request method directly
        with patch.object(file_service, '_request') as mock_request:
            # Mock response that acts as async context manager
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read.return_value = test_content
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            
            # The _request method returns the response directly
            mock_request.return_value = mock_response
            
            result = await file_service.download_file("test", "test-job-id", "test-file.txt")
            
            assert result == test_content
            
            # Verify the request was made
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_file_not_found(self, mock_settings):
        """Test file not found error."""
        auth_service = AsyncMock()
        from workload_analyzer.services.auth_service import Credentials
        auth_service.get_iss_credentials.return_value = Credentials(
            client_id="test_client",
            client_secret="test_secret"
        )
        
        file_service = FileService(mock_settings, auth_service)
        
        # Mock the _request method to raise FileNotFoundError
        with patch.object(file_service, '_request') as mock_request:
            # The service catches 404 and raises FileNotFoundError, which is then caught and re-raised as FileServiceError
            mock_request.side_effect = FileNotFoundError("File not found: missing-file.txt")
            
            with pytest.raises(FileServiceError) as exc_info:
                await file_service.download_file("test", "test-job-id", "missing-file.txt")
            
            assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_file_service_authentication_error(self, mock_settings):
        """Test authentication error in file service."""
        auth_service = AsyncMock()
        auth_service.get_iss_credentials.side_effect = ISSAuthenticationError("Authentication failed")
        
        file_service = FileService(mock_settings, auth_service)
        
        with pytest.raises(FileServiceError) as exc_info:
            await file_service.list_files("test", "test-job-id")
        
        assert "Authentication failed" in str(exc_info.value)