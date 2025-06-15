"""
Serving request models for Feature Store
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ServingRequest(BaseModel):
    """Request model for online feature serving"""

    feature_sets: List[str] = Field(..., description="List of feature set names")
    entities: Dict[str, List[str]] = Field(
        ..., description="Entity type to entity IDs mapping"
    )
    features: Optional[List[str]] = Field(
        None, description="Specific features to retrieve"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feature_sets": ["user_profile", "user_activity"],
                "entities": {"user": ["user_123", "user_456"]},
                "features": ["age", "total_purchases", "last_login"],
            }
        }
    )


class PointInTimeRequest(BaseModel):
    """Request model for point-in-time feature retrieval"""

    feature_sets: List[str] = Field(..., description="List of feature set names")
    entity_df: Dict = Field(..., description="Entity dataframe with timestamps")
    features: Optional[List[str]] = Field(
        None, description="Specific features to retrieve"
    )
    timestamp_column: str = Field(
        "event_timestamp", description="Timestamp column name"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feature_sets": ["user_profile", "user_activity"],
                "entity_df": {
                    "columns": ["user_id", "event_timestamp"],
                    "data": [
                        ["user_123", "2024-01-01T10:00:00"],
                        ["user_456", "2024-01-01T11:00:00"],
                    ],
                },
                "features": ["age", "total_purchases"],
                "timestamp_column": "event_timestamp",
            }
        }
    )


class BatchServingRequest(BaseModel):
    """Request model for batch feature serving"""

    feature_sets: List[str] = Field(..., description="List of feature set names")
    entity_source: str = Field(..., description="S3/GCS path or SQL query for entities")
    output_path: str = Field(..., description="Output path for features")
    features: Optional[List[str]] = Field(
        None, description="Specific features to retrieve"
    )
    start_date: Optional[datetime] = Field(
        None, description="Start date for historical features"
    )
    end_date: Optional[datetime] = Field(
        None, description="End date for historical features"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feature_sets": ["user_profile", "user_activity"],
                "entity_source": "s3://data/entities/users.parquet",
                "output_path": "s3://features/batch/user_features.parquet",
                "features": ["age", "total_purchases", "last_login"],
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59",
            }
        }
    )


class FeatureServingResponse(BaseModel):
    """Response model for feature serving"""

    features: Dict[str, Dict[str, Any]] = Field(
        ..., description="Entity ID to features mapping"
    )
    metadata: Dict = Field(default_factory=dict, description="Response metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "features": {
                    "user_123": {
                        "age": 28,
                        "total_purchases": 156,
                        "last_login": "2024-01-15T14:30:00",
                    },
                    "user_456": {
                        "age": 35,
                        "total_purchases": 89,
                        "last_login": "2024-01-14T09:15:00",
                    },
                },
                "metadata": {
                    "feature_count": 3,
                    "entity_count": 2,
                    "cache_hit": True,
                    "latency_ms": 12.5,
                },
            }
        }
    )
