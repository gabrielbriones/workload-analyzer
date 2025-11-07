"""
Custom exception classes for the Workload Analyzer.
"""

from typing import Any, Dict, Optional


class WorkloadAnalyzerException(Exception):
    """Base exception for all Workload Analyzer errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ISSAPIException(WorkloadAnalyzerException):
    """Exception raised when ISS API calls fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_data = response_data or {}


class AuthenticationException(WorkloadAnalyzerException):
    """Exception raised when authentication fails."""

    pass


class ConfigurationException(WorkloadAnalyzerException):
    """Exception raised when configuration is invalid."""

    pass


class FileServiceException(WorkloadAnalyzerException):
    """Exception raised when file service operations fail."""

    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.file_path = file_path


class JobNotFoundException(WorkloadAnalyzerException):
    """Exception raised when a job is not found."""

    def __init__(self, job_id: str, **kwargs):
        message = f"Job not found: {job_id}"
        super().__init__(message, **kwargs)
        self.job_id = job_id


class PlatformNotFoundException(WorkloadAnalyzerException):
    """Exception raised when a platform is not found."""

    def __init__(self, platform_id: str, **kwargs):
        message = f"Platform not found: {platform_id}"
        super().__init__(message, **kwargs)
        self.platform_id = platform_id


class InstanceNotFoundException(WorkloadAnalyzerException):
    """Exception raised when an instance is not found."""

    def __init__(self, instance_id: str, **kwargs):
        message = f"Instance not found: {instance_id}"
        super().__init__(message, **kwargs)
        self.instance_id = instance_id


class AnalysisException(WorkloadAnalyzerException):
    """Exception raised when analysis operations fail."""

    pass


class RateLimitException(WorkloadAnalyzerException):
    """Exception raised when rate limits are exceeded."""

    def __init__(self, retry_after: Optional[int] = None, **kwargs):
        message = "Rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ValidationException(WorkloadAnalyzerException):
    """Exception raised when validation fails."""

    def __init__(
        self, message: str, validation_errors: Optional[Dict[str, Any]] = None, **kwargs
    ):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or {}


# Aliases for common exception patterns
AuthenticationError = AuthenticationException
ConfigurationError = ConfigurationException
FileServiceError = FileServiceException
FileAccessError = FileServiceException
FileNotFoundError = FileServiceException
ISSServiceError = ISSAPIException
ISSAuthenticationError = AuthenticationException
ISSClientError = ISSAPIException
ISSNotFoundError = ISSAPIException
ISSRateLimitError = RateLimitException
AnalysisError = AnalysisException
RateLimitError = RateLimitException
ValidationError = ValidationException
AIServiceError = AnalysisException  # For AI-related errors
