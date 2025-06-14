"""
Model Version entity for the Model Registry
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict

from core.database import Base
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class VersionStatus(str, Enum):
    """Model version status"""

    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class ModelVersion(Base):
    """Model version entity representing a specific version of a model"""

    __tablename__ = "model_versions"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    version = Column(String(50), nullable=False)  # e.g., "1.0.0", "v2.1", etc.

    # Version information
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(VersionStatus), default=VersionStatus.PENDING)

    # Model artifacts and storage
    storage_uri = Column(String(512), nullable=True)  # S3/MinIO path to model artifacts
    model_format = Column(String(50), nullable=True)  # pickle, joblib, savedmodel, etc.
    model_size_bytes = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True)  # SHA256 checksum for integrity

    # Performance metrics
    training_metrics = Column(JSON, default=dict)  # Training performance metrics
    validation_metrics = Column(JSON, default=dict)  # Validation performance metrics
    test_metrics = Column(JSON, default=dict)  # Test performance metrics

    # Model signature and schema
    input_schema = Column(JSON, nullable=True)  # Expected input schema
    output_schema = Column(JSON, nullable=True)  # Expected output schema
    model_signature = Column(JSON, nullable=True)  # MLflow-style model signature

    # Training information
    training_data_hash = Column(String(64), nullable=True)  # Hash of training data
    training_duration_seconds = Column(Float, nullable=True)
    training_parameters = Column(JSON, default=dict)  # Hyperparameters used
    feature_names = Column(JSON, default=list)  # List of feature names

    # Lineage and provenance
    parent_version_id = Column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True
    )
    experiment_id = Column(
        UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=True
    )
    run_id = Column(String(255), nullable=True)  # MLflow run ID if applicable

    # Environment and dependencies
    python_version = Column(String(20), nullable=True)
    dependencies = Column(JSON, default=list)  # List of package dependencies
    environment = Column(JSON, default=dict)  # Environment variables and config

    # Deployment information
    deployed_at = Column(DateTime, nullable=True)
    deployment_config = Column(JSON, default=dict)

    # Metadata and tags
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)

    # Audit information
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    model = relationship("Model", back_populates="versions")
    experiment = relationship("Experiment", back_populates="versions")
    artifacts = relationship(
        "Artifact", back_populates="version", cascade="all, delete-orphan"
    )
    parent_version = relationship("ModelVersion", remote_side=[id])

    def __repr__(self):
        return f"<ModelVersion(id={self.id}, version={self.version}, model_id={self.model_id})>"

    def to_dict(self) -> Dict:
        """Convert model version to dictionary representation"""
        return {
            "id": str(self.id),
            "model_id": str(self.model_id),
            "version": self.version,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "storage_uri": self.storage_uri,
            "model_format": self.model_format,
            "model_size_bytes": self.model_size_bytes,
            "checksum": self.checksum,
            "training_metrics": self.training_metrics or {},
            "validation_metrics": self.validation_metrics or {},
            "test_metrics": self.test_metrics or {},
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "model_signature": self.model_signature,
            "training_data_hash": self.training_data_hash,
            "training_duration_seconds": self.training_duration_seconds,
            "training_parameters": self.training_parameters or {},
            "feature_names": self.feature_names or [],
            "parent_version_id": (
                str(self.parent_version_id) if self.parent_version_id else None
            ),
            "experiment_id": str(self.experiment_id) if self.experiment_id else None,
            "run_id": self.run_id,
            "python_version": self.python_version,
            "dependencies": self.dependencies or [],
            "environment": self.environment or {},
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "deployment_config": self.deployment_config or {},
            "tags": self.tags or [],
            "metadata": self.metadata or {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
