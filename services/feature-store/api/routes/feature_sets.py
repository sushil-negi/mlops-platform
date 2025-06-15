"""
Feature Set management API endpoints
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from storage.feature_storage import FeatureStorage

from core.database import get_db
from models.feature_set import FeatureSet, FeatureSetStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for API
class FeatureSetCreate(BaseModel):
    """Request model for creating a feature set"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    owner: str
    team: Optional[str] = None
    entities: List[str]
    entity_join_keys: Optional[Dict[str, str]] = {}
    source_type: str = "batch"
    source_config: Optional[Dict] = {}
    offline_enabled: bool = True
    online_enabled: bool = True
    materialization_enabled: bool = True
    materialization_schedule: Optional[str] = None
    ttl_offline_days: Optional[int] = None
    ttl_online_hours: Optional[int] = None
    tags: Optional[List[str]] = []


class FeatureSetUpdate(BaseModel):
    """Request model for updating a feature set"""

    description: Optional[str] = None
    owner: Optional[str] = None
    team: Optional[str] = None
    source_config: Optional[Dict] = None
    materialization_enabled: Optional[bool] = None
    materialization_schedule: Optional[str] = None
    ttl_offline_days: Optional[int] = None
    ttl_online_hours: Optional[int] = None
    tags: Optional[List[str]] = None
    status: Optional[FeatureSetStatus] = None


class FeatureSetResponse(BaseModel):
    """Response model for feature set"""

    id: str
    name: str
    version: int
    description: Optional[str]
    owner: str
    team: Optional[str]
    entities: List[str]
    entity_join_keys: Dict[str, str]
    source_type: str
    source_config: Dict
    offline_enabled: bool
    online_enabled: bool
    materialization_enabled: bool
    materialization_schedule: Optional[str]
    statistics: Dict
    status: str
    created_at: str
    updated_at: str
    features: List[Dict]


@router.post(
    "/", response_model=FeatureSetResponse, status_code=status.HTTP_201_CREATED
)
async def create_feature_set(
    feature_set_data: FeatureSetCreate, db: Session = Depends(get_db)
) -> FeatureSetResponse:
    """Create a new feature set"""

    try:
        # Check if feature set already exists
        existing = (
            db.query(FeatureSet)
            .filter(FeatureSet.name == feature_set_data.name)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Feature set '{feature_set_data.name}' already exists",
            )

        # Create feature set
        feature_set = FeatureSet(
            name=feature_set_data.name,
            description=feature_set_data.description,
            owner=feature_set_data.owner,
            team=feature_set_data.team,
            entities=feature_set_data.entities,
            entity_join_keys=feature_set_data.entity_join_keys,
            source_type=feature_set_data.source_type,
            source_config=feature_set_data.source_config,
            offline_enabled=feature_set_data.offline_enabled,
            online_enabled=feature_set_data.online_enabled,
            materialization_enabled=feature_set_data.materialization_enabled,
            materialization_schedule=feature_set_data.materialization_schedule,
            ttl_offline_days=feature_set_data.ttl_offline_days,
            ttl_online_hours=feature_set_data.ttl_online_hours,
            tags=feature_set_data.tags,
            status=FeatureSetStatus.DRAFT,
        )

        db.add(feature_set)
        db.commit()
        db.refresh(feature_set)

        logger.info(f"Created feature set: {feature_set.name}")

        return FeatureSetResponse(**feature_set.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating feature set: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create feature set",
        )


@router.get("/{feature_set_id}", response_model=FeatureSetResponse)
async def get_feature_set(
    feature_set_id: str, db: Session = Depends(get_db)
) -> FeatureSetResponse:
    """Get a specific feature set"""

    feature_set = db.query(FeatureSet).filter(FeatureSet.id == feature_set_id).first()

    if not feature_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature set with ID '{feature_set_id}' not found",
        )

    return FeatureSetResponse(**feature_set.to_dict())


