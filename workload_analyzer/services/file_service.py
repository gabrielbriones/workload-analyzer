"""File service for accessing simulation artifacts."""

import asyncio
import io
import logging
import os
import zipfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import aiohttp

from ..config import Settings
from ..exceptions import FileAccessError, FileNotFoundError, FileServiceError

logger = logging.getLogger(__name__)


class FileService:
    """Service for accessing files from ISS file service."""

    def __init__(self, settings: Settings, bearer_token: str, iss_client=None):
        """Initialize the file service.

        Args:
            settings: Application settings
            bearer_token: Bearer token for API authentication
            iss_client: Optional ISS client for job type lookup
        """
        self.settings = settings
        self.bearer_token = bearer_token
        self.iss_client = iss_client
        self._session: Optional[aiohttp.ClientSession] = None

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

    def _get_auth_headers(self) -> dict:
        """Get authentication headers with bearer token.
        
        Returns:
            Dictionary with Authorization header
        """
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Accept": "application/json",
        }

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

    async def _get_artifact_type_for_job(self, job_id: str) -> str:
        """Get the artifact type (iwps, isim, coho, workloadjob, workloadjobroi) based on job type.

        Args:
            job_id: Job identifier

        Returns:
            Artifact type ('iwps', 'isim', 'coho', 'workloadjob', 'workloadjobroi')
        """
        try:
            if not self.iss_client:
                logger.warning("ISS client not available, defaulting to 'iwps'")
                return "iwps"

            # Fetch job details from ISS
            async with self.iss_client:
                job = await self.iss_client.get_job(job_id)
                job_type = job.job_type if hasattr(job, 'job_type') else None

                # If job_type is an enum, get its value
                if hasattr(job_type, 'value'):
                    job_type = job_type.value

                logger.debug(f"Job {job_id} type: {job_type}")

                # Map job types to artifact types
                if job_type == "ISIM":
                    return "isim"
                elif job_type == "NovaCoho":
                    return "coho"
                elif job_type == "IWPS":
                    return "iwps"
                elif job_type == "WorkloadJob":
                    return "workloadjob"
                elif job_type == "WorkloadJobROI":
                    return "workloadjobroi"
                else:
                    # Default to iwps for unknown types
                    logger.warning(f"Unknown job type '{job_type}', defaulting to 'iwps'")
                    return "iwps"

        except Exception as e:
            logger.error(f"Failed to determine artifact type for job {job_id}: {e}")
            return "iwps"  # Default to iwps on error

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

            # Get authorization headers
            headers = self._get_auth_headers()

            # Prepare proxy parameter if proxy is configured
            proxy_param = self._proxy_url if hasattr(self, '_proxy_url') and self._proxy_url else None

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
            # Determine the correct artifact type for this job
            artifact_type = await self._get_artifact_type_for_job(job_id)

            # Build the correct file service path
            base_path = f"fs/files/{job_id}/{artifact_type}/artifacts/out"
            if path:
                base_path = f"{base_path}/{path.strip('/')}"

            if artifact_type in ["workloadjob", "workloadjobroi"]:
                # For custom workload jobs
                base_path =  f"fs/files/{job_id}/logs"

            async with await self._request(
                "GET", tenant, base_path, {}
            ) as response:
                data = await response.json()
                logger.debug(f"File list data retrieved: {data}")

                files = []
                file_data_list = data.get("files", []) if artifact_type not in ["workloadjob", "workloadjobroi"] else data.get("children", [])
                for file_data in file_data_list:
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
            # Determine the correct artifact type for this job
            artifact_type = await self._get_artifact_type_for_job(job_id)

            # Build the correct file service path
            base_path = f"fs/files/{job_id}/{artifact_type}/artifacts/out/{file_path.strip('/')}"

            if artifact_type in ["workloadjob", "workloadjobroi"]:
                # For custom workload jobs
                zip_file = None
                if "simics" in file_path.strip('/'):
                    zip_file = "simics"
                if "serialconsole" in file_path.strip('/'):
                    zip_file = "serialconsole"
                if zip_file is None:
                    raise Exception(f"Invalid file path {file_path} for workload job {job_id} logs")
                base_path =  f"fs/files/{job_id}/logs/all/{zip_file}"

            async with await self._request("GET", tenant, base_path) as response:
                content = await response.read()

                if artifact_type in ["workloadjob", "workloadjobroi"]:
                    logger.debug(f"Downloaded zip file for workload job {job_id}, size: {len(content)} bytes")
                    
                    # Extract specific file from zip
                    try:
                        with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:
                            # List available files in zip for debugging
                            available_files = zip_ref.namelist()
                            logger.debug(f"Files in zip archive: {available_files}")
                            
                            # Search for the requested file in the zip
                            # file_path might be something like "simics/console.log"
                            target_file = None
                            for zip_file_name in available_files:
                                if file_path.strip('/') in zip_file_name or zip_file_name.endswith(file_path.strip('/')):
                                    target_file = zip_file_name
                                    break
                            
                            if target_file is None:
                                # Try exact match
                                if file_path.strip('/') in available_files:
                                    target_file = file_path.strip('/')
                            
                            if target_file is None:
                                raise FileNotFoundError(
                                    f"File '{file_path}' not found in zip archive. Available files: {available_files}"
                                )
                            
                            # Extract the specific file
                            extracted_content = zip_ref.read(target_file)
                            logger.info(f"Extracted file '{target_file}' from zip ({len(extracted_content)} bytes)")
                            return extracted_content
                    except zipfile.BadZipFile as e:
                        logger.error(f"Failed to extract from zip file: {e}")
                        raise FileServiceError(f"Invalid zip file format: {e}")

                logger.info(f"Downloaded file {file_path} ({len(content)} bytes)")
                return content

        except Exception as e:
            logger.error(f"Failed to download file {file_path}: {e}")
            raise FileServiceError(f"Failed to download file: {e}")

