"""
Experiment management API endpoints for Experiment Tracking service
"""

import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from models.experiment import (
    EXPERIMENT_TEMPLATES,
    ExperimentComparison,
    ExperimentCreate,
    ExperimentListResponse,
    ExperimentMetrics,
    ExperimentResponse,
    ExperimentStatus,
    ExperimentSummary,
    ExperimentType,
    ExperimentUpdate,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Mock data store (replace with actual database integration)
experiments_store: dict[str, Any] = {}
runs_store: dict[str, Any] = {}


@router.post(
    "/", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED
)
async def create_experiment(experiment: ExperimentCreate) -> ExperimentResponse:
    """Create a new experiment"""

    experiment_id = str(uuid.uuid4())

    experiment_data = ExperimentResponse(
        id=uuid.UUID(experiment_id),
        **experiment.dict(),
        status=ExperimentStatus.CREATED,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        total_runs=0,
        successful_runs=0,
        failed_runs=0,
    )

    experiments_store[experiment_id] = experiment_data

    logger.info(f"Created experiment {experiment_id}: {experiment.name}")

    return experiment_data


@router.get("/", response_model=ExperimentListResponse)
async def list_experiments(
    project_id: Optional[str] = None,
    status: Optional[ExperimentStatus] = None,
    experiment_type: Optional[ExperimentType] = None,
    tag: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> ExperimentListResponse:
    """List experiments with filtering and pagination"""

    # Filter experiments
    filtered_experiments = []
    for experiment in experiments_store.values():
        if project_id and str(experiment.project_id) != project_id:
            continue
        if status and experiment.status != status:
            continue
        if experiment_type and experiment.experiment_type != experiment_type:
            continue
        if tag and tag not in experiment.tags:
            continue

        # Convert to summary
        experiment_summary = ExperimentSummary(
            id=experiment.id,
            project_id=experiment.project_id,
            name=experiment.name,
            description=experiment.description,
            experiment_type=experiment.experiment_type,
            status=experiment.status,
            tags=experiment.tags,
            created_at=experiment.created_at,
            run_count=experiment.total_runs,
            best_metric_value=experiment.best_metric_value,
            best_metric_name=experiment.best_metric_name,
        )

        filtered_experiments.append(experiment_summary)

    # Sort by creation date (newest first)
    filtered_experiments.sort(key=lambda e: e.created_at, reverse=True)

    # Pagination
    total = len(filtered_experiments)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    page_experiments = filtered_experiments[start_idx:end_idx]

    total_pages = (total + size - 1) // size

    return ExperimentListResponse(
        experiments=page_experiments,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str) -> ExperimentResponse:
    """Get experiment by ID"""

    if experiment_id not in experiments_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID '{experiment_id}' not found",
        )

    return experiments_store[experiment_id]


@router.put("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: str, experiment_update: ExperimentUpdate
) -> ExperimentResponse:
    """Update experiment"""

    if experiment_id not in experiments_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID '{experiment_id}' not found",
        )

    experiment = experiments_store[experiment_id]

    # Update fields
    update_data = experiment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(experiment, field, value)

    # Update timestamp
    experiment.updated_at = datetime.utcnow()

    logger.info(f"Updated experiment {experiment_id}")

    return experiment


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: str):
    """Delete experiment"""

    if experiment_id not in experiments_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID '{experiment_id}' not found",
        )

    experiment = experiments_store[experiment_id]

    # Check if experiment has running runs
    if experiment.status == ExperimentStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running experiment",
        )

    del experiments_store[experiment_id]

    logger.info(f"Deleted experiment {experiment_id}: {experiment.name}")

    return {"message": "Experiment deleted successfully"}


@router.post("/{experiment_id}/start")
async def start_experiment(experiment_id: str):
    """Start experiment"""

    if experiment_id not in experiments_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID '{experiment_id}' not found",
        )

    experiment = experiments_store[experiment_id]

    if experiment.status != ExperimentStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start experiment in status '{experiment.status}'",
        )

    experiment.status = ExperimentStatus.RUNNING
    experiment.started_at = datetime.utcnow()
    experiment.updated_at = datetime.utcnow()

    logger.info(f"Started experiment {experiment_id}")

    return {"message": "Experiment started", "status": experiment.status}


