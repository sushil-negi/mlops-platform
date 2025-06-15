"""
Health check endpoints for Experiment Tracking service
"""

import logging
import time
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from core.config import get_settings

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
    db_healthy = True  # TODO: Implement actual DB check

    # Check Redis connection
    redis_healthy = True  # TODO: Implement actual Redis check

    # Check storage connection
    storage_healthy = True  # TODO: Implement actual storage check

    # Check MLOps service connectivity
    model_registry_healthy = True  # TODO: Implement actual check
    pipeline_orchestrator_healthy = True  # TODO: Implement actual check
    feature_store_healthy = True  # TODO: Implement actual check

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
        "model_registry": {
            "status": "healthy" if model_registry_healthy else "unhealthy",
            "url": settings.registry_service_url,
            "checked_at": time.time(),
        },
        "pipeline_orchestrator": {
            "status": "healthy" if pipeline_orchestrator_healthy else "unhealthy",
            "url": settings.pipeline_orchestrator_url,
            "checked_at": time.time(),
        },
        "feature_store": {
            "status": "healthy" if feature_store_healthy else "unhealthy",
            "url": settings.feature_store_url,
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
        service="experiment-tracking",
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
    db_healthy = True  # TODO: Implement actual check

    if not db_healthy:
        return {"status": "not_ready", "reason": "database_unavailable"}

    return {"status": "ready", "timestamp": time.time()}


@router.get("/info")
async def service_info():
    """Detailed service information"""
    return {
        "name": "experiment-tracking",
        "version": "2.0.0",
        "description": "Comprehensive ML experiment management platform",
        "environment": settings.environment,
        "features": [
            "experiment_management",
            "run_tracking",
            "metric_logging",
            "hyperparameter_optimization",
            "visualization",
            "model_comparison",
            "mlops_integration",
        ],
        "integrations": [
            {
                "service": "model-registry",
                "url": settings.registry_service_url,
                "description": "Model registration and management",
            },
            {
                "service": "pipeline-orchestrator",
                "url": settings.pipeline_orchestrator_url,
                "description": "Pipeline execution and orchestration",
            },
            {
                "service": "feature-store",
                "url": settings.feature_store_url,
                "description": "Feature serving and management",
            },
        ],
        "configuration": {
            "max_concurrent_experiments": settings.max_concurrent_experiments,
            "max_runs_per_experiment": settings.max_runs_per_experiment,
            "enable_real_time_metrics": settings.enable_real_time_metrics,
            "enable_hpo": settings.enable_hpo,
            "healthcare_validation": settings.enable_healthcare_validation,
        },
    }
