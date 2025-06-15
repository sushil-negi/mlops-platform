"""
Metrics endpoints for monitoring and observability
"""

import logging
import time
from typing import Any, Dict

import databases
from fastapi import APIRouter, Depends

from core.config import get_settings
from core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("/")
async def get_metrics(
    db: databases.Database = Depends(get_database),
) -> Dict[str, Any]:
    """Get service metrics"""

    try:
        # Database metrics
        db_result = await db.fetch_one("SELECT COUNT(*) as model_count FROM models")
        model_count = db_result["model_count"] if db_result else 0

        db_result = await db.fetch_one(
            "SELECT COUNT(*) as version_count FROM model_versions"
        )
        version_count = db_result["version_count"] if db_result else 0

        db_result = await db.fetch_one(
            "SELECT COUNT(*) as experiment_count FROM experiments"
        )
        experiment_count = db_result["experiment_count"] if db_result else 0

        db_result = await db.fetch_one(
            "SELECT COUNT(*) as artifact_count FROM artifacts"
        )
        artifact_count = db_result["artifact_count"] if db_result else 0

        # Recent activity (last 24 hours)
        recent_models = await db.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM models
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """
        )

        recent_versions = await db.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM model_versions
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """
        )

    except Exception as e:
        logger.error(f"Failed to fetch metrics from database: {e}")
        # Return default metrics if database is unavailable
        model_count = version_count = experiment_count = artifact_count = 0
        recent_models = recent_versions = {"count": 0}

    return {
        "service": "model-registry",
        "timestamp": time.time(),
        "counts": {
            "models": model_count,
            "versions": version_count,
            "experiments": experiment_count,
            "artifacts": artifact_count,
        },
        "activity_24h": {
            "new_models": recent_models["count"] if recent_models else 0,
            "new_versions": recent_versions["count"] if recent_versions else 0,
        },
        "system": {
            "version": "1.0.0",
            "environment": settings.DEBUG and "development" or "production",
        },
    }


@router.get("/prometheus")
async def get_prometheus_metrics(
    db: databases.Database = Depends(get_database),
) -> str:
    """Get metrics in Prometheus format"""

    try:
        # Fetch basic counts
        db_result = await db.fetch_one("SELECT COUNT(*) as model_count FROM models")
        model_count = db_result["model_count"] if db_result else 0

        db_result = await db.fetch_one(
            "SELECT COUNT(*) as version_count FROM model_versions"
        )
        version_count = db_result["version_count"] if db_result else 0

        # Generate Prometheus format
        metrics = f"""# HELP model_registry_models_total Total number of models
# TYPE model_registry_models_total counter
model_registry_models_total {model_count}

# HELP model_registry_versions_total Total number of model versions
# TYPE model_registry_versions_total counter
model_registry_versions_total {version_count}

# HELP model_registry_up Service availability
# TYPE model_registry_up gauge
model_registry_up 1
"""

        return metrics

    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        return """# HELP model_registry_up Service availability
# TYPE model_registry_up gauge
model_registry_up 0
"""
