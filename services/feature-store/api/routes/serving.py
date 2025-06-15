"""
Feature serving API endpoints
"""

import logging
import time
from datetime import datetime
from typing import Dict

from core.database import get_db
from core.serving_engine import ServingEngine
from fastapi import APIRouter, Depends, HTTPException, status
from models.serving_request import (BatchServingRequest,
                                    FeatureServingResponse, PointInTimeRequest,
                                    ServingRequest)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/online", response_model=FeatureServingResponse)
async def get_online_features(
    request: ServingRequest,
    serving_engine: ServingEngine = Depends(lambda req: req.app.state.serving_engine),
) -> FeatureServingResponse:
    """
    Get online features for real-time serving

    This endpoint retrieves the latest feature values for given entities
    from the online store with low latency.
    """
    start_time = time.time()

    try:
        # Get features from serving engine
        features = await serving_engine.get_online_features(
            feature_sets=request.feature_sets,
            entities=request.entities,
            features=request.features,
        )

        # Calculate metadata
        latency_ms = (time.time() - start_time) * 1000
        feature_count = len(request.features) if request.features else 0
        entity_count = sum(len(ids) for ids in request.entities.values())

        return FeatureServingResponse(
            features=features,
            metadata={
                "feature_count": feature_count,
                "entity_count": entity_count,
                "latency_ms": round(latency_ms, 2),
                "cache_hit": True if latency_ms < 10 else False,  # Simple heuristic
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error serving online features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve features",
        )


@router.post("/historical", response_model=Dict)
async def get_historical_features(
    request: PointInTimeRequest,
    serving_engine: ServingEngine = Depends(lambda req: req.app.state.serving_engine),
) -> Dict:
    """
    Get point-in-time correct features for historical analysis

    This endpoint retrieves feature values as they were at specific timestamps,
    essential for training ML models and backtesting.
    """
    start_time = time.time()

    try:
        # Convert entity dataframe from request
        import pandas as pd

        entity_df = pd.DataFrame(
            request.entity_df["data"], columns=request.entity_df["columns"]
        )

        # Convert timestamp column to datetime
        if request.timestamp_column in entity_df.columns:
            entity_df[request.timestamp_column] = pd.to_datetime(
                entity_df[request.timestamp_column]
            )

        # Get historical features
        result_df = await serving_engine.get_historical_features(
            feature_sets=request.feature_sets,
            entity_df=entity_df,
            features=request.features,
            timestamp_column=request.timestamp_column,
        )

        # Convert result to JSON-serializable format
        result = {
            "columns": result_df.columns.tolist(),
            "data": result_df.values.tolist(),
            "shape": result_df.shape,
            "metadata": {
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "row_count": len(result_df),
                "feature_count": len(result_df.columns) - len(entity_df.columns),
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error serving historical features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve historical features",
        )


@router.post("/batch")
async def submit_batch_serving_job(
    request: BatchServingRequest, db: Session = Depends(get_db)
) -> Dict:
    """
    Submit a batch feature serving job

    This endpoint processes large-scale feature retrieval jobs asynchronously,
    writing results to specified storage locations.
    """

    try:
        # TODO: Implement batch serving job submission
        # This would typically:
        # 1. Validate the request
        # 2. Submit job to a distributed processing engine (Spark, Dask, etc.)
        # 3. Return job ID for tracking

        # For now, return mock response
        job_id = "batch-job-" + str(int(time.time()))

        logger.info(f"Submitted batch serving job: {job_id}")

        return {
            "job_id": job_id,
            "status": "submitted",
            "feature_sets": request.feature_sets,
            "entity_source": request.entity_source,
            "output_path": request.output_path,
            "estimated_completion_time": "2024-01-01T12:00:00",
            "message": "Batch serving job submitted successfully",
        }

    except Exception as e:
        logger.error(f"Error submitting batch serving job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit batch serving job",
        )


@router.get("/batch/{job_id}")
async def get_batch_job_status(job_id: str) -> Dict:
    """Get status of a batch serving job"""

    # TODO: Implement actual job status tracking
    # For now, return mock status

    return {
        "job_id": job_id,
        "status": "running",
        "progress": 65,
        "started_at": "2024-01-01T11:00:00",
        "rows_processed": 150000,
        "estimated_completion": "2024-01-01T12:00:00",
    }


@router.post("/validate")
async def validate_serving_request(
    request: ServingRequest, db: Session = Depends(get_db)
) -> Dict:
    """
    Validate a feature serving request

    This endpoint checks if the requested features and entities are valid
    without actually retrieving the data.
    """

    try:
        # Validate feature sets exist
        from models.feature_set import FeatureSet

        issues = []
        valid_features = []

        for fs_name in request.feature_sets:
            feature_set = (
                db.query(FeatureSet).filter(FeatureSet.name == fs_name).first()
            )

            if not feature_set:
                issues.append(f"Feature set '{fs_name}' not found")
            elif feature_set.status != "active":
                issues.append(f"Feature set '{fs_name}' is not active")
            else:
                # Check if requested features exist
                if request.features:
                    fs_features = feature_set.get_feature_names()
                    for feature in request.features:
                        if feature in fs_features:
                            valid_features.append(feature)
                        else:
                            issues.append(
                                f"Feature '{feature}' not found in '{fs_name}'"
                            )

        is_valid = len(issues) == 0

        return {
            "valid": is_valid,
            "issues": issues,
            "valid_features": valid_features,
            "feature_count": len(valid_features),
            "entity_count": sum(len(ids) for ids in request.entities.values()),
        }

    except Exception as e:
        logger.error(f"Error validating serving request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate request",
        )
