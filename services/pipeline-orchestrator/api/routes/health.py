"""
Health check endpoints for Pipeline Orchestrator
"""

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from core.config import get_settings
from core.database import check_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


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

    # Check scheduler (would need global access to scheduler)
    scheduler_healthy = True  # Placeholder

    checks = {
        "database": {
            "status": "healthy" if db_healthy else "unhealthy",
            "checked_at": time.time(),
        },
        "scheduler": {
            "status": "healthy" if scheduler_healthy else "unhealthy",
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
        version="2.0.0",
        service="pipeline-orchestrator",
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

    if not db_healthy:
        return {"status": "not_ready", "reason": "database_unavailable"}

    return {"status": "ready", "timestamp": time.time()}
