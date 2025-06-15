"""
Model management API endpoints
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import databases
from core.config import get_settings
from core.database import get_database
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.model import ModelFramework, ModelStage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


# Pydantic models for request/response
class ModelCreate(BaseModel):
    """Model creation request"""

    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    framework: ModelFramework
    model_type: str = Field(..., max_length=100)
    task_type: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict] = Field(default_factory=dict)
    team: Optional[str] = Field(None, max_length=255)
    project: Optional[str] = Field(None, max_length=255)


class ModelUpdate(BaseModel):
    """Model update request"""

    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None
    team: Optional[str] = Field(None, max_length=255)
    project: Optional[str] = Field(None, max_length=255)
    current_stage: Optional[ModelStage] = None


class ModelResponse(BaseModel):
    """Model response"""

    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    framework: str
    model_type: str
    task_type: Optional[str]
    tags: List[str]
    metadata: Dict
    created_by: str
    team: Optional[str]
    project: Optional[str]
    latest_version: Optional[str]
    current_stage: str
    created_at: str
    updated_at: str


class ModelListResponse(BaseModel):
    """Model list response"""

    models: List[ModelResponse]
    total: int
    page: int
    size: int


@router.post("/", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    model_data: ModelCreate,
    created_by: str = "system",  # TODO: Extract from auth token
    db: databases.Database = Depends(get_database),
) -> ModelResponse:
    """Create a new model"""

    # Check if model name already exists
    existing = await db.fetch_one(
        "SELECT id FROM models WHERE name = :name", {"name": model_data.name}
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model with name '{model_data.name}' already exists",
        )

    # Create model
    model_id = uuid.uuid4()
    now = datetime.utcnow()

    await db.execute(
        """
        INSERT INTO models (
            id, name, display_name, description, framework, model_type,
            task_type,
            tags, metadata, created_by, team, project, current_stage,
            created_at, updated_at
        ) VALUES (
            :id, :name, :display_name, :description, :framework,
            :model_type, :task_type,
            :tags, :metadata, :created_by, :team, :project,
            :current_stage, :created_at, :updated_at
        )
        """,
        {
            "id": model_id,
            "name": model_data.name,
            "display_name": model_data.display_name,
            "description": model_data.description,
            "framework": model_data.framework.value,
            "model_type": model_data.model_type,
            "task_type": model_data.task_type,
            "tags": model_data.tags,
            "metadata": model_data.metadata,
            "created_by": created_by,
            "team": model_data.team,
            "project": model_data.project,
            "current_stage": ModelStage.DEVELOPMENT.value,
            "created_at": now,
            "updated_at": now,
        },
    )

    # Fetch and return created model
    model = await db.fetch_one("SELECT * FROM models WHERE id = :id", {"id": model_id})

    return ModelResponse(
        id=str(model["id"]),
        name=model["name"],
        display_name=model["display_name"],
        description=model["description"],
        framework=model["framework"],
        model_type=model["model_type"],
        task_type=model["task_type"],
        tags=model["tags"] or [],
        metadata=model["metadata"] or {},
        created_by=model["created_by"],
        team=model["team"],
        project=model["project"],
        latest_version=model["latest_version"],
        current_stage=model["current_stage"],
        created_at=model["created_at"].isoformat(),
        updated_at=model["updated_at"].isoformat(),
    )


@router.get("/", response_model=ModelListResponse)
async def list_models(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    framework: Optional[ModelFramework] = None,
    model_type: Optional[str] = None,
    stage: Optional[ModelStage] = None,
    team: Optional[str] = None,
    project: Optional[str] = None,
    search: Optional[str] = None,
    db: databases.Database = Depends(get_database),
) -> ModelListResponse:
    """List models with filtering and pagination"""

    # Build query conditions
    conditions = []
    params = {}

    if framework:
        conditions.append("framework = :framework")
        params["framework"] = framework.value

    if model_type:
        conditions.append("model_type = :model_type")
        params["model_type"] = model_type

    if stage:
        conditions.append("current_stage = :stage")
        params["stage"] = stage.value

    if team:
        conditions.append("team = :team")
        params["team"] = team

    if project:
        conditions.append("project = :project")
        params["project"] = project

    if search:
        conditions.append("(name ILIKE :search OR description ILIKE :search)")
        params["search"] = f"%{search}%"

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get total count
    count_query = f"SELECT COUNT(*) as total FROM models WHERE {where_clause}"
    total_result = await db.fetch_one(count_query, params)
    total = total_result["total"] if total_result else 0

    # Get models with pagination
    offset = (page - 1) * size
    params.update({"limit": size, "offset": offset})

    models_query = f"""
        SELECT * FROM models
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """

    models = await db.fetch_all(models_query, params)

    model_responses = [
        ModelResponse(
            id=str(model["id"]),
            name=model["name"],
            display_name=model["display_name"],
            description=model["description"],
            framework=model["framework"],
            model_type=model["model_type"],
            task_type=model["task_type"],
            tags=model["tags"] or [],
            metadata=model["metadata"] or {},
            created_by=model["created_by"],
            team=model["team"],
            project=model["project"],
            latest_version=model["latest_version"],
            current_stage=model["current_stage"],
            created_at=model["created_at"].isoformat(),
            updated_at=model["updated_at"].isoformat(),
        )
        for model in models
    ]

    return ModelListResponse(models=model_responses, total=total, page=page, size=size)


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str, db: databases.Database = Depends(get_database)
) -> ModelResponse:
    """Get a specific model by ID"""

    model = await db.fetch_one("SELECT * FROM models WHERE id = :id", {"id": model_id})

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID '{model_id}' not found",
        )

    return ModelResponse(
        id=str(model["id"]),
        name=model["name"],
        display_name=model["display_name"],
        description=model["description"],
        framework=model["framework"],
        model_type=model["model_type"],
        task_type=model["task_type"],
        tags=model["tags"] or [],
        metadata=model["metadata"] or {},
        created_by=model["created_by"],
        team=model["team"],
        project=model["project"],
        latest_version=model["latest_version"],
        current_stage=model["current_stage"],
        created_at=model["created_at"].isoformat(),
        updated_at=model["updated_at"].isoformat(),
    )


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: str,
    model_data: ModelUpdate,
    db: databases.Database = Depends(get_database),
) -> ModelResponse:
    """Update a model"""

    # Check if model exists
    existing = await db.fetch_one(
        "SELECT * FROM models WHERE id = :id", {"id": model_id}
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID '{model_id}' not found",
        )

    # Build update query
    updates = []
    params = {"id": model_id, "updated_at": datetime.utcnow()}

    if model_data.display_name is not None:
        updates.append("display_name = :display_name")
        params["display_name"] = model_data.display_name

    if model_data.description is not None:
        updates.append("description = :description")
        params["description"] = model_data.description

    if model_data.tags is not None:
        updates.append("tags = :tags")
        params["tags"] = model_data.tags

    if model_data.metadata is not None:
        updates.append("metadata = :metadata")
        params["metadata"] = model_data.metadata

    if model_data.team is not None:
        updates.append("team = :team")
        params["team"] = model_data.team

    if model_data.project is not None:
        updates.append("project = :project")
        params["project"] = model_data.project

    if model_data.current_stage is not None:
        updates.append("current_stage = :current_stage")
        params["current_stage"] = model_data.current_stage.value

    if not updates:
        # No updates provided, return existing model
        return ModelResponse(
            id=str(existing["id"]),
            name=existing["name"],
            display_name=existing["display_name"],
            description=existing["description"],
            framework=existing["framework"],
            model_type=existing["model_type"],
            task_type=existing["task_type"],
            tags=existing["tags"] or [],
            metadata=existing["metadata"] or {},
            created_by=existing["created_by"],
            team=existing["team"],
            project=existing["project"],
            latest_version=existing["latest_version"],
            current_stage=existing["current_stage"],
            created_at=existing["created_at"].isoformat(),
            updated_at=existing["updated_at"].isoformat(),
        )

    # Execute update
    update_query = f"""
        UPDATE models
        SET {', '.join(updates)}, updated_at = :updated_at
        WHERE id = :id
    """

    await db.execute(update_query, params)

    # Fetch and return updated model
    model = await db.fetch_one("SELECT * FROM models WHERE id = :id", {"id": model_id})

    return ModelResponse(
        id=str(model["id"]),
        name=model["name"],
        display_name=model["display_name"],
        description=model["description"],
        framework=model["framework"],
        model_type=model["model_type"],
        task_type=model["task_type"],
        tags=model["tags"] or [],
        metadata=model["metadata"] or {},
        created_by=model["created_by"],
        team=model["team"],
        project=model["project"],
        latest_version=model["latest_version"],
        current_stage=model["current_stage"],
        created_at=model["created_at"].isoformat(),
        updated_at=model["updated_at"].isoformat(),
    )


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: str, db: databases.Database = Depends(get_database)):
    """Delete a model and all its versions"""

    # Check if model exists
    existing = await db.fetch_one(
        "SELECT id FROM models WHERE id = :id", {"id": model_id}
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID '{model_id}' not found",
        )

    # Delete model (cascading deletes will handle versions and experiments)
    await db.execute("DELETE FROM models WHERE id = :id", {"id": model_id})
