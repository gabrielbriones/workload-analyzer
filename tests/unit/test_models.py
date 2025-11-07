"""Unit tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from workload_analyzer.models.job_models import (
    JobDetail, JobStatus, JobType, ISSJobsResponse
)
from workload_analyzer.models.response_models import (
    JobDetailResponse, FileListResponse
)


class TestJobModels:
    """Test job-related models."""
    
    def test_job_type_enum(self):
        """Test JobType enum values."""
        assert JobType.IWPS == "IWPS"
        assert JobType.ISIM == "ISIM"
        assert JobType.COHO == "Coho"
        assert JobType.NOVA_COHO == "NovaCoho"
        assert JobType.INSTANCE == "Instance"
        assert JobType.WORKLOAD_JOB == "WorkloadJob"
        assert JobType.WORKLOAD_JOB_ROI == "WorkloadJobROI"
        assert JobType.CUSTOM == "Custom"
    
    def test_job_status_enum(self):
        """Test JobStatus enum values."""
        assert JobStatus.REQUESTED == "requested"
        assert JobStatus.QUEUED == "queued"
        assert JobStatus.ALLOCATING == "allocating"
        assert JobStatus.ALLOCATED == "allocated"
        assert JobStatus.BOOTING == "booting"
        assert JobStatus.INPROGRESS == "inprogress"
        assert JobStatus.CHECKPOINTING == "checkpointing"
        assert JobStatus.DONE == "done"
        assert JobStatus.ERROR == "error"
        assert JobStatus.RELEASING == "releasing"
        assert JobStatus.RELEASED == "released"
        assert JobStatus.COMPLETE == "complete"
    
    def test_job_detail_creation(self):
        """Test JobDetail creation with valid data."""
        job_data = {
            "JobRequestID": "caef4de5-00e2-4483-b23c-b4bd3bbb5876",
            "Name": "Test Job",
            "Type": "IWPS",  # Valid JobType
            "JobRequestStatus": "inprogress",  # Valid JobStatus
            "RequestedOn": "2024-01-01T10:00:00Z",
            "owner": "test@intel.com"
        }
        
        job = JobDetail(**job_data)
        assert job.job_id == "caef4de5-00e2-4483-b23c-b4bd3bbb5876"
        assert job.name == "Test Job"
        assert job.job_type == JobType.IWPS
        assert job.status == JobStatus.INPROGRESS
    
    def test_job_detail_validation(self):
        """Test job detail validation."""
        # Test invalid job type
        with pytest.raises(ValidationError):
            JobDetail(
                job_id="test-id",
                name="Test Job",
                job_type="InvalidType",  # Invalid job type
                status=JobStatus.COMPLETE,
                created_at=datetime.utcnow().isoformat(),
                owner="test@intel.com"
            )
    
    def test_iss_jobs_response(self):
        """Test ISSJobsResponse creation and validation."""
        response_data = {
            "jobs": [
                {
                    "JobRequestID": "caef4de5-00e2-4483-b23c-b4bd3bbb5876",
                    "Name": "Test Job 1",
                    "Type": "IWPS", 
                    "JobRequestStatus": "inprogress",
                    "RequestedOn": "2024-01-01T10:00:00Z",
                    "owner": "test1@intel.com"
                },
                {
                    "JobRequestID": "b1234567-89ab-cdef-0123-456789abcdef",
                    "Name": "Test Job 2", 
                    "Type": "ISIM",
                    "JobRequestStatus": "done",
                    "RequestedOn": "2024-01-01T11:00:00Z",
                    "owner": "test2@intel.com"
                }
            ],
            "count": 2,  # Fixed: should be "count" not "total"
            "page": 1,
            "per_page": 100
        }
        
        response = ISSJobsResponse(**response_data)
        assert len(response.jobs) == 2
        assert response.count == 2
        assert response.jobs[0].job_id == "caef4de5-00e2-4483-b23c-b4bd3bbb5876"


class TestResponseModels:
    """Test API response models."""
    
    def test_job_detail_response(self):
        """Test JobDetailResponse creation."""
        job_data = {
            "JobRequestID": "caef4de5-00e2-4483-b23c-b4bd3bbb5876",
            "Name": "Test Job",
            "Type": "IWPS",
            "JobRequestStatus": "inprogress", 
            "RequestedOn": "2024-01-01T10:00:00Z",
            "owner": "test@intel.com"
        }
        
        response = JobDetailResponse(job=JobDetail(**job_data))
        assert response.job.job_id == "caef4de5-00e2-4483-b23c-b4bd3bbb5876"
        assert isinstance(response.job, JobDetail)
    
    def test_file_list_response(self):
        """Test file list response model."""
        files = [
            "sim.bbprofile",
            "sim.funcprofile",
            "sim.insprofile",
            "sim.out"
        ]
        
        response = FileListResponse(
            files=files,
            total_files=len(files),
            job_id="caef4de5-00e2-4483-b23c-b4bd3bbb5876"
        )
        
        assert len(response.files) == 4
        assert response.total_files == 4
        assert response.job_id == "caef4de5-00e2-4483-b23c-b4bd3bbb5876"
        assert "sim.bbprofile" in response.files
