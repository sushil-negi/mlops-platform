"""
Feature model for Feature Store
"""

from datetime import datetime
from enum import Enum
from typing import Dict
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from core.database import Base


class FeatureType(str, Enum):
    """Feature data types"""

    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    ARRAY = "array"
    STRUCT = "struct"
    BINARY = "binary"


class FeatureStatus(str, Enum):
    """Feature lifecycle status"""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class Feature(Base):
    """Feature definition model"""

    __tablename__ = "features"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Feature identification
    name = Column(String(255), nullable=False)
    feature_set_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("feature_sets.id"), nullable=False
    )

    # Feature metadata
    description = Column(Text)
    data_type = Column(SQLEnum(FeatureType), nullable=False)
    default_value = Column(JSON)
    tags = Column(JSON, default=list)

    # Feature configuration
    transformation = Column(Text)  # SQL or Python expression
    aggregations = Column(JSON, default=list)  # e.g., ["sum", "avg", "min", "max"]
    window_size = Column(String(50))  # e.g., "1h", "1d", "7d"

    # Validation rules
    validation_rules = Column(JSON, default=dict)
    min_value = Column(JSON)
    max_value = Column(JSON)
    allowed_values = Column(JSON)

    # Status and lifecycle
    status = Column(SQLEnum(FeatureStatus), default=FeatureStatus.DRAFT)
    version = Column(Integer, default=1)

    # Lineage
    source_features = Column(JSON, default=list)  # IDs of features this is derived from
    downstream_features = Column(
        JSON, default=list
    )  # IDs of features derived from this

    # Statistics
    statistics = Column(JSON, default=dict)
    last_computed = Column(DateTime)
    compute_cost = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    updated_by = Column(String(255))

    # Relationships
    feature_set = relationship("FeatureSet", back_populates="features")
    values = relationship(
        "FeatureValue", back_populates="feature", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_feature_name_set", "name", "feature_set_id", unique=True),
        Index("idx_feature_status", "status"),
        Index("idx_feature_created", "created_at"),
    )

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "id": str(self.id),
            "name": self.name,
            "feature_set_id": str(self.feature_set_id),
            "description": self.description,
            "data_type": self.data_type.value if self.data_type else None,
            "default_value": self.default_value,
            "tags": self.tags or [],
            "transformation": self.transformation,
            "aggregations": self.aggregations or [],
            "window_size": self.window_size,
            "validation_rules": self.validation_rules or {},
            "status": self.status.value if self.status else None,
            "version": self.version,
            "statistics": self.statistics or {},
            "last_computed": (
                self.last_computed.isoformat() if self.last_computed else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def validate_value(self, value: any) -> bool:
        """Validate a value against feature rules"""
        if value is None and self.default_value is not None:
            return True

        # Type validation
        if self.data_type == FeatureType.INT and not isinstance(value, int):
            return False
        elif self.data_type == FeatureType.FLOAT and not isinstance(
            value, (int, float)
        ):
            return False
        elif self.data_type == FeatureType.STRING and not isinstance(value, str):
            return False
        elif self.data_type == FeatureType.BOOLEAN and not isinstance(value, bool):
            return False

        # Range validation
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False

        # Allowed values validation
        if self.allowed_values and value not in self.allowed_values:
            return False

        return True
