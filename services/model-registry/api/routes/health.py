"""
Health check endpoints
"""

import logging
import os
import time
from typing import Any, Dict

import redis
from fastapi import APIRouter
from pydantic import BaseModel

from core.config import get_settings
from core.database import check_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


async def check_redis_connection() -> bool:
    """Check Redis connection health"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url, socket_timeout=5)
        await r.ping()
        return True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return False


async def check_storage_health() -> bool:
    """Check storage health (file system or S3)"""
    try:
        storage_path = os.getenv("STORAGE_PATH", "/tmp/model-registry")

        # Check if storage path exists and is writable
        if not os.path.exists(storage_path):
            os.makedirs(storage_path, exist_ok=True)

        # Test write operation
        test_file = os.path.join(storage_path, ".health_check")
        with open(test_file, "w") as f:
            f.write("health_check")

        # Test read operation
        with open(test_file, "r") as f:
            content = f.read()

        # Cleanup
        os.remove(test_file)

        return content == "health_check"
    except Exception as e:
        logger.warning(f"Storage health check failed: {e}")
        return False


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str
    timestamp: float
    version: str
    service: str
    checks: Dict[str, Any]


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""

    # Check database connection
    db_healthy = await check_db_connection()

    # Check Redis connection
    redis_healthy = await check_redis_connection()

    # Check storage health
    storage_healthy = await check_storage_health()

    checks = {
        "database": {
            "status": "healthy" if db_healthy else "unhealthy",
            "checked_at": time.time(),
        },
        "redis": {
            "status": "healthy" if redis_healthy else "unhealthy",
            "checked_at": time.time(),
        },
        "storage": {
            "status": "healthy" if storage_healthy else "unhealthy",
            "checked_at": time.time(),
        },
    }

    # Determine overall status
    overall_status = (
        "healthy"
        if all(check["status"] == "healthy" for check in checks.values())
        else "unhealthy"
    )

    return HealthResponse(
        status=overall_status,
        timestamp=time.time(),
        version="1.0.0",
        service="model-registry",
        checks=checks,
    )


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""

    # Check if service is ready to handle requests
    db_healthy = await check_db_connection()
    redis_healthy = await check_redis_connection()
    storage_healthy = await check_storage_health()

    if not db_healthy:
        return {"status": "not_ready", "reason": "database_unavailable"}

    if not redis_healthy:
        return {"status": "not_ready", "reason": "redis_unavailable"}

    if not storage_healthy:
        return {"status": "not_ready", "reason": "storage_unavailable"}

    return {"status": "ready", "timestamp": time.time()}
