"""Authentication service for AWS Secrets Manager integration."""

import json
import logging
from typing import Dict, Optional

import boto3
from pydantic import BaseModel

from ..config import Settings
from ..exceptions import AuthenticationError, ConfigurationError

logger = logging.getLogger(__name__)


class Credentials(BaseModel):
    """Credentials model for ISS API."""

    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None
    expires_at: Optional[str] = None


class AuthService:
    """Service for managing authentication and credentials."""

    def __init__(self, settings: Settings):
        """Initialize the authentication service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._client: Optional[boto3.client] = None
        self._cached_credentials: Optional[Credentials] = None

    @property
    def client(self) -> boto3.client:
        """Get or create the Secrets Manager client."""
        if self._client is None:
            try:
                session = boto3.Session(
                    aws_access_key_id=self.settings.aws_access_key_id_iss,
                    aws_secret_access_key=self.settings.aws_secret_access_key_iss,
                    region_name=self.settings.aws_region_iss,
                )
                self._client = session.client("secretsmanager")
                logger.info("Initialized AWS Secrets Manager client with ISS credentials")
            except Exception as e:
                logger.error(f"Failed to initialize AWS client: {e}")
                raise ConfigurationError(f"AWS configuration error: {e}")

        return self._client

    async def get_iss_credentials(self, force_refresh: bool = False) -> Credentials:
        """Get ISS API credentials from AWS Secrets Manager.

        Args:
            force_refresh: Force refresh cached credentials

        Returns:
            ISS API credentials

        Raises:
            AuthenticationError: If credentials cannot be retrieved
        """
        if self._cached_credentials and not force_refresh:
            logger.debug("Using cached ISS credentials")
            return self._cached_credentials

        try:
            logger.info(
                f"Retrieving ISS credentials from secret: {self.settings.client_secret_name}"
            )

            response = self.client.get_secret_value(
                SecretId=self.settings.client_secret_name
            )
            secret_string = response["SecretString"]
            secret_data = json.loads(secret_string)

            # Validate required fields - support both username/password and OAuth2 client credentials
            has_user_pass = "username" in secret_data and "password" in secret_data
            has_oauth_creds = "client_id" in secret_data and "client_secret" in secret_data
            
            if not has_user_pass and not has_oauth_creds:
                raise AuthenticationError(
                    "Secret must contain either (username, password) or (client_id, client_secret)"
                )

            credentials = Credentials(
                username=secret_data.get("username"),
                password=secret_data.get("password"),
                client_id=secret_data.get("client_id"),
                client_secret=secret_data.get("client_secret"),
                api_key=secret_data.get("api_key"),
                token=secret_data.get("token"),
                expires_at=secret_data.get("expires_at"),
            )

            self._cached_credentials = credentials
            
            # Log appropriate credential type
            if credentials.username:
                logger.info(f"Successfully retrieved ISS credentials for user: {credentials.username}")
            elif credentials.client_id:
                logger.info(f"Successfully retrieved ISS OAuth2 credentials for client: {credentials.client_id}")
            else:
                logger.info("Successfully retrieved ISS credentials")
                
            return credentials

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in secret {self.settings.client_secret_name}: {e}")
            raise AuthenticationError(f"Invalid credential format: {e}")
        except Exception as e:
            logger.error(f"Failed to retrieve ISS credentials: {e}")
            raise AuthenticationError(f"Credential retrieval failed: {e}")

    async def refresh_credentials(self) -> Credentials:
        """Force refresh of cached credentials.

        Returns:
            Fresh ISS API credentials
        """
        logger.info("Forcing refresh of ISS credentials")
        self._cached_credentials = None
        return await self.get_iss_credentials(force_refresh=True)

    def clear_cache(self) -> None:
        """Clear cached credentials."""
        logger.info("Clearing cached credentials")
        self._cached_credentials = None

    async def validate_credentials(self, credentials: Credentials) -> bool:
        """Validate credentials by testing API access.

        Args:
            credentials: Credentials to validate

        Returns:
            True if credentials are valid
        """
        try:
            # Import here to avoid circular dependency
            from .iss_client import ISSClient

            # Create temporary client to test credentials
            test_client = ISSClient(self.settings)
            test_client._credentials = credentials

            # Try to fetch platforms as a validation test
            await test_client.get_platforms(limit=1)
            
            # Log appropriate success message
            if credentials.username:
                logger.info(f"Credentials validated for user: {credentials.username}")
            elif credentials.client_id:
                logger.info(f"OAuth2 credentials validated for client: {credentials.client_id}")
            else:
                logger.info("Credentials validated successfully")
                
            return True

        except Exception as e:
            logger.warning(f"Credential validation failed: {e}")
            return False

    async def get_bedrock_credentials(self) -> Dict[str, str]:
        """Get Bedrock credentials (if stored separately).

        Returns:
            Bedrock credential dictionary

        Note:
            Currently uses the same AWS credentials as Secrets Manager.
            Override this method if Bedrock uses different credentials.
        """
        return {
            "aws_access_key_id": self.settings.aws_access_key_id or "",
            "aws_secret_access_key": self.settings.aws_secret_access_key or "",
            "region_name": self.settings.aws_region,
        }
