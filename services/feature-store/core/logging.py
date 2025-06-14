"""
Logging configuration for Feature Store
"""

import logging
import sys
from typing import Any

import structlog

from .config import settings


def setup_logging() -> logging.Logger:
    """Setup structured logging"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameter(),
            structlog.processors.dict_tracebacks,
            (
                structlog.processors.JSONRenderer()
                if not settings.DEBUG
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Create logger
    logger = structlog.get_logger(settings.SERVICE_NAME)

    return logger


def get_logger(name: str) -> Any:
    """Get a logger instance"""
    return structlog.get_logger(name)


def log_feature_access(
    feature_set: str,
    features: list,
    entity_ids: list,
    latency_ms: float,
    cache_hit: bool = False,
) -> None:
    """Log feature access for monitoring"""
    logger = get_logger("feature_access")
    logger.info(
        "feature_access",
        feature_set=feature_set,
        features=features,
        entity_count=len(entity_ids),
        latency_ms=latency_ms,
        cache_hit=cache_hit,
    )


def log_feature_computation(
    feature_set: str,
    compute_type: str,
    duration_seconds: float,
    row_count: int,
    status: str,
) -> None:
    """Log feature computation metrics"""
    logger = get_logger("feature_computation")
    logger.info(
        "feature_computation",
        feature_set=feature_set,
        compute_type=compute_type,
        duration_seconds=duration_seconds,
        row_count=row_count,
        status=status,
    )
