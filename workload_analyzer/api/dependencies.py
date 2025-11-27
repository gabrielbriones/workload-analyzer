"""Shared FastAPI dependencies for API endpoints."""

from fastapi import Depends, Header, HTTPException, status

from ..config import Settings, get_settings
from ..services.iss_client import ISSClient
from ..services.file_service import FileService


def get_bearer_token(authorization: str = Header(...)) -> str:
    """Extract and validate bearer token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Bearer token
        
    Raises:
        HTTPException: If token format is invalid
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )
    return authorization[7:]  # Remove "Bearer " prefix


def get_iss_client(
    bearer_token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings)
) -> ISSClient:
    """Dependency to get ISS client with bearer token."""
    return ISSClient(settings, bearer_token)


async def get_file_service(
    bearer_token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings),
    iss_client: ISSClient = Depends(get_iss_client)
) -> FileService:
    """Dependency to get file service with bearer token."""
    return FileService(settings, bearer_token, iss_client)
