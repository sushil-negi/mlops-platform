"""
Feature Value model for Feature Store
"""

from datetime import datetime
from typing import Dict
from uuid import uuid4

from core.database import Base
from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, ForeignKey,
                        Index, Integer, String)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship


class FeatureValue(Base):
    """Feature value storage model"""

    __tablename__ = "feature_values"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Feature reference
    feature_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("features.id"), nullable=False
    )

    # Entity identification
    entity_id = Column(String(255), nullable=False)
    entity_type = Column(String(50), nullable=False)

    # Feature value (stored in appropriate column based on type)
    value_int = Column(Integer)
    value_float = Column(Float)
    value_string = Column(String)
    value_bool = Column(Boolean)
    value_json = Column(JSON)

    # Temporal information
    event_timestamp = Column(DateTime, nullable=False)
    created_timestamp = Column(DateTime, default=datetime.utcnow)

    # Versioning
    version = Column(Integer, default=1)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Relationships
    feature = relationship("Feature", back_populates="values")

    # Indexes for fast lookup
    __table_args__ = (
        Index("idx_feature_value_lookup", "feature_id", "entity_id", "event_timestamp"),
        Index("idx_feature_value_entity", "entity_id", "entity_type"),
        Index("idx_feature_value_timestamp", "event_timestamp"),
        Index("idx_feature_value_created", "created_timestamp"),
    )

    def get_value(self):
        """Get the actual value based on feature type"""
        if self.value_int is not None:
            return self.value_int
        elif self.value_float is not None:
            return self.value_float
        elif self.value_string is not None:
            return self.value_string
        elif self.value_bool is not None:
            return self.value_bool
        elif self.value_json is not None:
            return self.value_json
        return None

    def set_value(self, value, data_type: str):
        """Set value in appropriate column based on data type"""
        # Clear all value columns
        self.value_int = None
        self.value_float = None
        self.value_string = None
        self.value_bool = None
        self.value_json = None

        # Set value in appropriate column
        if data_type == "int":
            self.value_int = int(value)
        elif data_type == "float":
            self.value_float = float(value)
        elif data_type == "string":
            self.value_string = str(value)
        elif data_type == "boolean":
            self.value_bool = bool(value)
        else:
            # Store complex types as JSON
            self.value_json = value

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "id": str(self.id),
            "feature_id": str(self.feature_id),
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "value": self.get_value(),
            "event_timestamp": (
                self.event_timestamp.isoformat() if self.event_timestamp else None
            ),
            "created_timestamp": (
                self.created_timestamp.isoformat() if self.created_timestamp else None
            ),
            "version": self.version,
            "metadata": self.metadata or {},
        }
