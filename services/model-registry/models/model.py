"""
Model entity for the Model Registry
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict

from core.database import Base
from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ModelStage(str, Enum):
    """Model lifecycle stages"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelFramework(str, Enum):
    """Supported ML frameworks"""

    SKLEARN = "sklearn"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    ONNX = "onnx"
    CUSTOM = "custom"


class Model(Base):
    """Model entity representing a machine learning model"""

    __tablename__ = "models"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Framework and type information
    framework = Column(SQLEnum(ModelFramework), nullable=False)
    model_type = Column(
        String(100), nullable=False
    )  # classification, regression, clustering, etc.
    task_type = Column(
        String(100), nullable=True
    )  # binary_classification, multi_class, etc.

    # Metadata
    tags = Column(JSON, default=list)  # List of tags for categorization
    metadata = Column(JSON, default=dict)  # Additional custom metadata

    # Ownership and governance
    created_by = Column(String(255), nullable=False)
    team = Column(String(255), nullable=True)
    project = Column(String(255), nullable=True)

    # Current state
    latest_version = Column(String(50), nullable=True)
    current_stage = Column(SQLEnum(ModelStage), default=ModelStage.DEVELOPMENT)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    versions = relationship(
        "ModelVersion", back_populates="model", cascade="all, delete-orphan"
    )
    experiments = relationship(
        "Experiment", back_populates="model", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Model(id={self.id}, name={self.name}, framework={self.framework})>"

    def to_dict(self) -> Dict:
        """Convert model to dictionary representation"""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "framework": self.framework.value if self.framework else None,
            "model_type": self.model_type,
            "task_type": self.task_type,
            "tags": self.tags or [],
            "metadata": self.metadata or {},
            "created_by": self.created_by,
            "team": self.team,
            "project": self.project,
            "latest_version": self.latest_version,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
