"""
Logging configuration for Pipeline Orchestrator service
"""

import logging
import sys
from typing import Optional

from .config import get_settings

settings = get_settings()


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Setup application logging configuration

    Args:
        log_level: Optional override for log level
    """
    level = log_level or settings.LOG_LEVEL

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("databases").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Enable debug logging for our application in debug mode
    if settings.DEBUG:
        logging.getLogger("core").setLevel(logging.DEBUG)
        logging.getLogger("api").setLevel(logging.DEBUG)
        logging.getLogger("operator").setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
