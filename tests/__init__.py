"""Test suite for the Workload Analyzer."""

# Test configuration
import pytest
import pytest_asyncio
from pytest_httpx import HTTPXMock

# Test utilities
from .conftest import *
from .test_utils import *

# Unit tests
from .unit import *

# Integration tests
from .integration import *

# API tests
from .api import *

__all__ = [
    # Test fixtures and utilities
    "app_client",
    "mock_settings",
    "mock_iss_client",
    "mock_auth_service",
    "sample_job_data",
    "sample_platform_data",
    "sample_instance_data",
    
    # Test modules
    "test_config",
    "test_models",
    "test_services",
    "test_analysis", 
    "test_api_jobs",
    "test_api_platforms",
    "test_api_instances",
    "test_api_analysis",
    "test_integration_full",
]