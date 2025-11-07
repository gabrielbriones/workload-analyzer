"""
Logging configuration for the Workload Analyzer.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from workload_analyzer.config import settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        log_message = super().format(record)
        if record.levelname in self.COLORS:
            log_message = f"{self.COLORS[record.levelname]}{log_message}{self.RESET}"
        return log_message


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    include_request_id: bool = True,
) -> None:
    """
    Set up logging configuration for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging output
        include_request_id: Whether to include request ID in logs
    """
    log_level = level or settings.log_level

    # Create formatters
    console_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if include_request_id:
        console_format = (
            "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"
        )

    file_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    if include_request_id:
        file_format = "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(funcName)s:%(lineno)d - %(message)s"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    if settings.app_env == "development":
        console_formatter = ColoredFormatter(console_format)
    else:
        console_formatter = logging.Formatter(console_format)

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set third-party library log levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    # Add request ID filter if needed
    if include_request_id:
        add_request_id_filter()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class RequestIDFilter(logging.Filter):
    """Filter to add request ID to log records."""

    def filter(self, record):
        # Add default request_id if not present
        if not hasattr(record, "request_id"):
            record.request_id = "no-request-id"
        return True


def add_request_id_filter():
    """Add request ID filter to all handlers."""
    root_logger = logging.getLogger()
    request_filter = RequestIDFilter()

    for handler in root_logger.handlers:
        handler.addFilter(request_filter)
