"""Main FastAPI application with auto-bedrock-chat-fastapi integration."""

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from auto_bedrock_chat_fastapi import add_bedrock_chat
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from .api import jobs_router, platforms_router
# Temporarily disabled for cleanup
# from .api import analysis_router, instances_router
from .config import Settings, get_settings
from .exceptions import (
    AnalysisError,
    AuthenticationError,
    ConfigurationError,
    FileServiceError,
    ISSClientError,
)
from .models.response_models import ErrorResponse, HealthResponse
from .utils.logging import setup_logging


class DateTimeJSONResponse(JSONResponse):
    """Custom JSONResponse that handles datetime serialization."""
    
    def render(self, content: Any) -> bytes:
        """Render content as JSON with datetime support."""
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=self._json_serial,
        ).encode("utf-8")
    
    def _json_serial(self, obj):
        """JSON serializer for objects not serializable by default json code."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Workload Analyzer application")

    try:
        # Initialize services and validate configuration
        settings = get_settings()

        # Validate critical configuration
        if not settings.get_iss_url():
            raise ConfigurationError("ISS_API_URL is required")

        if not settings.aws_region:
            raise ConfigurationError("AWS_REGION is required")

        # Test ISS connectivity (optional, non-blocking)
        try:
            from .services.auth_service import AuthService
            from .services.iss_client import ISSClient

            auth_service = AuthService(settings)
            async with ISSClient(settings, auth_service) as iss_client:
                # Test basic connectivity
                await iss_client.get_platforms({})

            logger.info("ISS connectivity verified")

        except Exception as e:
            logger.warning(f"ISS connectivity test failed: {e}")
            raise e

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Workload Analyzer application")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Get settings
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title="Intel Workload Analyzer",
        description="AI-powered analysis platform for Intel Simulation Service workloads",
        version="1.0.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "health",
                "description": "Health check and system status endpoints",
            },
            {
                "name": "jobs",
                "description": "Job management and analysis operations",
            },
            {
                "name": "platforms",
                "description": "Platform information and utilization analysis",
            },
            # {
            #     "name": "instances",
            #     "description": "Instance monitoring and resource tracking",
            # },
            # {
            #     "name": "analysis",
            #     "description": "AI-powered workload analysis and insights",
            # },
            {
                "name": "chat",
                "description": "AI assistant for interactive workload analysis",
            },
        ],
    )

    # Add middleware
    setup_middleware(app, settings)

    # Add exception handlers
    setup_exception_handlers(app)

    # Include routers
    setup_routers(app)

    # Setup auto-bedrock-chat integration
    setup_ai_integration(app, settings)

    return app


def setup_middleware(app: FastAPI, settings: Settings) -> None:
    """Setup application middleware."""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Trusted host middleware for production
    if settings.app_env == "production":
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log incoming requests with timing."""
        start_time = time.time()

        # Generate request ID for correlation
        import uuid

        request_id = str(uuid.uuid4())[:8]

        # Add request ID to request state
        request.state.request_id = request_id

        # Log request arrival
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"🚀 [{request_id}] {request.method} {request.url.path} - Client: {client_ip}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )

        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response completion
            status_emoji = "✅" if response.status_code < 400 else "❌"
            logger.info(
                f"{status_emoji} [{request_id}] {response.status_code} - {process_time:.3f}s",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}s",
                    "response_size": response.headers.get("content-length", "unknown"),
                },
            )

            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"💥 [{request_id}] Request FAILED: {str(e)} - {process_time:.3f}s",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": f"{process_time:.3f}s",
                },
            )
            raise


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers."""

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        """Handle authentication errors."""
        logger.error(f"Authentication error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(
                error="Authentication Error",
                message=str(exc),
                request_id=getattr(request.state, "request_id", None),
            ).dict(),
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(request: Request, exc: ConfigurationError):
        """Handle configuration errors."""
        logger.error(f"Configuration error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Configuration Error",
                message="Service configuration error",
                request_id=getattr(request.state, "request_id", None),
            ).dict(),
        )

    @app.exception_handler(ISSClientError)
    async def iss_client_error_handler(request: Request, exc: ISSClientError):
        """Handle ISS client errors."""
        logger.error(f"ISS client error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(
                error="External Service Error",
                message="Intel Simulation Service unavailable",
                request_id=getattr(request.state, "request_id", None),
            ).dict(),
        )

    @app.exception_handler(FileServiceError)
    async def file_service_error_handler(request: Request, exc: FileServiceError):
        """Handle file service errors."""
        logger.error(f"File service error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(
                error="File Service Error",
                message="File service unavailable",
                request_id=getattr(request.state, "request_id", None),
            ).dict(),
        )

    @app.exception_handler(AnalysisError)
    async def analysis_error_handler(request: Request, exc: AnalysisError):
        """Handle analysis errors."""
        logger.error(f"Analysis error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="Analysis Error",
                message=str(exc),
                request_id=getattr(request.state, "request_id", None),
            ).dict(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return DateTimeJSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP Error",
                message=exc.detail,
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return DateTimeJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal Server Error",
                message="An unexpected error occurred",
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )


def setup_routers(app: FastAPI) -> None:
    """Setup API routers."""

    # Health check endpoint
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
        summary="Health check",
        description="Check application health and service status",
    )
    async def health_check():
        """Health check endpoint."""
        from datetime import datetime

        settings = get_settings()

        # Check service connectivity
        iss_status = "unknown"
        bedrock_status = "unknown"

        try:
            # Quick ISS connectivity check
            from .services.auth_service import AuthService
            from .services.iss_client import ISSClient

            auth_service = AuthService(settings)
            async with ISSClient(settings, auth_service) as iss_client:
                await iss_client.get_platforms(limit=1)
            iss_status = "healthy"

        except Exception:
            iss_status = "unhealthy"

        # Bedrock status (simplified)
        bedrock_status = "healthy" if settings.bedrock_model_id else "not_configured"

        # System metrics (optional)
        memory_usage = None
        try:
            import psutil
            memory_usage = psutil.virtual_memory().used / (1024 * 1024)  # MB
        except ImportError:
            # psutil not available, skip memory monitoring
            pass

        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            iss_api_status=iss_status,
            bedrock_status=bedrock_status,
            memory_usage_mb=memory_usage,
        )

    # Include API routers
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(platforms_router, prefix="/api/v1")
    # Temporarily disabled for cleanup
    # app.include_router(instances_router, prefix="/api/v1")
    # app.include_router(analysis_router, prefix="/api/v1")


def setup_ai_integration(app: FastAPI, settings: Settings) -> None:
    """Setup auto-bedrock-chat integration."""

    try:
        # Only setup if Bedrock is configured
        if not settings.bedrock_model_id:
            logger.warning("Bedrock model not configured - AI chat will be unavailable")
            return
        
        logger.debug(f"Bedrock Allowed Paths: {settings.bedrock_allowed_paths}")
        logger.debug(f"Bedrock Excluded Paths: {settings.bedrock_excluded_paths}")

        # Setup with path exclusions for API endpoints
        add_bedrock_chat(
            app,
            # These list fields need to be set in code (Pydantic v2 limitation)
            allowed_paths=settings.bedrock_allowed_paths,
            excluded_paths=settings.bedrock_excluded_paths,
            # UI Configuration
            ui_title=settings.bedrock_ui_title,
            ui_welcome_message=settings.bedrock_ui_welcome_message,
            # All other settings (model_id, temperature, endpoints, etc.) come from .env
            enable_tool_auth=False,
        )

        logger.info("Auto-bedrock-chat integration configured successfully")

    except Exception as e:
        logger.error(f"Failed to setup AI integration: {e}")
        # Don't fail app startup, just log the error


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    # Run the application
    uvicorn.run(
        "workload_analyzer.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
        access_log=True,
    )
