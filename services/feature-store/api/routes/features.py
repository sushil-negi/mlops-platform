"""
Feature management API endpoints
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from models.feature import Feature, FeatureStatus, FeatureType

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for API
class FeatureCreate(BaseModel):
    """Request model for creating a feature"""

    name: str = Field(..., min_length=1, max_length=255)
    feature_set_id: str
    description: Optional[str] = None
    data_type: FeatureType
    default_value: Optional[Any] = None
    transformation: Optional[str] = None
    aggregations: Optional[List[str]] = []
    window_size: Optional[str] = None
    validation_rules: Optional[Dict] = {}
    tags: Optional[List[str]] = []


class FeatureUpdate(BaseModel):
    """Request model for updating a feature"""

    description: Optional[str] = None
    default_value: Optional[Any] = None
    transformation: Optional[str] = None
    aggregations: Optional[List[str]] = None
    window_size: Optional[str] = None
    validation_rules: Optional[Dict] = None
    tags: Optional[List[str]] = None
    status: Optional[FeatureStatus] = None


class FeatureResponse(BaseModel):
    """Response model for feature"""

    id: str
    name: str
    feature_set_id: str
    description: Optional[str]
    data_type: str
    default_value: Optional[any]
    transformation: Optional[str]
    aggregations: List[str]
    window_size: Optional[str]
    validation_rules: Dict
    tags: List[str]
    status: str
    version: int
    statistics: Dict
    created_at: str
    updated_at: str


@router.post("/", response_model=FeatureResponse, status_code=status.HTTP_201_CREATED)
async def create_feature(
    feature_data: FeatureCreate, db: Session = Depends(get_db)
) -> FeatureResponse:
    """Create a new feature"""

    try:
        # Check if feature already exists
        existing = (
            db.query(Feature)
            .filter(
                Feature.name == feature_data.name,
                Feature.feature_set_id == feature_data.feature_set_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Feature '{feature_data.name}' already exists in this "
                    "feature set"
                ),
            )

        # Create feature
        feature = Feature(
            name=feature_data.name,
            feature_set_id=UUID(feature_data.feature_set_id),
            description=feature_data.description,
            data_type=feature_data.data_type,
            default_value=feature_data.default_value,
            transformation=feature_data.transformation,
            aggregations=feature_data.aggregations,
            window_size=feature_data.window_size,
            validation_rules=feature_data.validation_rules,
            tags=feature_data.tags,
            status=FeatureStatus.DRAFT,
        )

        db.add(feature)
        db.commit()
        db.refresh(feature)

        logger.info(f"Created feature: {feature.name}")

        return FeatureResponse(**feature.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating feature: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create feature",
        )


@router.get("/{feature_id}", response_model=FeatureResponse)
async def get_feature(
    feature_id: str, db: Session = Depends(get_db)
) -> FeatureResponse:
    """Get a specific feature"""

    feature = db.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature with ID '{feature_id}' not found",
        )

    return FeatureResponse(**feature.to_dict())


@router.get("/", response_model=List[FeatureResponse])
async def list_features(
    feature_set_id: Optional[str] = None,
    status: Optional[FeatureStatus] = None,
    tag: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[FeatureResponse]:
    """List features with filtering"""

    query = db.query(Feature)

    if feature_set_id:
        query = query.filter(Feature.feature_set_id == feature_set_id)

    if status:
        query = query.filter(Feature.status == status)

    if tag:
        query = query.filter(Feature.tags.contains([tag]))

    features = query.offset(skip).limit(limit).all()

    return [FeatureResponse(**f.to_dict()) for f in features]


@router.patch("/{feature_id}", response_model=FeatureResponse)
async def update_feature(
    feature_id: str, update_data: FeatureUpdate, db: Session = Depends(get_db)
) -> FeatureResponse:
    """Update a feature"""

    feature = db.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature with ID '{feature_id}' not found",
        )

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(feature, field, value)

    # Increment version
    feature.version = (feature.version or 1) + 1

    db.commit()
    db.refresh(feature)

    logger.info(f"Updated feature: {feature.name}")

    return FeatureResponse(**feature.to_dict())


@router.delete("/{feature_id}")
async def delete_feature(feature_id: str, db: Session = Depends(get_db)) -> Dict:
    """Delete a feature"""

    feature = db.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature with ID '{feature_id}' not found",
        )

    # Check if feature can be deleted
    if feature.status == FeatureStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active feature. Archive it first.",
        )

    feature_name = feature.name
    db.delete(feature)
    db.commit()

    logger.info(f"Deleted feature: {feature_name}")

    return {"message": f"Feature '{feature_name}' deleted successfully"}


@router.post("/{feature_id}/activate")
async def activate_feature(feature_id: str, db: Session = Depends(get_db)) -> Dict:
    """Activate a feature"""

    feature = db.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature with ID '{feature_id}' not found",
        )

    if feature.status == FeatureStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feature is already active",
        )

    feature.status = FeatureStatus.ACTIVE
    db.commit()

    logger.info(f"Activated feature: {feature.name}")

    return {
        "message": f"Feature '{feature.name}' activated successfully",
        "feature_id": feature_id,
        "status": "active",
    }


@router.post("/{feature_id}/archive")
async def archive_feature(feature_id: str, db: Session = Depends(get_db)) -> Dict:
    """Archive a feature"""

    feature = db.query(Feature).filter(Feature.id == feature_id).first()

    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature with ID '{feature_id}' not found",
        )

    feature.status = FeatureStatus.ARCHIVED
    db.commit()

    logger.info(f"Archived feature: {feature.name}")

    return {
        "message": f"Feature '{feature.name}' archived successfully",
        "feature_id": feature_id,
        "status": "archived",
    }
