"""File service for accessing simulation artifacts."""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import aiohttp

from ..config import Settings
from ..exceptions import FileAccessError, FileNotFoundError, FileServiceError

logger = logging.getLogger(__name__)


class FileService:
    """Service for accessing files from ISS file service."""

    def __init__(self, settings: Settings, auth_service=None):
        """Initialize the file service.

        Args:
            settings: Application settings
            auth_service: Authentication service for OAuth2 tokens
        """
        self.settings = settings
        self.auth_service = auth_service
        self._session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None

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
            timeout = aiohttp.ClientTimeout(
                total=self.settings.file_service_timeout_seconds
            )
            
            # Configure proxy settings for corporate environment
            proxy_url = None
            https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
            if https_proxy:
                proxy_url = https_proxy
                logger.debug(f"Using proxy: {proxy_url}")
            
            connector = aiohttp.TCPConnector()
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "Workload-Analyzer-FileService/1.0"},
                connector=connector,
            )
            
            # Store proxy URL for use in requests
            self._proxy_url = proxy_url
            logger.debug("Created new file service session with proxy configuration")

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("Closed file service session")

    async def _get_access_token(self) -> str:
        """Get OAuth2 access token for file service authentication.
        
        Returns:
            Access token for authentication
            
        Raises:
            FileServiceError: If authentication fails
        """
        if not self.auth_service:
            raise FileServiceError("Authentication service not provided")
            
        try:
            # Get OAuth2 credentials from auth service
            credentials = await self.auth_service.get_iss_credentials()
            
            # Prepare OAuth2 token request
            token_url = self.settings.auth_domain
            token_data = {
                "grant_type": "client_credentials",
                "scope": ""
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Use HTTP Basic Auth with client_id/client_secret
            auth = aiohttp.BasicAuth(credentials.client_id, credentials.client_secret)
            
            # Prepare proxy parameter if proxy is configured
            proxy_param = self._proxy_url if hasattr(self, '_proxy_url') and self._proxy_url else None
            
            async with self._session.post(
                token_url,
                data=token_data,
                headers=headers,
                auth=auth,
                proxy=proxy_param
            ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    logger.error(f"OAuth2 token request failed: {response.status} - {response_text}")
                    raise FileServiceError(f"OAuth2 authentication failed: {response.status}")
                
                token_response = await response.json()
                access_token = token_response.get("access_token")
                
                if not access_token:
                    raise FileServiceError("No access token in OAuth2 response")
                
                logger.debug("Successfully obtained OAuth2 access token for file service")
                return access_token
                
        except Exception as e:
            logger.error(f"Failed to get OAuth2 token for file service: {e}")
            raise FileServiceError(f"Authentication failed: {e}")

    def _get_file_service_url(self, tenant: str) -> str:
        """Get file service URL for specified tenant.

        Args:
            tenant: Tenant identifier

        Returns:
            File service base URL
        """
        return self.settings.get_file_service_url(tenant)

    def _build_url(self, tenant: str, path: str) -> str:
        """Build full URL for file service endpoint.

        Args:
            tenant: Tenant identifier
            path: File path

        Returns:
            Full URL
        """
        base_url = self._get_file_service_url(tenant).rstrip("/")
        path = path.lstrip("/")
        return urljoin(f"{base_url}/", path)

    def _build_file_path(self, job_id: str, file_path: str = "") -> str:
        """Build the correct file service path for job files.

        Args:
            job_id: Job identifier
            file_path: Optional file path within the job artifacts

        Returns:
            Complete file service path
        """
        base_path = f"fs/files/{job_id}/iwps/artifacts/out"
        if file_path:
            base_path = f"{base_path}/{file_path.strip('/')}"
        return base_path

    async def _request(
        self, method: str, tenant: str, path: str, params: Optional[dict] = None
    ) -> aiohttp.ClientResponse:
        """Make request to file service.

        Args:
            method: HTTP method
            tenant: Tenant identifier
            path: File path
            params: Query parameters

        Returns:
            Response object

        Raises:
            FileServiceError: On request failure
        """
        await self._ensure_session()
        url = self._build_url(tenant, path)

        try:
            logger.debug(f"Making {method} request to {url}")

            # Get OAuth2 access token if auth service is available
            headers = {}
            if self.auth_service:
                if not self._access_token:
                    self._access_token = await self._get_access_token()
                headers["Authorization"] = f"Bearer {self._access_token}"

            # Prepare proxy parameter if proxy is configured
            proxy_param = self._proxy_url if hasattr(self, '_proxy_url') and self._proxy_url else None

            response = await self._session.request(
                method=method, url=url, params=params, headers=headers, proxy=proxy_param
            )

            if response.status == 401 and self.auth_service:
                # Token might be expired, refresh and retry once
                logger.warning("Authentication failed, refreshing access token")
                self._access_token = await self._get_access_token()
                headers["Authorization"] = f"Bearer {self._access_token}"
                
                # Retry the request with new token
                response = await self._session.request(
                    method=method, url=url, params=params, headers=headers, proxy=proxy_param
                )
                
            if response.status == 404:
                raise FileNotFoundError(f"File not found: {path}")
            elif response.status == 401:
                raise FileAccessError(f"Authentication failed: {path}")
            elif response.status == 403:
                raise FileAccessError(f"Access denied: {path}")
            elif response.status >= 400:
                error_text = await response.text()
                raise FileServiceError(
                    f"Request failed with status {response.status}: {error_text}"
                )

            return response

        except aiohttp.ClientError as e:
            logger.error(f"Network error for {method} {url}: {e}")
            raise FileServiceError(f"Network error: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout for {method} {url}")
            raise FileServiceError("Request timeout")

    async def list_files(
        self, tenant: str, job_id: str, path: str = ""
    ) -> List[str]:
        """List files for a job.

        Args:
            tenant: Tenant identifier
            job_id: Job identifier
            path: Directory path within job

        Returns:
            List of filenames
        """
        try:
            # Use the correct file service path for IWPS artifacts
            file_path = self._build_file_path(job_id, path)

            async with await self._request(
                "GET", tenant, file_path, {}
            ) as response:
                data = await response.json()
                logger.debug(f"File list data retrieved: {data}")

                files = []
                for file_data in data.get("files", []):
                    try:
                        # Handle both string filenames and object file data
                        if isinstance(file_data, str):
                            # Simple filename string
                            files.append(file_data)
                        else:
                            # Object with file metadata - extract name
                            filename = file_data.get("name", "")
                            if filename:
                                files.append(filename)

                    except Exception as e:
                        logger.warning(f"Failed to parse file data: {e}")
                        continue

                logger.info(f"Retrieved {len(files)} files for job {job_id}")
                return files

        except Exception as e:
            logger.error(f"Failed to list files for job {job_id}: {e}")
            raise FileServiceError(f"Failed to list files: {e}")

    async def download_file(
        self, tenant: str, job_id: str, file_path: str
    ) -> bytes:
        """Download a file.

        Args:
            tenant: Tenant identifier
            job_id: Job identifier
            file_path: Path to the file

        Returns:
            File content as bytes
        """
        try:
            path = self._build_file_path(job_id, file_path)

            async with await self._request("GET", tenant, path) as response:
                content = await response.read()

                logger.info(f"Downloaded file {file_path} ({len(content)} bytes)")
                return content

        except Exception as e:
            logger.error(f"Failed to download file {file_path}: {e}")
            raise FileServiceError(f"Failed to download file: {e}")

