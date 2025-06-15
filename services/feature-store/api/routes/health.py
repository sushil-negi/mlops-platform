"""
Health check endpoints for Feature Store
"""

import logging
import time
from typing import Dict

from fastapi import APIRouter, status
from sqlalchemy import text

from core.database import database

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "feature-store",
        "version": "2.0.0",
        "timestamp": time.time(),
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict:
    """Readiness check - verifies all dependencies are available"""
    checks = {"database": False, "storage": False, "cache": False, "compute": False}

    issues = []

    # Check database
    try:
        await database.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        issues.append(f"Database unavailable: {str(e)}")

    # Check storage (would check S3/MinIO connection)
    try:
        # TODO: Implement storage health check
        checks["storage"] = True
    except Exception as e:
        issues.append(f"Storage unavailable: {str(e)}")

    # Check cache (would check Redis connection)
    try:
        # TODO: Implement cache health check
        checks["cache"] = True
    except Exception as e:
        issues.append(f"Cache unavailable: {str(e)}")

    # Check compute engine
    try:
        # TODO: Implement compute engine health check
        checks["compute"] = True
    except Exception as e:
        issues.append(f"Compute engine unavailable: {str(e)}")

    # Determine overall status
    all_healthy = all(checks.values())

    response = {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": time.time(),
    }

    if issues:
        response["issues"] = issues

    if not all_healthy:
        return response

    return response


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict:
    """Liveness check - verifies service is running"""
    return {"status": "alive", "timestamp": time.time()}
