"""
Pipeline run management API endpoints
"""

import logging
from typing import Dict, List, Optional

from api.routes.pipelines import pipelines_store
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for API
class PipelineRunRequest(BaseModel):
    """Request model for starting a pipeline run"""

    pipeline_id: str
    parameters: Dict = Field(default_factory=dict)
    triggered_by: str = Field(default="manual")


class TaskExecutionResponse(BaseModel):
    """Response model for task execution"""

    task_id: str
    task_name: str
    status: str
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: Optional[float]
    retry_count: int
    error_message: Optional[str]


class PipelineRunResponse(BaseModel):
    """Response model for pipeline run"""

    run_id: str
    pipeline_id: str
    pipeline_name: str
    status: str
    triggered_by: str
    start_time: Optional[str]
    end_time: Optional[str]
    progress: float
    parameters: Dict
    task_executions: List[TaskExecutionResponse]


class PipelineRunListResponse(BaseModel):
    """Response model for pipeline run list"""

    runs: List[PipelineRunResponse]
    total: int
    page: int
    size: int


# Mock data for demonstration (would be replaced with actual
# scheduler integration)
mock_runs = {}


@router.post(
    "/",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_pipeline_run(
    run_request: PipelineRunRequest,
) -> PipelineRunResponse:
    """Start a new pipeline run"""

    # Check if pipeline exists
    if run_request.pipeline_id not in pipelines_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline with ID '{run_request.pipeline_id}' not found",
        )

    pipeline = pipelines_store[run_request.pipeline_id]

    # Check if pipeline is active
    if not pipeline.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pipeline '{pipeline.name}' is not active",
        )

    # Validate pipeline before running
    validation_errors = pipeline.validate_dag()
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pipeline validation failed: {validation_errors}",
        )

    # This would normally call the scheduler to submit the pipeline
    # For demo purposes, we'll create a mock run
    import uuid

    run_id = str(uuid.uuid4())

    # Create mock task executions
    task_executions = []
    for task_id, task in pipeline.tasks.items():
        task_executions.append(
            TaskExecutionResponse(
                task_id=task_id,
                task_name=task.name,
                status="pending",
                start_time=None,
                end_time=None,
                duration_seconds=None,
                retry_count=0,
                error_message=None,
            )
        )

    # Create run response
    run_response = PipelineRunResponse(
        run_id=run_id,
        pipeline_id=run_request.pipeline_id,
        pipeline_name=pipeline.name,
        status="queued",
        triggered_by=run_request.triggered_by,
        start_time=None,
        end_time=None,
        progress=0.0,
        parameters=run_request.parameters,
        task_executions=task_executions,
    )

    # Store mock run
    mock_runs[run_id] = run_response

    logger.info(f"Started pipeline run {run_id} for pipeline {pipeline.name}")

    # TODO: Actually submit to scheduler
    # run_id = await scheduler.submit_pipeline(
    #     pipeline, run_request.triggered_by, run_request.parameters
    # )

    return run_response


@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(run_id: str) -> PipelineRunResponse:
    """Get status of a specific pipeline run"""

    # TODO: Get from actual scheduler
    # run_status = await scheduler.get_run_status(run_id)

    # For demo, return mock data
    if run_id not in mock_runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run with ID '{run_id}' not found",
        )

    return mock_runs[run_id]


@router.get("/", response_model=PipelineRunListResponse)
async def list_pipeline_runs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    pipeline_id: Optional[str] = None,
    status: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> PipelineRunListResponse:
    """List pipeline runs with filtering and pagination"""

    # Filter runs
    filtered_runs = []
    for run in mock_runs.values():
        if pipeline_id and run.pipeline_id != pipeline_id:
            continue
        if status and run.status != status:
            continue
        if triggered_by and run.triggered_by != triggered_by:
            continue

        filtered_runs.append(run)

    # Sort by start time (newest first)
    filtered_runs.sort(key=lambda r: r.start_time or "", reverse=True)

    # Pagination
    total = len(filtered_runs)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    page_runs = filtered_runs[start_idx:end_idx]

    return PipelineRunListResponse(runs=page_runs, total=total, page=page, size=size)


@router.post("/{run_id}/cancel")
async def cancel_pipeline_run(run_id: str) -> Dict:
    """Cancel a running pipeline"""

    if run_id not in mock_runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run with ID '{run_id}' not found",
        )

    run = mock_runs[run_id]

    if run.status in ["success", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel pipeline run with status '{run.status}'",
        )

    # TODO: Actually cancel in scheduler
    # success = await scheduler.cancel_pipeline(run_id)

    # Update mock data
    run.status = "cancelled"
    logger.info(f"Cancelled pipeline run {run_id}")

    return {
        "run_id": run_id,
        "status": "cancelled",
        "message": "Pipeline run cancelled successfully",
    }


@router.get("/{run_id}/logs")
async def get_pipeline_run_logs(
    run_id: str,
    task_id: Optional[str] = None,
    tail: int = Query(100, ge=1, le=1000),
) -> Dict:
    """Get logs for a pipeline run or specific task"""

    if run_id not in mock_runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run with ID '{run_id}' not found",
        )

    # Mock log data
    logs = [
        f"2024-01-01 10:00:00 - INFO - Pipeline run {run_id} started",
        "2024-01-01 10:00:01 - INFO - Executing task data_ingestion",
        ("2024-01-01 10:00:05 - INFO - Task data_ingestion completed " "successfully"),
        "2024-01-01 10:00:06 - INFO - Executing task data_validation",
        ("2024-01-01 10:00:10 - INFO - Task data_validation completed " "successfully"),
    ]

    if task_id:
        # Filter logs for specific task
        logs = [log for log in logs if task_id in log]

    # Apply tail limit
    logs = logs[-tail:]

    return {
        "run_id": run_id,
        "task_id": task_id,
        "logs": logs,
        "total_lines": len(logs),
        "tail": tail,
    }


@router.get("/{run_id}/metrics")
async def get_pipeline_run_metrics(run_id: str) -> Dict:
    """Get metrics for a pipeline run"""

    if run_id not in mock_runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run with ID '{run_id}' not found",
        )

    run = mock_runs[run_id]

    # Mock metrics data
    return {
        "run_id": run_id,
        "pipeline_name": run.pipeline_name,
        "status": run.status,
        "progress": run.progress,
        "resource_usage": {
            "cpu_seconds": 1200,
            "memory_gb_seconds": 4800,
            "gpu_seconds": 0,
        },
        "task_metrics": {
            "total_tasks": len(run.task_executions),
            "completed_tasks": len(
                [t for t in run.task_executions if t.status == "success"]
            ),
            "failed_tasks": len(
                [t for t in run.task_executions if t.status == "failed"]
            ),
            "pending_tasks": len(
                [t for t in run.task_executions if t.status == "pending"]
            ),
        },
        "performance": {
            "avg_task_duration": 30.0,
            "total_duration": 120.0,
            "throughput_tasks_per_minute": 2.0,
        },
    }
