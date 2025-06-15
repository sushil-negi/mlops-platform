"""
Feature Set model for Feature Store
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List
from uuid import uuid4

from core.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship


class FeatureSetStatus(str, Enum):
    """Feature set lifecycle status"""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class FeatureSet(Base):
    """Feature set definition model"""

    __tablename__ = "feature_sets"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Feature set identification
    name = Column(String(255), nullable=False, unique=True)
    version = Column(Integer, default=1)

    # Metadata
    description = Column(Text)
    owner = Column(String(255))
    team = Column(String(255))
    tags = Column(JSON, default=list)

    # Entity configuration
    entities = Column(JSON, nullable=False)  # List of entity names/types
    entity_join_keys = Column(JSON, default=dict)  # Mapping of entity to join key

    # Data source configuration
    source_type = Column(String(50))  # batch, stream, request
    source_config = Column(JSON, default=dict)

    # Storage configuration
    offline_enabled = Column(Boolean, default=True)
    online_enabled = Column(Boolean, default=True)
    storage_config = Column(JSON, default=dict)

    # Materialization configuration
    materialization_enabled = Column(Boolean, default=True)
    materialization_schedule = Column(String(100))  # cron expression
    materialization_start_date = Column(DateTime)
    materialization_end_date = Column(DateTime)
    materialization_max_delay = Column(Integer)  # seconds

    # TTL configuration
    ttl_offline_days = Column(Integer)
    ttl_online_hours = Column(Integer)

    # Statistics and monitoring
    statistics = Column(JSON, default=dict)
    last_materialization = Column(DateTime)
    row_count = Column(Integer, default=0)
    size_bytes = Column(Integer, default=0)

    # Status and lifecycle
    status = Column(SQLEnum(FeatureSetStatus), default=FeatureSetStatus.DRAFT)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    updated_by = Column(String(255))

    # Relationships
    features = relationship(
        "Feature", back_populates="feature_set", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_feature_set_name", "name"),
        Index("idx_feature_set_status", "status"),
        Index("idx_feature_set_owner", "owner"),
        Index("idx_feature_set_created", "created_at"),
    )

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "id": str(self.id),
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "owner": self.owner,
            "team": self.team,
            "tags": self.tags or [],
            "entities": self.entities or [],
            "entity_join_keys": self.entity_join_keys or {},
            "source_type": self.source_type,
            "source_config": self.source_config or {},
            "offline_enabled": self.offline_enabled,
            "online_enabled": self.online_enabled,
            "materialization_enabled": self.materialization_enabled,
            "materialization_schedule": self.materialization_schedule,
            "statistics": self.statistics or {},
            "last_materialization": (
                self.last_materialization.isoformat()
                if self.last_materialization
                else None
            ),
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "features": [f.to_dict() for f in self.features] if self.features else [],
        }

    def get_feature_names(self) -> List[str]:
        """Get list of feature names in this set"""
        return [f.name for f in self.features]

    def get_active_features(self) -> List:
        """Get list of active features"""
        from .feature import FeatureStatus

        return [f for f in self.features if f.status == FeatureStatus.ACTIVE]
