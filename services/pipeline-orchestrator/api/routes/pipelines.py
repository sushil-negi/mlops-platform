"""
Pipeline management API endpoints
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from core.dag import (Pipeline, ResourceRequirements, RetryPolicy, Task,
                      TriggerType)
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for API
class TaskCreateRequest(BaseModel):
    """Request model for creating a task"""

    name: str = Field(..., min_length=1, max_length=255)
    operator: str = Field(..., min_length=1)
    parameters: Dict = Field(default_factory=dict)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    upstream_tasks: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Resource requirements
    cpu: float = Field(default=1.0, ge=0.1, le=64.0)
    memory_gb: float = Field(default=2.0, ge=0.1, le=128.0)
    gpu: int = Field(default=0, ge=0, le=8)
    timeout_seconds: int = Field(default=3600, ge=1, le=86400)

    # Retry policy
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600)

    # Execution settings
    condition: Optional[str] = None
    trigger_rule: str = Field(default="all_success")


class PipelineCreateRequest(BaseModel):
    """Request model for creating a pipeline"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    version: str = Field(default="1.0.0")
    owner: str = Field(..., min_length=1)
    team: Optional[str] = None
    project: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    trigger_type: TriggerType = Field(default=TriggerType.MANUAL)
    max_concurrent_runs: int = Field(default=1, ge=1, le=10)
    tasks: List[TaskCreateRequest] = Field(default_factory=list)


class PipelineResponse(BaseModel):
    """Response model for pipeline"""

    id: str
    name: str
    description: Optional[str]
    version: str
    owner: str
    team: Optional[str]
    project: Optional[str]
    tags: List[str]
    trigger_type: str
    task_count: int
    is_active: bool
    created_at: str
    updated_at: str


class PipelineDetailResponse(BaseModel):
    """Detailed response model for pipeline"""

    id: str
    name: str
    description: Optional[str]
    version: str
    owner: str
    team: Optional[str]
    project: Optional[str]
    tags: List[str]
    trigger_type: str
    max_concurrent_runs: int
    is_active: bool
    created_at: str
    updated_at: str
    tasks: List[Dict]
    validation_errors: List[str]


class PipelineListResponse(BaseModel):
    """Response model for pipeline list"""

    pipelines: List[PipelineResponse]
    total: int
    page: int
    size: int


# In-memory storage for demo (would use database in production)
pipelines_store: Dict[str, Pipeline] = {}


@router.post(
    "/", response_model=PipelineDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_pipeline(
    pipeline_data: PipelineCreateRequest,
) -> PipelineDetailResponse:
    """Create a new pipeline"""

    # Create pipeline
    pipeline = Pipeline(
        name=pipeline_data.name,
        description=pipeline_data.description,
        version=pipeline_data.version,
        owner=pipeline_data.owner,
        team=pipeline_data.team,
        project=pipeline_data.project,
        tags=pipeline_data.tags,
        trigger_type=pipeline_data.trigger_type,
        max_concurrent_runs=pipeline_data.max_concurrent_runs,
    )

    # Add tasks
    for task_request in pipeline_data.tasks:
        # Create resource requirements
        resources = ResourceRequirements(
            cpu=task_request.cpu,
            memory_gb=task_request.memory_gb,
            gpu=task_request.gpu,
            timeout_seconds=task_request.timeout_seconds,
        )

        # Create retry policy
        retry_policy = RetryPolicy(
            max_retries=task_request.max_retries,
            retry_delay_seconds=task_request.retry_delay_seconds,
        )

        # Create task
        task = Task(
            name=task_request.name,
            operator=task_request.operator,
            parameters=task_request.parameters,
            environment_variables=task_request.environment_variables,
            upstream_tasks=task_request.upstream_tasks,
            description=task_request.description,
            tags=task_request.tags,
            resources=resources,
            retry_policy=retry_policy,
            condition=task_request.condition,
            trigger_rule=task_request.trigger_rule,
        )

        pipeline.add_task(task)

    # Validate pipeline
    validation_errors = pipeline.validate_dag()

    # Store pipeline
    pipelines_store[pipeline.id] = pipeline

    logger.info(f"Created pipeline: {pipeline.name} ({pipeline.id})")

    return PipelineDetailResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        version=pipeline.version,
        owner=pipeline.owner,
        team=pipeline.team,
        project=pipeline.project,
        tags=pipeline.tags,
        trigger_type=pipeline.trigger_type.value,
        max_concurrent_runs=pipeline.max_concurrent_runs,
        is_active=pipeline.is_active,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
        tasks=[task.dict() for task in pipeline.tasks.values()],
        validation_errors=validation_errors,
    )