@router.get("/", response_model=List[FeatureSetResponse])
async def list_feature_sets(
    owner: Optional[str] = None,
    team: Optional[str] = None,
    status: Optional[FeatureSetStatus] = None,
    tag: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[FeatureSetResponse]:
    """List feature sets with filtering"""

    query = db.query(FeatureSet)

    if owner:
        query = query.filter(FeatureSet.owner == owner)

    if team:
        query = query.filter(FeatureSet.team == team)

    if status:
        query = query.filter(FeatureSet.status == status)

    if tag:
        query = query.filter(FeatureSet.tags.contains([tag]))

    feature_sets = query.offset(skip).limit(limit).all()

    return [FeatureSetResponse(**fs.to_dict()) for fs in feature_sets]


@router.patch("/{feature_set_id}", response_model=FeatureSetResponse)
async def update_feature_set(
    feature_set_id: str, update_data: FeatureSetUpdate, db: Session = Depends(get_db)
) -> FeatureSetResponse:
    """Update a feature set"""

    feature_set = db.query(FeatureSet).filter(FeatureSet.id == feature_set_id).first()

    if not feature_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature set with ID '{feature_set_id}' not found",
        )

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(feature_set, field, value)

    # Increment version
    feature_set.version = (feature_set.version or 1) + 1

    db.commit()
    db.refresh(feature_set)

    logger.info(f"Updated feature set: {feature_set.name}")

    return FeatureSetResponse(**feature_set.to_dict())


@router.delete("/{feature_set_id}")
async def delete_feature_set(
    feature_set_id: str, db: Session = Depends(get_db)
) -> Dict:
    """Delete a feature set"""

    feature_set = db.query(FeatureSet).filter(FeatureSet.id == feature_set_id).first()

    if not feature_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature set with ID '{feature_set_id}' not found",
        )

    # Check if feature set can be deleted
    if feature_set.status == FeatureSetStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active feature set. Archive it first.",
        )

    feature_set_name = feature_set.name
    db.delete(feature_set)
    db.commit()

    logger.info(f"Deleted feature set: {feature_set_name}")

    return {"message": f"Feature set '{feature_set_name}' deleted successfully"}


@router.post("/{feature_set_id}/activate")
async def activate_feature_set(
    feature_set_id: str, db: Session = Depends(get_db)
) -> Dict:
    """Activate a feature set"""

    feature_set = db.query(FeatureSet).filter(FeatureSet.id == feature_set_id).first()

    if not feature_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature set with ID '{feature_set_id}' not found",
        )

    if feature_set.status == FeatureSetStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feature set is already active",
        )

    # Validate feature set has features
    if not feature_set.features:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot activate feature set without features",
        )

    feature_set.status = FeatureSetStatus.ACTIVE
    db.commit()

    logger.info(f"Activated feature set: {feature_set.name}")

    return {
        "message": f"Feature set '{feature_set.name}' activated successfully",
        "feature_set_id": feature_set_id,
        "status": "active",
    }


@router.post("/{feature_set_id}/materialize")
async def materialize_feature_set(
    feature_set_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    storage: FeatureStorage = Depends(lambda: FeatureStorage()),
) -> Dict:
    """Trigger materialization for a feature set"""

    feature_set = db.query(FeatureSet).filter(FeatureSet.id == feature_set_id).first()

    if not feature_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature set with ID '{feature_set_id}' not found",
        )

    if feature_set.status != FeatureSetStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feature set must be active to materialize",
        )

    if not feature_set.materialization_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Materialization is not enabled for this feature set",
        )

    # Use default dates if not provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=1)

    # TODO: Submit materialization job to scheduler
    # For now, return mock response

    logger.info(f"Triggered materialization for feature set: {feature_set.name}")

    return {
        "message": f"Materialization triggered for '{feature_set.name}'",
        "feature_set_id": feature_set_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "job_id": "mock-job-id",
        "status": "submitted",
    }


@router.get("/{feature_set_id}/statistics")
async def get_feature_set_statistics(
    feature_set_id: str, db: Session = Depends(get_db)
) -> Dict:
    """Get statistics for a feature set"""

    feature_set = db.query(FeatureSet).filter(FeatureSet.id == feature_set_id).first()

    if not feature_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature set with ID '{feature_set_id}' not found",
        )

    # Return current statistics and additional computed metrics
    stats = feature_set.statistics or {}

    return {
        "feature_set_id": feature_set_id,
        "feature_set_name": feature_set.name,
        "statistics": stats,
        "feature_count": len(feature_set.features),
        "active_features": len(feature_set.get_active_features()),
        "row_count": feature_set.row_count,
        "size_bytes": feature_set.size_bytes,
        "last_materialization": (
            feature_set.last_materialization.isoformat()
            if feature_set.last_materialization
            else None
        ),
        "status": feature_set.status.value,
    }
