"""ISS (Intel Simulation Service) API client."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import aiohttp
from pydantic import ValidationError

from ..config import Settings
from ..exceptions import (
    ISSAuthenticationError,
    ISSClientError,
    ISSNotFoundError,
    ISSRateLimitError,
)
from ..models.job_models import JobDetail, JobRequest, JobStatus, JobType, ISSJobsResponse
from ..models.platform_models import Instance, Platform
from .auth_service import AuthService, Credentials

logger = logging.getLogger(__name__)


class ISSClient:
    """Client for Intel Simulation Service API."""

    def __init__(self, settings: Settings, auth_service: Optional[AuthService] = None):
        """Initialize the ISS client.

        Args:
            settings: Application settings
            auth_service: Authentication service instance
        """
        self.settings = settings
        self.auth_service = auth_service or AuthService(settings)
        self._session: Optional[aiohttp.ClientSession] = None
        self._credentials: Optional[Credentials] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.settings.iss_timeout_seconds)
            
            # Configure proxy settings for corporate environment
            proxy_url = None
            https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
            if https_proxy:
                proxy_url = https_proxy
                logger.debug(f"Using proxy: {proxy_url}")
            
            connector = aiohttp.TCPConnector()
            self._session = aiohttp.ClientSession(
                timeout=timeout, 
                headers={"User-Agent": "Workload-Analyzer/1.0"},
                connector=connector
            )
            
            # Store proxy URL for use in requests
            self._proxy_url = proxy_url
            logger.debug("Created new aiohttp session with proxy configuration")

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("Closed aiohttp session")

    async def _get_credentials(self) -> Credentials:
        """Get or refresh credentials."""
        if self._credentials is None:
            self._credentials = await self.auth_service.get_iss_credentials()
        return self._credentials

    async def _get_oauth_token(self, credentials: Credentials) -> str:
        """Get OAuth2 access token using client credentials.
        
        Args:
            credentials: OAuth2 client credentials
            
        Returns:
            Access token
            
        Raises:
            ISSClientError: If token exchange fails
        """
        try:
            token_url = self.settings.auth_domain
            logger.info(f"Requesting OAuth2 token from: {token_url}")
            
            # Prepare OAuth2 client credentials request (matching working code)
            token_data = {
                "grant_type": "client_credentials",
                "scope": ""
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Use HTTP Basic Auth with client_id/client_secret (like the working code)
            auth = aiohttp.BasicAuth(credentials.client_id, credentials.client_secret)
            
            # Use a shorter timeout for the OAuth request
            timeout = aiohttp.ClientTimeout(total=10)

            logger.debug(f"Making OAuth2 request for {token_url} with data: {token_data} and headers: {headers} using BasicAuth {auth}")

            # Prepare proxy parameter if proxy is configured
            proxy_param = self._proxy_url if hasattr(self, '_proxy_url') and self._proxy_url else None

            async with self._session.post(
                token_url,
                data=token_data,
                headers=headers,
                auth=auth,
                timeout=timeout,
                proxy=proxy_param
            ) as response:
                response_text = await response.text()
                logger.debug(f"OAuth2 response status: {response.status}")
                
                if response.status != 200:
                    logger.error(f"OAuth2 token request failed: {response.status} - {response_text}")
                    raise ISSClientError(f"OAuth2 token request failed: {response.status} - {response_text}")
                
                try:
                    token_response = await response.json()
                except Exception as json_error:
                    logger.error(f"Failed to parse OAuth2 response as JSON: {json_error}")
                    logger.error(f"Response text: {response_text}")
                    raise ISSClientError(f"Invalid OAuth2 response format: {json_error}")
                
                access_token = token_response.get("access_token")
                
                if not access_token:
                    logger.error(f"No access_token in OAuth2 response: {token_response}")
                    raise ISSClientError("No access_token in OAuth2 response")
                
                logger.debug(f"Successfully obtained OAuth2 access token: {access_token[:20]}...")
                return access_token
                
        except asyncio.TimeoutError:
            logger.error(f"OAuth2 request timed out to {token_url}")
            raise ISSClientError(f"OAuth2 request timed out to {token_url}")
        except aiohttp.ClientError as e:
            logger.error(f"OAuth2 client error: {e}")
            raise ISSClientError(f"OAuth2 client error: {e}")
        except Exception as e:
            logger.error(f"Failed to get OAuth2 token: {e}")
            raise ISSClientError(f"OAuth2 authentication failed: {e}")

    def _build_url(self, endpoint: str) -> str:
        """Build full URL for ISS API endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            Full URL
        """
        base_url = self.settings.iss_api_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base_url}/v1/{endpoint}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_auth: bool = True,
    ) -> Dict[str, Any]:
        """Make authenticated request to ISS API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON body data
            retry_auth: Retry on auth failure

        Returns:
            Response data

        Raises:
            ISSClientError: On request failure
        """
        await self._ensure_session()
        credentials = await self._get_credentials()

        url = self._build_url(endpoint)
        
        # Use OAuth2 Bearer token if we have client credentials, otherwise Basic Auth
        headers = {"Accept": "application/json"}
        if credentials.client_id and credentials.client_secret:
            # OAuth2 flow - get bearer token
            token = await self._get_oauth_token(credentials)
            headers["Authorization"] = f"Bearer {token}"
        elif credentials.username and credentials.password:
            # Basic Auth flow
            auth = aiohttp.BasicAuth(credentials.username, credentials.password)
        else:
            raise ISSClientError("No valid authentication credentials available")

        if json_data:
            headers["Content-Type"] = "application/json"

        try:
            logger.debug(f"Making {method} request to {url} {params}")

            # Prepare request arguments
            request_kwargs = {
                "method": method,
                "url": url,
                "params": params,
                "json": json_data,
                "headers": headers,
            }
            
            # Add proxy if configured
            if hasattr(self, '_proxy_url') and self._proxy_url:
                request_kwargs["proxy"] = self._proxy_url
            
            # Add auth only for Basic Auth (Bearer token is in headers)
            if credentials.username and credentials.password:
                request_kwargs["auth"] = auth

            async with self._session.request(**request_kwargs) as response:

                # Handle different response status codes
                if response.status == 401:
                    if retry_auth:
                        logger.warning("Authentication failed, refreshing credentials")
                        self._credentials = None
                        return await self._request(
                            method, endpoint, params, json_data, False
                        )
                    else:
                        raise ISSAuthenticationError(
                            "Authentication failed after retry"
                        )

                elif response.status == 404:
                    raise ISSNotFoundError(f"Resource not found: {endpoint}")

                elif response.status == 429:
                    raise ISSRateLimitError("Rate limit exceeded")

                elif response.status >= 400:
                    error_text = await response.text()
                    raise ISSClientError(
                        f"Request failed with status {response.status}: {error_text}"
                    )

                # Parse response
                try:
                    data = await response.json()
                    logger.debug(f"Request successful for {method} {url}")
                    return data
                except Exception as e:
                    text = await response.text()
                    logger.error(
                        f"Failed to parse response JSON: {e}, text: {text[:200]}"
                    )
                    raise ISSClientError(f"Invalid response format: {e}")

        except aiohttp.ClientError as e:
            logger.error(f"Network error for {method} {url}: {e}")
            raise ISSClientError(f"Network error: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout for {method} {url}")
            raise ISSClientError("Request timeout")

    # Job-related methods

    async def get_jobs(
        self,
        limit: int = 100,
        status: Optional[JobStatus] = None,
        job_request_id: Optional[str] = None,
        job_type: Optional[str] = None,
        queue: Optional[str] = None,
        requested_by: Optional[str] = None,
        parent_instance_id: Optional[str] = None,
        workload_job_roi_id: Optional[str] = None,
        continuation_token: Optional[str] = None,
    ) -> ISSJobsResponse:
        """Get list of jobs with optional filtering.

        Args:
            limit: Maximum number of jobs to return (1-100, default 100)
            status: Filter by job status
            job_request_id: Filter by specific job request ID
            job_type: Filter jobs by type (comma-separated for multiple)
            queue: Filter jobs by queue
            requested_by: Filter jobs by requesting user
            parent_instance_id: Filter jobs by parent instance ID
            workload_job_roi_id: Filter jobs by workload job ROI ID
            continuation_token: Token for pagination continuation

        Returns:
            ISS jobs response with jobs list, count, and continuation token
        """
        params = {
            "Limit": min(max(limit, 1), 100),  # Ensure between 1-100 per ISS API spec
        }

        if status:
            params["JobRequestStatus"] = status.value
        if job_request_id:
            params["JobRequestID"] = job_request_id
        if job_type:
            params["Type"] = job_type
        if queue:
            params["Queue"] = queue
        if requested_by:
            params["RequestedBy"] = requested_by
        if parent_instance_id:
            params["ParentInstanceID"] = parent_instance_id
        if workload_job_roi_id:
            params["WorkloadJobROIID"] = workload_job_roi_id
        if continuation_token:
            params["ContinuationToken"] = continuation_token

        try:
            data = await self._request("GET", "jobs", params=params)
            # logger.debug(f"Response keys: {data.keys()}")
            # logger.debug(f"Count: {data.get('Count')}")
            # logger.debug(f"Length: {len(data.get('Jobs'))}")
            jobs = []

            for job_data in data.get("Jobs", []):
                try:
                    # logger.debug(f"Parsing job data: {job_data}")
                    
                    # Flatten nested metadata fields for better parsing
                    if "Metadata" in job_data:
                        metadata = job_data.pop("Metadata")
                        job_data["RequestedOn"] = metadata.get("RequestedOn")
                        job_data["LastUpdatedOn"] = metadata.get("LastUpdatedOn")
                        job_data["RequestedBy"] = metadata.get("RequestedBy")
                        job_data["LastUpdatedBy"] = metadata.get("LastUpdatedBy")
                    
                    job = JobRequest(**job_data)
                    jobs.append(job)
                except ValidationError as e:
                    logger.warning(f"Failed to parse job data: {e}")
                    continue

            logger.info(f"Retrieved {len(jobs)} jobs")
            
            # Return the complete ISS response with pagination info
            return ISSJobsResponse(
                jobs=jobs,
                count=data.get("Count", len(jobs)),
                continuation_token=data.get("ContinuationToken")
            )

        except Exception as e:
            logger.error(f"Failed to get jobs: {e}")
            raise ISSClientError(f"Failed to get jobs: {e}")

    async def get_job(self, job_id: str) -> JobDetail:
        """Get detailed information for a specific job.

        Args:
            job_id: Job identifier

        Returns:
            Detailed job information
        """
        try:
            data = await self._request("GET", f"jobs/job/{job_id}")
            # logger.debug(f"Job data retrieved: {data}")
            job = JobDetail(**data)
            logger.info(f"Retrieved job details for {job_id}")
            return job

        except ValidationError as e:
            logger.error(f"Failed to parse job detail data: {e}")
            raise ISSClientError(f"Invalid job data format: {e}")

    # Platform-related methods

    async def get_platforms(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get platform data with all query parameters passed through to ISS API.

        Args:
            query_params: Dictionary of query parameters to pass to ISS API

        Returns:
            Raw response from ISS API
        """
        try:
            # Pass all parameters directly to ISS API
            data = await self._request("GET", "platforms", params=query_params)
            logger.info(f"Retrieved platforms data with {len(data.get('Platforms', []))} platforms")
            return data

        except Exception as e:
            logger.error(f"Failed to get platforms (raw): {e}")
            raise ISSClientError(f"Failed to get platforms: {e}")

    async def get_platform(self, platform_id: str) -> Platform:
        """Get detailed information for a specific platform.

        Args:
            platform_id: Platform identifier

        Returns:
            Platform information
        """
        try:
            data = await self._request("GET", f"platforms/platform/{platform_id}")
            
            # Map ISS API field names to our model field names
            mapped_data = {}
            
            # Required field mappings
            mapped_data["platform_id"] = data.get("PlatformID", "")
            mapped_data["name"] = data.get("PlatformName", "")
            
            # Map platform type from ISS to our enum
            iss_platform_type = data.get("PlatformType", "")
            if iss_platform_type == "Simics":
                mapped_data["platform_type"] = "Simulation"
            else:
                # Default mapping for unknown types
                mapped_data["platform_type"] = "Virtual"
            
            # Optional field mappings
            mapped_data["description"] = data.get("Description")
            mapped_data["version"] = data.get("SimicsPlatformVersion") or data.get("SimicsPlatformRelease")
            
            # Map features if available
            if "Features" in data:
                features = data["Features"]
                mapped_data["is_available"] = True  # Default to available
                # Map IWPS enabled status
                if "iwps_enabled" in features:
                    mapped_data["tags"] = {"iwps_enabled": str(features["iwps_enabled"])}
            
            # Memory mapping
            if "PlatformMemorySize" in data:
                mapped_data["max_memory_gb"] = float(data["PlatformMemorySize"])
            
            # Set reasonable defaults for required fields
            mapped_data.setdefault("is_active", True)
            mapped_data.setdefault("is_available", True)
            mapped_data.setdefault("maintenance_mode", False)
            
            platform = Platform(**mapped_data)
            logger.info(f"Retrieved platform details for {platform_id}")
            return platform

        except ValidationError as e:
            logger.error(f"Failed to parse platform data from {data}: {e}")
            raise ISSClientError(f"Invalid platform data format: {e}")
        except Exception as e:
            logger.error(f"Failed to get platform {platform_id}: {e}")
            raise ISSClientError(f"Failed to get platform {platform_id}: {e}")

    # Instance-related methods

    async def get_instances(
        self,
        platform_id: Optional[str] = None,
        is_available: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Instance]:
        """Get list of instances with optional filtering.

        Args:
            platform_id: Filter by platform ID
            is_available: Filter by availability
            limit: Maximum number of instances to return
            offset: Number of instances to skip

        Returns:
            List of instances
        """
        params = {"limit": min(limit, 1000), "offset": max(offset, 0)}

        if platform_id:
            params["platform_id"] = platform_id
        if is_available is not None:
            params["available"] = str(is_available).lower()

        try:
            data = await self._request("GET", "instances", params=params)
            instances = []

            for instance_data in data.get("instances", []):
                try:
                    instance = Instance(**instance_data)
                    instances.append(instance)
                except ValidationError as e:
                    logger.warning(f"Failed to parse instance data: {e}")
                    continue

            logger.info(f"Retrieved {len(instances)} instances")
            return instances

        except Exception as e:
            logger.error(f"Failed to get instances: {e}")
            raise ISSClientError(f"Failed to get instances: {e}")

    async def get_instance(self, instance_id: str) -> Instance:
        """Get detailed information for a specific instance.

        Args:
            instance_id: Instance identifier

        Returns:
            Instance information
        """
        try:
            data = await self._request("GET", f"instances/{instance_id}")
            instance = Instance(**data)
            logger.info(f"Retrieved instance details for {instance_id}")
            return instance

        except ValidationError as e:
            logger.error(f"Failed to parse instance data: {e}")
            raise ISSClientError(f"Invalid instance data format: {e}")
