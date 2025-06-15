"""
Experiment run management API endpoints for Experiment Tracking service
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# Mock data stores
runs_store: dict[str, Any] = {}
metrics_store: dict[str, Any] = {}
artifacts_store: dict[str, Any] = {}


class RunStatus(str):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunCreate(BaseModel):
    """Run creation model"""

    experiment_id: uuid.UUID = Field(..., description="Experiment ID")
    name: Optional[str] = Field(None, description="Run name")
    description: Optional[str] = Field(None, description="Run description")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Run parameters"
    )
    tags: List[str] = Field(default_factory=list, description="Run tags")
    environment: Dict[str, Any] = Field(
        default_factory=dict, description="Environment info"
    )


class RunUpdate(BaseModel):
    """Run update model"""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    final_metrics: Optional[Dict[str, float]] = None


class RunResponse(BaseModel):
    """Run response model"""

    id: uuid.UUID
    experiment_id: uuid.UUID
    name: Optional[str]
    description: Optional[str]
    status: str
    parameters: Dict[str, Any]
    tags: List[str]
    environment: Dict[str, Any]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    final_metrics: Dict[str, float] = Field(default_factory=dict)
    artifacts_count: int = Field(default=0)
    logs_size_mb: float = Field(default=0.0)

    # Compute info
    duration_seconds: Optional[int] = None
    compute_hours: Optional[float] = None
    memory_usage_gb: Optional[float] = None


class RunSummary(BaseModel):
    """Run summary model for listings"""

    id: uuid.UUID
    experiment_id: uuid.UUID
    name: Optional[str]
    status: str
    created_at: datetime
    duration_seconds: Optional[int]

    # Key metrics
    key_metrics: Dict[str, float] = Field(default_factory=dict)
    artifacts_count: int = Field(default=0)


class RunListResponse(BaseModel):
    """Run list response model"""

    runs: List[RunSummary]
    total: int
    page: int
    size: int
    total_pages: int


class MetricPoint(BaseModel):
    """Single metric point"""

    timestamp: datetime
    step: int
    value: float
    epoch: Optional[int] = None


class MetricSeries(BaseModel):
    """Metric time series"""

    metric_name: str
    run_id: uuid.UUID
    points: List[MetricPoint]


class LogMetricRequest(BaseModel):
    """Log metric request"""

    metric_name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    step: int = Field(..., description="Step number")
    timestamp: Optional[datetime] = None
    epoch: Optional[int] = None


@router.post("/", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(run: RunCreate) -> RunResponse:
    """Create a new run"""

    run_id = str(uuid.uuid4())

    run_data = RunResponse(
        id=uuid.UUID(run_id),
        **run.dict(),
        status=RunStatus.CREATED,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    runs_store[run_id] = run_data

    logger.info(f"Created run {run_id} for experiment {run.experiment_id}")

    return run_data


@router.get("/", response_model=RunListResponse)
async def list_runs(
    experiment_id: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> RunListResponse:
    """List runs with filtering and pagination"""

    # Filter runs
    filtered_runs = []
    for run in runs_store.values():
        if experiment_id and str(run.experiment_id) != experiment_id:
            continue
        if status and run.status != status:
            continue
        if tag and tag not in run.tags:
            continue

        # Convert to summary
        run_summary = RunSummary(
            id=run.id,
            experiment_id=run.experiment_id,
            name=run.name,
            status=run.status,
            created_at=run.created_at,
            duration_seconds=run.duration_seconds,
            key_metrics=dict(list(run.final_metrics.items())[:3]),  # Top 3 metrics
            artifacts_count=run.artifacts_count,
        )

        filtered_runs.append(run_summary)

    # Sort by creation date (newest first)
    filtered_runs.sort(key=lambda r: r.created_at, reverse=True)

    # Pagination
    total = len(filtered_runs)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    page_runs = filtered_runs[start_idx:end_idx]

    total_pages = (total + size - 1) // size

    return RunListResponse(
        runs=page_runs, total=total, page=page, size=size, total_pages=total_pages
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str) -> RunResponse:
    """Get run by ID"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    return runs_store[run_id]


@router.put("/{run_id}", response_model=RunResponse)
async def update_run(run_id: str, run_update: RunUpdate) -> RunResponse:
    """Update run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    run = runs_store[run_id]

    # Update fields
    update_data = run_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(run, field, value)

    # Update timestamp
    run.updated_at = datetime.utcnow()

    logger.info(f"Updated run {run_id}")

    return run


@router.delete("/{run_id}")
async def delete_run(run_id: str):
    """Delete run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    run = runs_store[run_id]

    # Check if run is currently running
    if run.status == RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete running run"
        )

    # Clean up associated data
    if run_id in metrics_store:
        del metrics_store[run_id]
    if run_id in artifacts_store:
        del artifacts_store[run_id]

    del runs_store[run_id]

    logger.info(f"Deleted run {run_id}")

    return {"message": "Run deleted successfully"}