@router.get("/", response_model=PipelineListResponse)
async def list_pipelines(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    owner: Optional[str] = None,
    team: Optional[str] = None,
    project: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
) -> PipelineListResponse:
    """List pipelines with filtering and pagination"""

    # Filter pipelines
    filtered_pipelines = []
    for pipeline in pipelines_store.values():
        # Apply filters
        if owner and pipeline.owner != owner:
            continue
        if team and pipeline.team != team:
            continue
        if project and pipeline.project != project:
            continue
        if is_active is not None and pipeline.is_active != is_active:
            continue
        if search and search.lower() not in pipeline.name.lower():
            continue

        filtered_pipelines.append(pipeline)

    # Sort by creation date (newest first)
    filtered_pipelines.sort(key=lambda p: p.created_at, reverse=True)

    # Pagination
    total = len(filtered_pipelines)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    page_pipelines = filtered_pipelines[start_idx:end_idx]

    # Convert to response format
    pipeline_responses = [
        PipelineResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            version=p.version,
            owner=p.owner,
            team=p.team,
            project=p.project,
            tags=p.tags,
            trigger_type=p.trigger_type.value,
            task_count=len(p.tasks),
            is_active=p.is_active,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in page_pipelines
    ]

    return PipelineListResponse(
        pipelines=pipeline_responses, total=total, page=page, size=size
    )


@router.get("/{pipeline_id}", response_model=PipelineDetailResponse)
async def get_pipeline(pipeline_id: str) -> PipelineDetailResponse:
    """Get a specific pipeline by ID"""

    if pipeline_id not in pipelines_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline with ID '{pipeline_id}' not found",
        )

    pipeline = pipelines_store[pipeline_id]
    validation_errors = pipeline.validate_dag()

    return PipelineDetailResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        version=pipeline.version,
        owner=pipeline.owner,
        team=pipeline.team,
        project=pipeline.project,
        tags=pipeline.tags,
        trigger_type=pipeline.trigger_type.value,
        max_concurrent_runs=pipeline.max_concurrent_runs,
        is_active=pipeline.is_active,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
        tasks=[task.dict() for task in pipeline.tasks.values()],
        validation_errors=validation_errors,
    )


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(pipeline_id: str):
    """Delete a pipeline"""

    if pipeline_id not in pipelines_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline with ID '{pipeline_id}' not found",
        )

    pipeline = pipelines_store.pop(pipeline_id)
    logger.info(f"Deleted pipeline: {pipeline.name} ({pipeline_id})")


@router.post("/{pipeline_id}/activate", response_model=PipelineResponse)
async def activate_pipeline(pipeline_id: str) -> PipelineResponse:
    """Activate a pipeline"""

    if pipeline_id not in pipelines_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline with ID '{pipeline_id}' not found",
        )

    pipeline = pipelines_store[pipeline_id]
    pipeline.is_active = True
    pipeline.updated_at = datetime.utcnow()

    logger.info(f"Activated pipeline: {pipeline.name} ({pipeline_id})")

    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        version=pipeline.version,
        owner=pipeline.owner,
        team=pipeline.team,
        project=pipeline.project,
        tags=pipeline.tags,
        trigger_type=pipeline.trigger_type.value,
        task_count=len(pipeline.tasks),
        is_active=pipeline.is_active,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
    )


@router.post("/{pipeline_id}/deactivate", response_model=PipelineResponse)
async def deactivate_pipeline(pipeline_id: str) -> PipelineResponse:
    """Deactivate a pipeline"""

    if pipeline_id not in pipelines_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline with ID '{pipeline_id}' not found",
        )

    pipeline = pipelines_store[pipeline_id]
    pipeline.is_active = False
    pipeline.updated_at = datetime.utcnow()

    logger.info(f"Deactivated pipeline: {pipeline.name} ({pipeline_id})")

    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        description=pipeline.description,
        version=pipeline.version,
        owner=pipeline.owner,
        team=pipeline.team,
        project=pipeline.project,
        tags=pipeline.tags,
        trigger_type=pipeline.trigger_type.value,
        task_count=len(pipeline.tasks),
        is_active=pipeline.is_active,
        created_at=pipeline.created_at.isoformat(),
        updated_at=pipeline.updated_at.isoformat(),
    )


@router.get("/{pipeline_id}/validate")
async def validate_pipeline(pipeline_id: str) -> Dict:
    """Validate a pipeline and return validation results"""

    if pipeline_id not in pipelines_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline with ID '{pipeline_id}' not found",
        )

    pipeline = pipelines_store[pipeline_id]
    validation_errors = pipeline.validate_dag()

    # Additional validation checks
    warnings = []

    # Check for resource efficiency
    total_cpu = sum(task.resources.cpu for task in pipeline.tasks.values())
    if total_cpu > 50:
        warnings.append(
            "High total CPU requirements - consider optimizing resource usage"
        )

    # Check for long-running tasks
    long_tasks = [
        task.name
        for task in pipeline.tasks.values()
        if task.resources.timeout_seconds > 7200
    ]  # 2 hours
    if long_tasks:
        warnings.append(f"Long-running tasks detected: {', '.join(long_tasks)}")

    return {
        "pipeline_id": pipeline_id,
        "pipeline_name": pipeline.name,
        "is_valid": len(validation_errors) == 0,
        "errors": validation_errors,
        "warnings": warnings,
        "task_count": len(pipeline.tasks),
        "estimated_duration": str(pipeline.estimate_duration()),
        "validation_timestamp": datetime.utcnow().isoformat(),
    }
