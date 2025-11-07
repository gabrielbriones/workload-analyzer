"""API router modules."""

from .jobs import router as jobs_router
from .platforms import router as platforms_router

# Temporarily disabled for cleanup
# from .analysis import router as analysis_router
# from .instances import router as instances_router

__all__ = [
    "jobs_router",
    "platforms_router",
    # "instances_router",
    # "analysis_router",
]