@router.post("/{run_id}/start")
async def start_run(run_id: str):
    """Start run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    run = runs_store[run_id]

    if run.status != RunStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start run in status '{run.status}'",
        )

    run.status = RunStatus.RUNNING
    run.started_at = datetime.utcnow()
    run.updated_at = datetime.utcnow()

    logger.info(f"Started run {run_id}")

    return {"message": "Run started", "status": run.status}


@router.post("/{run_id}/finish")
async def finish_run(run_id: str, final_status: str = "completed"):
    """Finish run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    run = runs_store[run_id]

    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finish run in status '{run.status}'",
        )

    run.status = final_status
    run.completed_at = datetime.utcnow()
    run.updated_at = datetime.utcnow()

    # Calculate duration
    if run.started_at:
        duration = run.completed_at - run.started_at
        run.duration_seconds = int(duration.total_seconds())
        run.compute_hours = duration.total_seconds() / 3600

    logger.info(f"Finished run {run_id} with status {final_status}")

    return {"message": "Run finished", "status": run.status}


@router.post("/{run_id}/metrics")
async def log_metric(run_id: str, metric_request: LogMetricRequest):
    """Log a metric for a run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    # Initialize metrics store for run if needed
    if run_id not in metrics_store:
        metrics_store[run_id] = {}

    # Initialize metric series if needed
    if metric_request.metric_name not in metrics_store[run_id]:
        metrics_store[run_id][metric_request.metric_name] = []

    # Create metric point
    timestamp = metric_request.timestamp or datetime.utcnow()

    metric_point = MetricPoint(
        timestamp=timestamp,
        step=metric_request.step,
        value=metric_request.value,
        epoch=metric_request.epoch,
    )

    # Add to series
    metrics_store[run_id][metric_request.metric_name].append(metric_point)

    # Update run's final metrics
    run = runs_store[run_id]
    run.final_metrics[metric_request.metric_name] = metric_request.value
    run.updated_at = datetime.utcnow()

    logger.info(
        f"Logged metric {metric_request.metric_name}="
        f"{metric_request.value} for run {run_id}"
    )

    return {"message": "Metric logged successfully"}


@router.get("/{run_id}/metrics", response_model=Dict[str, List[MetricPoint]])
async def get_run_metrics(run_id: str) -> Dict[str, List[MetricPoint]]:
    """Get all metrics for a run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    return metrics_store.get(run_id, {})


@router.get("/{run_id}/metrics/{metric_name}", response_model=List[MetricPoint])
async def get_run_metric_series(run_id: str, metric_name: str) -> List[MetricPoint]:
    """Get specific metric series for a run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    if run_id not in metrics_store or metric_name not in metrics_store[run_id]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric '{metric_name}' not found for run '{run_id}'",
        )

    return metrics_store[run_id][metric_name]


@router.post("/{run_id}/artifacts")
async def upload_artifact(
    run_id: str, file: UploadFile = File(...), artifact_type: str = "model"
):
    """Upload an artifact for a run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    # Initialize artifacts store for run if needed
    if run_id not in artifacts_store:
        artifacts_store[run_id] = []

    # Mock artifact storage (in real implementation, store in MinIO/S3)
    artifact_id = str(uuid.uuid4())

    artifact_info = {
        "id": artifact_id,
        "filename": file.filename,
        "type": artifact_type,
        "size_bytes": 0,  # Would be actual file size
        "uploaded_at": datetime.utcnow().isoformat(),
        "path": f"artifacts/{run_id}/{artifact_id}/{file.filename}",
    }

    artifacts_store[run_id].append(artifact_info)

    # Update run artifacts count
    run = runs_store[run_id]
    run.artifacts_count = len(artifacts_store[run_id])
    run.updated_at = datetime.utcnow()

    logger.info(f"Uploaded artifact {file.filename} for run {run_id}")

    return {
        "message": "Artifact uploaded successfully",
        "artifact_id": artifact_id,
        "path": artifact_info["path"],
    }


@router.get("/{run_id}/artifacts")
async def list_run_artifacts(run_id: str):
    """List artifacts for a run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    return {
        "artifacts": artifacts_store.get(run_id, []),
        "total": len(artifacts_store.get(run_id, [])),
    }


@router.post("/{run_id}/logs")
async def log_message(run_id: str, message: str, level: str = "info"):
    """Log a message for a run"""

    if run_id not in runs_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run with ID '{run_id}' not found",
        )

    # Mock log storage (in real implementation, store in proper logging system)
    logger.info(f"[{run_id}] {level.upper()}: {message}")

    logger.info(f"[{run_id}] {level.upper()}: {message}")

    return {"message": "Log entry created"}
