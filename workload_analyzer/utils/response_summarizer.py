"""Utilities for summarizing large API responses to reduce LLM context usage."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def summarize_job(job_data: Dict[str, Any], include_details: bool = False) -> Dict[str, Any]:
    """
    Summarize a job object to reduce token count for LLM processing.
    
    Includes only essential fields needed for job analysis while removing
    verbose nested structures that consume context tokens.
    
    Args:
        job_data: Full job data from ISS API
        include_details: If True, include more fields (for direct API clients).
                        If False, return minimal summary (for LLM).
    
    Returns:
        Summarized job object
    """
    # Essential fields that should always be included
    essential_fields = {
        'JobRequestID': job_data.get('JobRequestID'),
        'Name': job_data.get('Name'),
        'Type': job_data.get('Type'),
        'JobRequestStatus': job_data.get('JobRequestStatus'),
        'Queue': job_data.get('Queue'),
        'TenantID': job_data.get('TenantID'),
        'RequestedBy': job_data.get('RequestedBy'),
        'RequestedOn': job_data.get('RequestedOn'),
    }
    
    if include_details:
        # For non-LLM clients, include more fields
        essential_fields.update({
            'PlatformID': job_data.get('PlatformID'),
            'priority': job_data.get('priority'),
            'owner': job_data.get('owner'),
            'project': job_data.get('project'),
            'JobResult': job_data.get('JobResult'),
            'LastUpdatedOn': job_data.get('LastUpdatedOn'),
            'LastUpdatedBy': job_data.get('LastUpdatedBy'),
        })
    
    # Include workload type if available (compact form)
    if 'Workload' in job_data and isinstance(job_data['Workload'], dict):
        workload_type = job_data['Workload'].get('WorkloadType')
        if workload_type:
            essential_fields['WorkloadType'] = workload_type
    
    # Include platform info if available (compact form)
    if 'TargetPlatform' in job_data and isinstance(job_data['TargetPlatform'], dict):
        platform = job_data['TargetPlatform']
        platform_summary = {
            'PlatformID': platform.get('PlatformID'),
            'PlatformName': platform.get('PlatformName'),
            'PlatformType': platform.get('PlatformType'),
            'PlatformMemorySize': platform.get('PlatformMemorySize'),
        }
        # Only include if we have meaningful data
        if any(platform_summary.values()):
            essential_fields['Platform'] = platform_summary
    
    return essential_fields


def summarize_jobs_response(
    jobs_response: Dict[str, Any], 
    max_jobs: Optional[int] = None,
    max_chars_per_response: int = 50000,
) -> Dict[str, Any]:
    """
    Summarize a jobs response to reduce LLM context usage.
    
    Args:
        jobs_response: Response from ISSClient.get_jobs()
        max_jobs: Maximum number of jobs to include (None = all)
        max_chars_per_response: Maximum characters in response before truncation
    
    Returns:
        Summarized response
    """
    jobs = jobs_response.get('jobs', [])
    
    # Summarize each job
    summarized_jobs = []
    total_chars = 0
    
    for job in jobs:
        summarized_job = summarize_job(job, include_details=False)
        job_str = str(summarized_job)
        
        # Check if adding this job would exceed character limit
        if total_chars + len(job_str) > max_chars_per_response:
            logger.warning(
                f"Jobs response truncated: reached {total_chars} chars "
                f"(limit: {max_chars_per_response}). "
                f"Returned {len(summarized_jobs)} of {len(jobs)} jobs."
            )
            break
        
        summarized_jobs.append(summarized_job)
        total_chars += len(job_str)
        
        # Check max_jobs limit
        if max_jobs and len(summarized_jobs) >= max_jobs:
            break
    
    # Return summarized response
    return {
        'jobs': summarized_jobs,
        'count': len(summarized_jobs),
        'total_available': len(jobs),
        'continuation_token': jobs_response.get('continuation_token'),
        '_summary_info': {
            'original_count': len(jobs),
            'summarized_count': len(summarized_jobs),
            'approximate_chars': total_chars,
            'truncated': len(summarized_jobs) < len(jobs)
        }
    }


def summarize_platform(platform_data: Dict[str, Any], include_details: bool = False) -> Dict[str, Any]:
    """
    Summarize a platform object to reduce token count.
    
    Args:
        platform_data: Full platform data from ISS API
        include_details: If True, include more detailed specifications
    
    Returns:
        Summarized platform object
    """
    essential = {
        'PlatformID': platform_data.get('PlatformID'),
        'PlatformName': platform_data.get('PlatformName'),
        'PlatformType': platform_data.get('PlatformType'),
        'PlatformMemorySize': platform_data.get('PlatformMemorySize'),
        'Available': platform_data.get('Available'),
    }
    
    if include_details:
        essential.update({
            'Description': platform_data.get('Description'),
            'Version': platform_data.get('Version'),
            'MaintenanceMode': platform_data.get('MaintenanceMode'),
        })
        
        # Include key Simics parameters
        if 'SimicsParameters' in platform_data:
            params = platform_data['SimicsParameters']
            essential['CoreCount'] = params.get('n_cores')
            essential['Threads'] = params.get('n_threads')
            essential['MemoryPerDimm'] = params.get('memory_per_dimm')
    
    return essential


def summarize_file_list(
    files: List[Dict[str, Any]], 
    max_files: int = 20,
) -> List[Dict[str, Any]]:
    """
    Summarize a file list to reduce LLM context.
    
    Args:
        files: List of file objects
        max_files: Maximum number of files to include
    
    Returns:
        Summarized file list
    """
    if len(files) > max_files:
        logger.warning(
            f"File list truncated: {len(files)} files > {max_files} max. "
            f"Showing first {max_files} files."
        )
        files = files[:max_files]
    
    # Keep only essential file info
    summarized = []
    for file in files:
        summarized.append({
            'name': file.get('name') or file.get('FileName'),
            'size': file.get('size') or file.get('Size'),
            'modified': file.get('modified') or file.get('LastModified'),
        })
    
    return summarized


def estimate_token_count(text: str, model: str = "claude") -> int:
    """
    Rough estimate of token count for text.
    
    Claude models typically use ~4 chars per token on average.
    This is a rough approximation.
    
    Args:
        text: Text to estimate
        model: Model type (claude, gpt, etc.)
    
    Returns:
        Estimated token count
    """
    # Rough estimates: Claude ~4 chars/token, GPT ~3.5 chars/token
    if model.lower() == "gpt":
        return int(len(text) / 3.5)
    else:  # Claude
        return int(len(text) / 4)
