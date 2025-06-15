"""
Artifact entity for the Model Registry
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class ArtifactType(str, Enum):
    """Types of artifacts that can be stored"""

    MODEL = "model"  # Trained model binary
    DATASET = "dataset"  # Training/validation datasets
    METRICS = "metrics"  # Performance metrics and reports
    PLOT = "plot"  # Visualization artifacts
    LOG = "log"  # Training logs
    CONFIG = "config"  # Configuration files
    CHECKPOINT = "checkpoint"  # Model checkpoints
    FEATURE_IMPORTANCE = "feature_importance"  # Feature importance data
    CONFUSION_MATRIX = "confusion_matrix"  # Classification results
    PREDICTION = "prediction"  # Model predictions
    OTHER = "other"  # Other artifact types


class Artifact(Base):
    """Artifact entity for storing various files related to models and experiments"""

    __tablename__ = "artifacts"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Type and format
    artifact_type = Column(SQLEnum(ArtifactType), nullable=False)
    file_format = Column(String(50), nullable=True)  # json, png, pkl, h5, etc.
    content_type = Column(String(100), nullable=True)  # MIME type

    # Storage information
    storage_uri = Column(String(512), nullable=False)  # Full path to the artifact
    storage_backend = Column(String(50), nullable=False)  # s3, minio, local, etc.
    file_size_bytes = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True)  # SHA256 checksum

    # Relationships - can belong to either a model version or experiment
    version_id = Column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True
    )
    experiment_id = Column(
        UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=True
    )

    # Metadata and properties
    properties = Column(JSON, default=dict)  # Artifact-specific properties
    tags = Column(JSON, default=list)  # Tags for categorization
    metadata = Column(JSON, default=dict)  # Additional metadata

    # Access and permissions
    is_public = Column(
        String(10), default="false"
    )  # Whether artifact is publicly accessible
    access_permissions = Column(JSON, default=dict)  # Access control settings

    # Versioning for artifacts
    artifact_version = Column(String(50), default="1.0")
    parent_artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=True
    )

    # Lifecycle management
    expiry_date = Column(DateTime, nullable=True)  # When artifact should be cleaned up
    is_active = Column(String(10), default="true")  # Whether artifact is active

    # Audit information
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)

    # Relationships
    version = relationship("ModelVersion", back_populates="artifacts")
    experiment = relationship("Experiment", back_populates="artifacts")
    parent_artifact = relationship("Artifact", remote_side=[id])

    def __repr__(self):
        return f"<Artifact(id={self.id}, name={self.name}, type={self.artifact_type})>"

    def to_dict(self) -> Dict:
        """Convert artifact to dictionary representation"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "artifact_type": self.artifact_type.value if self.artifact_type else None,
            "file_format": self.file_format,
            "content_type": self.content_type,
            "storage_uri": self.storage_uri,
            "storage_backend": self.storage_backend,
            "file_size_bytes": self.file_size_bytes,
            "checksum": self.checksum,
            "version_id": str(self.version_id) if self.version_id else None,
            "experiment_id": str(self.experiment_id) if self.experiment_id else None,
            "properties": self.properties or {},
            "tags": self.tags or [],
            "metadata": self.metadata or {},
            "is_public": self.is_public,
            "access_permissions": self.access_permissions or {},
            "artifact_version": self.artifact_version,
            "parent_artifact_id": (
                str(self.parent_artifact_id) if self.parent_artifact_id else None
            ),
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_accessed": (
                self.last_accessed.isoformat() if self.last_accessed else None
            ),
            "access_count": self.access_count,
        }
