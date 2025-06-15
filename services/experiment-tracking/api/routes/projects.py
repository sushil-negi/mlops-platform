"""
Project management API endpoints for Experiment Tracking service
"""

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, status

from models.project import (
    PROJECT_TEMPLATES,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectStats,
    ProjectSummary,
    ProjectUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Mock data store (replace with actual database integration)
projects_store: dict[str, Any] = {}


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate) -> ProjectResponse:
    """Create a new project"""

    # Check if project name already exists
    for existing_project in projects_store.values():
        if existing_project.name == project.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with name '{project.name}' already exists",
            )

    # Create project
    from datetime import datetime

    project_id = str(uuid.uuid4())

    project_data = ProjectResponse(
        id=uuid.UUID(project_id),
        **project.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        total_experiments=0,
        active_experiments=0,
        total_runs=0,
    )

    projects_store[project_id] = project_data

    logger.info(f"Created project {project_id}: {project.name}")

    return project_data


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    team: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    owner: Optional[str] = None,
) -> ProjectListResponse:
    """List projects with filtering and pagination"""

    # Filter projects
    filtered_projects = []
    for project in projects_store.values():
        if team and project.team != team:
            continue
        if status and project.status != status:
            continue
        if tag and tag not in project.tags:
            continue
        if owner and project.owner != owner:
            continue

        # Convert to summary
        project_summary = ProjectSummary(
            id=project.id,
            name=project.name,
            description=project.description,
            team=project.team,
            owner=project.owner,
            status=project.status,
            priority=project.priority,
            tags=project.tags,
            created_at=project.created_at,
            updated_at=project.updated_at,
            experiment_count=project.total_experiments,
            recent_activity=project.updated_at,
        )

        filtered_projects.append(project_summary)

    # Sort by creation date (newest first)
    filtered_projects.sort(key=lambda p: p.created_at, reverse=True)

    # Pagination
    total = len(filtered_projects)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    page_projects = filtered_projects[start_idx:end_idx]

    total_pages = (total + size - 1) // size

    return ProjectListResponse(
        projects=page_projects,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> ProjectResponse:
    """Get project by ID"""

    if project_id not in projects_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found",
        )

    return projects_store[project_id]


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str, project_update: ProjectUpdate
) -> ProjectResponse:
    """Update project"""

    if project_id not in projects_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found",
        )

    project = projects_store[project_id]

    # Update fields
    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    # Update timestamp
    from datetime import datetime

    project.updated_at = datetime.utcnow()

    logger.info(f"Updated project {project_id}")

    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project"""

    if project_id not in projects_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found",
        )

    project = projects_store[project_id]

    # Check if project has active experiments
    if project.active_experiments > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete project with active experiments",
        )

    del projects_store[project_id]

    logger.info(f"Deleted project {project_id}: {project.name}")

    return {"message": "Project deleted successfully"}


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(project_id: str) -> ProjectStats:
    """Get project statistics"""

    if project_id not in projects_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found",
        )

    # Mock statistics (replace with actual database queries)
    from datetime import datetime, timedelta

    stats = ProjectStats(
        project_id=uuid.UUID(project_id),
        total_experiments=5,
        active_experiments=2,
        completed_experiments=3,
        total_runs=25,
        successful_runs=22,
        failed_runs=3,
        running_runs=0,
        avg_experiment_duration_hours=4.5,
        total_compute_hours=112.5,
        total_artifacts_mb=1024.0,
        total_metrics_logged=15000,
        unique_contributors=3,
        experiments_per_contributor={
            "alice@company.com": 2,
            "bob@company.com": 2,
            "charlie@company.com": 1,
        },
        last_experiment_date=datetime.utcnow() - timedelta(hours=2),
        experiments_last_7_days=2,
        experiments_last_30_days=5,
    )

    return stats


@router.get("/templates/", response_model=dict)
async def get_project_templates():
    """Get available project templates"""
    return {"templates": PROJECT_TEMPLATES, "total": len(PROJECT_TEMPLATES)}


@router.post("/from-template/{template_name}", response_model=ProjectResponse)
async def create_project_from_template(
    template_name: str, project_data: ProjectCreate
) -> ProjectResponse:
    """Create project from template"""

    if template_name not in PROJECT_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )

    template = PROJECT_TEMPLATES[template_name]

    # Merge template with provided data
    template_data = template.copy()
    project_dict = project_data.dict()

    # Update template with user data
    for key, value in project_dict.items():
        if value is not None:
            template_data[key] = value

    # Create project with template data
    template_project = ProjectCreate(**template_data)  # type: ignore
    return await create_project(template_project)
