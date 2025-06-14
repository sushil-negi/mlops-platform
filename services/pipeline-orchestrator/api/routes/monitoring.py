"""
Monitoring and metrics endpoints for Pipeline Orchestrator
"""

import logging
import time
from typing import Dict

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/metrics")
async def get_system_metrics() -> Dict:
    """Get system metrics for the pipeline orchestrator"""

    # Mock metrics - would be replaced with actual data from scheduler and resource manager
    return {
        "service": "pipeline-orchestrator",
        "timestamp": time.time(),
        "scheduler": {
            "active_runs": 3,
            "queued_runs": 1,
            "completed_runs_24h": 15,
            "total_runs": 150,
            "success_rate": 0.92,
        },
        "resources": {
            "cpu_utilization": 45.2,
            "memory_utilization": 62.8,
            "gpu_utilization": 23.1,
            "available_workers": 7,
            "total_workers": 10,
        },
        "tasks": {
            "tasks_executed_24h": 85,
            "avg_task_duration_seconds": 45.6,
            "task_failure_rate": 0.08,
            "most_common_operators": [
                {"operator": "data_ingestion", "count": 25},
                {"operator": "model_training", "count": 18},
                {"operator": "data_validation", "count": 22},
            ],
        },
        "pipelines": {
            "total_pipelines": 12,
            "active_pipelines": 8,
            "avg_pipeline_duration_minutes": 15.4,
        },
    }


@router.get("/health/detailed")
async def get_detailed_health() -> Dict:
    """Get detailed health information"""

    return {
        "overall_status": "healthy",
        "timestamp": time.time(),
        "components": {
            "scheduler": {
                "status": "healthy",
                "uptime_seconds": 3600,
                "last_heartbeat": time.time() - 30,
            },
            "resource_manager": {
                "status": "healthy",
                "available_resources": {
                    "cpu_cores": 12.5,
                    "memory_gb": 32.0,
                    "gpu_count": 2,
                },
            },
            "task_executor": {
                "status": "healthy",
                "available_operators": [
                    "data_ingestion",
                    "data_validation",
                    "model_training",
                    "model_registration",
                    "custom_script",
                ],
            },
            "storage": {
                "status": "healthy",
                "pipeline_definitions": 12,
                "run_artifacts": 145,
            },
        },
        "recent_activity": {
            "pipelines_started_1h": 5,
            "tasks_completed_1h": 32,
            "errors_1h": 2,
        },
    }


@router.get("/operators")
async def get_available_operators() -> Dict:
    """Get list of available task operators"""

    operators = [
        {
            "type": "data_ingestion",
            "description": "Ingest data from various sources",
            "category": "data",
            "resource_requirements": {"cpu": 1.0, "memory_gb": 2.0, "gpu": 0},
            "parameters": [
                {"name": "source_type", "type": "string", "required": True},
                {"name": "source_path", "type": "string", "required": True},
                {"name": "output_path", "type": "string", "required": False},
            ],
        },
        {
            "type": "data_validation",
            "description": "Validate data quality and schema",
            "category": "data",
            "resource_requirements": {"cpu": 0.5, "memory_gb": 1.0, "gpu": 0},
            "parameters": [
                {"name": "input_path", "type": "string", "required": True},
                {"name": "validation_rules", "type": "object", "required": False},
                {"name": "max_error_rate", "type": "number", "required": False},
            ],
        },
        {
            "type": "model_training",
            "description": "Train machine learning models",
            "category": "ml",
            "resource_requirements": {"cpu": 4.0, "memory_gb": 8.0, "gpu": 1},
            "parameters": [
                {"name": "model_type", "type": "string", "required": True},
                {"name": "algorithm", "type": "string", "required": True},
                {"name": "hyperparameters", "type": "object", "required": False},
                {"name": "training_data_path", "type": "string", "required": True},
            ],
        },
        {
            "type": "model_registration",
            "description": "Register trained models in model registry",
            "category": "ml",
            "resource_requirements": {"cpu": 0.5, "memory_gb": 1.0, "gpu": 0},
            "parameters": [
                {"name": "model_name", "type": "string", "required": True},
                {"name": "model_version", "type": "string", "required": False},
                {"name": "description", "type": "string", "required": False},
                {"name": "tags", "type": "array", "required": False},
            ],
        },
        {
            "type": "custom_script",
            "description": "Execute custom scripts and commands",
            "category": "utility",
            "resource_requirements": {"cpu": 1.0, "memory_gb": 2.0, "gpu": 0},
            "parameters": [
                {"name": "script_type", "type": "string", "required": True},
                {"name": "script_content", "type": "string", "required": False},
                {"name": "script_path", "type": "string", "required": False},
            ],
        },
    ]

    return {
        "operators": operators,
        "total_count": len(operators),
        "categories": list(set(op["category"] for op in operators)),
    }


@router.get("/statistics")
async def get_pipeline_statistics(days: int = Query(7, ge=1, le=30)) -> Dict:
    """Get pipeline execution statistics"""

    # Mock statistics data
    return {
        "period_days": days,
        "generated_at": time.time(),
        "execution_stats": {
            "total_runs": 45,
            "successful_runs": 41,
            "failed_runs": 4,
            "cancelled_runs": 0,
            "success_rate": 0.911,
            "avg_duration_minutes": 12.5,
            "total_compute_hours": 18.7,
        },
        "operator_usage": [
            {"operator": "data_ingestion", "executions": 45, "success_rate": 0.978},
            {"operator": "data_validation", "executions": 45, "success_rate": 0.956},
            {"operator": "model_training", "executions": 38, "success_rate": 0.895},
            {"operator": "model_registration", "executions": 34, "success_rate": 1.0},
            {"operator": "custom_script", "executions": 12, "success_rate": 0.917},
        ],
        "resource_efficiency": {
            "avg_cpu_utilization": 0.78,
            "avg_memory_utilization": 0.65,
            "avg_gpu_utilization": 0.42,
            "peak_concurrent_tasks": 8,
            "resource_waste_percentage": 12.3,
        },
        "error_analysis": {
            "most_common_failures": [
                {"error": "data_validation_timeout", "count": 2},
                {"error": "insufficient_training_data", "count": 1},
                {"error": "model_convergence_failure", "count": 1},
            ],
            "retry_success_rate": 0.75,
        },
        "trends": {
            "daily_runs": [6, 7, 5, 8, 6, 7, 6],
            "daily_success_rate": [0.83, 0.86, 1.0, 0.88, 1.0, 0.86, 1.0],
            "daily_avg_duration": [11.2, 13.1, 10.8, 14.2, 11.9, 12.8, 13.5],
        },
    }


@router.get("/alerts")
async def get_active_alerts() -> Dict:
    """Get active system alerts"""

    # Mock alerts
    alerts = [
        {
            "id": "alert-001",
            "severity": "warning",
            "title": "High resource utilization",
            "description": "CPU utilization has been above 80% for the last 30 minutes",
            "component": "resource_manager",
            "created_at": time.time() - 1800,  # 30 minutes ago
            "status": "active",
        },
        {
            "id": "alert-002",
            "severity": "info",
            "title": "Long-running pipeline detected",
            "description": "Pipeline 'ml-training-pipeline' has been running for 45 minutes",
            "component": "scheduler",
            "created_at": time.time() - 2700,  # 45 minutes ago
            "status": "active",
        },
    ]

    return {
        "alerts": alerts,
        "total_count": len(alerts),
        "severity_counts": {"critical": 0, "warning": 1, "info": 1},
    }
