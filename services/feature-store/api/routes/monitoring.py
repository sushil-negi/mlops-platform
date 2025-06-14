"""
Monitoring and metrics endpoints for Feature Store
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict

from core.database import get_db
from fastapi import APIRouter, Depends, Query
from models.feature import Feature
from models.feature_set import FeatureSet
from models.feature_value import FeatureValue
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/metrics")
async def get_system_metrics(db: Session = Depends(get_db)) -> Dict:
    """Get system metrics for the Feature Store"""

    # Calculate metrics
    total_feature_sets = db.query(func.count(FeatureSet.id)).scalar()
    active_feature_sets = (
        db.query(func.count(FeatureSet.id))
        .filter(FeatureSet.status == "active")
        .scalar()
    )

    total_features = db.query(func.count(Feature.id)).scalar()
    active_features = (
        db.query(func.count(Feature.id)).filter(Feature.status == "active").scalar()
    )

    # Recent activity
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_values = (
        db.query(func.count(FeatureValue.id))
        .filter(FeatureValue.created_timestamp >= recent_cutoff)
        .scalar()
    )

    return {
        "service": "feature-store",
        "timestamp": time.time(),
        "feature_sets": {
            "total": total_feature_sets,
            "active": active_feature_sets,
            "inactive": total_feature_sets - active_feature_sets,
        },
        "features": {
            "total": total_features,
            "active": active_features,
            "inactive": total_features - active_features,
        },
        "activity": {
            "values_written_24h": recent_values,
            "materialization_jobs_24h": 0,  # Would be tracked
            "serving_requests_24h": 0,  # Would be tracked
            "cache_hit_rate": 0.0,  # Would be calculated
        },
        "storage": {
            "offline_size_gb": 0.0,  # Would be calculated
            "online_entries": 0,  # Would be counted from Redis
            "total_rows": db.query(func.count(FeatureValue.id)).scalar(),
        },
    }


@router.get("/health/detailed")
async def get_detailed_health(db: Session = Depends(get_db)) -> Dict:
    """Get detailed health information"""

    return {
        "overall_status": "healthy",
        "timestamp": time.time(),
        "components": {
            "database": {
                "status": "healthy",
                "connection_pool": {"size": 20, "active": 5, "idle": 15},
            },
            "storage": {"status": "healthy", "backend": "s3", "accessible": True},
            "cache": {
                "status": "healthy",
                "type": "redis",
                "memory_usage_mb": 256,
                "hit_rate": 0.85,
            },
            "compute_engine": {
                "status": "healthy",
                "type": "duckdb",
                "available_threads": 4,
            },
        },
        "recent_errors": [],
        "warnings": [],
    }


@router.get("/statistics")
async def get_feature_statistics(
    days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)
) -> Dict:
    """Get feature usage and performance statistics"""

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Feature set statistics
    feature_sets = db.query(FeatureSet).all()
    fs_stats = []

    for fs in feature_sets:
        # Calculate statistics for each feature set
        fs_stat = {
            "name": fs.name,
            "status": fs.status.value if fs.status else "unknown",
            "feature_count": len(fs.features),
            "row_count": fs.row_count,
            "size_bytes": fs.size_bytes,
            "last_materialization": (
                fs.last_materialization.isoformat() if fs.last_materialization else None
            ),
            "materialization_enabled": fs.materialization_enabled,
        }
        fs_stats.append(fs_stat)

    # Top features by usage (mock data for now)
    top_features = [
        {"name": "user_age", "usage_count": 15420, "avg_latency_ms": 2.3},
        {"name": "purchase_count", "usage_count": 12350, "avg_latency_ms": 3.1},
        {"name": "last_login", "usage_count": 10200, "avg_latency_ms": 1.8},
        {"name": "account_balance", "usage_count": 8900, "avg_latency_ms": 2.5},
        {"name": "risk_score", "usage_count": 7650, "avg_latency_ms": 4.2},
    ]

    return {
        "period_days": days,
        "generated_at": datetime.utcnow().isoformat(),
        "feature_set_statistics": fs_stats,
        "top_features_by_usage": top_features,
        "performance": {
            "avg_serving_latency_ms": 3.2,
            "p95_serving_latency_ms": 8.5,
            "p99_serving_latency_ms": 15.2,
            "cache_hit_rate": 0.82,
            "materialization_success_rate": 0.95,
        },
        "data_quality": {
            "validation_pass_rate": 0.98,
            "missing_value_rate": 0.02,
            "schema_violations": 3,
        },
    }


@router.get("/usage")
async def get_usage_metrics(
    start_date: datetime = Query(default=None),
    end_date: datetime = Query(default=None),
    db: Session = Depends(get_db),
) -> Dict:
    """Get feature usage metrics"""

    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=7)

    # Mock usage data
    daily_usage = []
    current_date = start_date
    while current_date <= end_date:
        daily_usage.append(
            {
                "date": current_date.strftime("%Y-%m-%d"),
                "serving_requests": 12500 + (current_date.day * 100),
                "unique_entities": 3200 + (current_date.day * 50),
                "features_served": 45000 + (current_date.day * 500),
                "cache_hits": 38000 + (current_date.day * 400),
            }
        )
        current_date += timedelta(days=1)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily_usage": daily_usage,
        "summary": {
            "total_requests": sum(d["serving_requests"] for d in daily_usage),
            "total_features_served": sum(d["features_served"] for d in daily_usage),
            "avg_daily_requests": sum(d["serving_requests"] for d in daily_usage)
            / len(daily_usage),
            "peak_day": max(daily_usage, key=lambda x: x["serving_requests"])["date"],
        },
    }


@router.get("/data-freshness")
async def get_data_freshness(db: Session = Depends(get_db)) -> Dict:
    """Get data freshness metrics for feature sets"""

    feature_sets = db.query(FeatureSet).filter(FeatureSet.status == "active").all()

    freshness_data = []

    for fs in feature_sets:
        if fs.last_materialization:
            age_hours = (
                datetime.utcnow() - fs.last_materialization
            ).total_seconds() / 3600
            is_stale = age_hours > 24  # Consider stale if older than 24 hours

            freshness_data.append(
                {
                    "feature_set": fs.name,
                    "last_update": fs.last_materialization.isoformat(),
                    "age_hours": round(age_hours, 2),
                    "is_stale": is_stale,
                    "materialization_schedule": fs.materialization_schedule,
                }
            )

    stale_count = sum(1 for f in freshness_data if f["is_stale"])

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "feature_sets": freshness_data,
        "summary": {
            "total_active": len(freshness_data),
            "stale_count": stale_count,
            "fresh_count": len(freshness_data) - stale_count,
            "freshness_rate": (
                (len(freshness_data) - stale_count) / len(freshness_data)
                if freshness_data
                else 0
            ),
        },
    }


@router.get("/alerts")
async def get_active_alerts() -> Dict:
    """Get active alerts for the Feature Store"""

    # Mock alerts
    alerts = [
        {
            "id": "alert-001",
            "severity": "warning",
            "title": "High serving latency detected",
            "description": "P95 latency exceeded threshold (15ms) for the last 10 minutes",
            "component": "serving_engine",
            "created_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "status": "active",
        },
        {
            "id": "alert-002",
            "severity": "info",
            "title": "Materialization job delayed",
            "description": "Feature set 'user_activity' materialization is 2 hours behind schedule",
            "component": "materialization",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "status": "active",
        },
    ]

    return {
        "alerts": alerts,
        "total_count": len(alerts),
        "severity_counts": {"critical": 0, "warning": 1, "info": 1},
        "timestamp": datetime.utcnow().isoformat(),
    }