@router.post("/{experiment_id}/stop")
async def stop_experiment(experiment_id: str):
    """Stop experiment"""

    if experiment_id not in experiments_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID '{experiment_id}' not found",
        )

    experiment = experiments_store[experiment_id]

    if experiment.status != ExperimentStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot stop experiment in status '{experiment.status}'",
        )

    experiment.status = ExperimentStatus.COMPLETED
    experiment.completed_at = datetime.utcnow()
    experiment.updated_at = datetime.utcnow()

    logger.info(f"Stopped experiment {experiment_id}")

    return {"message": "Experiment stopped", "status": experiment.status}


@router.get("/{experiment_id}/metrics", response_model=ExperimentMetrics)
async def get_experiment_metrics(experiment_id: str) -> ExperimentMetrics:
    """Get experiment metrics"""

    if experiment_id not in experiments_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with ID '{experiment_id}' not found",
        )

    # Mock metrics (replace with actual database queries)
    metrics = ExperimentMetrics(
        experiment_id=uuid.UUID(experiment_id),
        best_run_metrics={
            "accuracy": 0.9818,
            "f1_score": 0.9756,
            "precision": 0.9689,
            "recall": 0.9825,
        },
        average_metrics={
            "accuracy": 0.9654,
            "f1_score": 0.9521,
            "precision": 0.9456,
            "recall": 0.9589,
        },
        metric_trends={
            "accuracy": [0.92, 0.94, 0.96, 0.97, 0.98],
            "f1_score": [0.91, 0.93, 0.95, 0.96, 0.98],
        },
        total_runs=15,
        successful_runs=13,
        failed_runs=2,
        average_run_duration_minutes=45.5,
        total_compute_hours=11.375,
        average_memory_usage_gb=2.8,
        total_storage_mb=512.0,
    )

    return metrics


@router.post("/compare", response_model=ExperimentComparison)
async def compare_experiments(
    comparison_request: ExperimentComparison,
) -> ExperimentComparison:
    """Compare multiple experiments"""

    # Validate experiments exist
    for exp_id in comparison_request.experiments:
        if str(exp_id) not in experiments_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment with ID '{exp_id}' not found",
            )

    # Mock comparison results
    comparison_result = ExperimentComparison(
        experiments=comparison_request.experiments,
        comparison_metrics=comparison_request.comparison_metrics,
        best_experiment=comparison_request.experiments[0],
        metric_comparison={
            "accuracy": {
                comparison_request.experiments[0]: 0.9818,
                comparison_request.experiments[1]: (
                    0.9756 if len(comparison_request.experiments) > 1 else 0.0
                ),
            },
            "f1_score": {
                comparison_request.experiments[0]: 0.9756,
                comparison_request.experiments[1]: (
                    0.9689 if len(comparison_request.experiments) > 1 else 0.0
                ),
            },
        },
        statistical_significance={
            "accuracy": {
                "p_value": 0.032,
                "significant": True,
                "confidence_interval": [0.005, 0.025],
            }
        },
        visualization_url="/api/v1/experiments/visualizations/comparison",
    )

    return comparison_result


@router.get("/templates/", response_model=dict)
async def get_experiment_templates():
    """Get available experiment templates"""
    return {"templates": EXPERIMENT_TEMPLATES, "total": len(EXPERIMENT_TEMPLATES)}


@router.post("/from-template/{template_name}", response_model=ExperimentResponse)
async def create_experiment_from_template(
    template_name: str, experiment_data: ExperimentCreate
) -> ExperimentResponse:
    """Create experiment from template"""

    if template_name not in EXPERIMENT_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )

    template = EXPERIMENT_TEMPLATES[template_name]

    # Merge template with provided data
    template_data = template.copy()
    experiment_dict = experiment_data.dict()

    # Update template with user data
    for key, value in experiment_dict.items():
        if value is not None:
            template_data[key] = value

    # Create experiment with template data
    template_experiment = ExperimentCreate(**template_data)  # type: ignore
    return await create_experiment(template_experiment)
