"""
Experiment entity for the Model Registry
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict

from core.database import Base
from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ExperimentStatus(str, Enum):
    """Experiment status"""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Experiment(Base):
    """Experiment entity for tracking model training experiments"""

    __tablename__ = "experiments"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Parent model
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)

    # Experiment metadata
    status = Column(SQLEnum(ExperimentStatus), default=ExperimentStatus.RUNNING)
    experiment_type = Column(
        String(100), nullable=True
    )  # training, tuning, evaluation, etc.

    # Execution information
    run_id = Column(
        String(255), nullable=True, unique=True
    )  # External run ID (MLflow, etc.)
    execution_environment = Column(JSON, default=dict)  # Environment details

    # Configuration
    parameters = Column(JSON, default=dict)  # Hyperparameters and config
    data_config = Column(JSON, default=dict)  # Data sources and preprocessing
    model_config = Column(JSON, default=dict)  # Model architecture and settings

    # Results and metrics
    metrics = Column(JSON, default=dict)  # All metrics from the experiment
    final_metrics = Column(JSON, default=dict)  # Final/best metrics

    # Execution details
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Resource usage
    compute_resources = Column(JSON, default=dict)  # CPU, GPU, memory usage
    cost_estimate = Column(Float, nullable=True)  # Estimated compute cost

    # Lineage
    parent_experiment_id = Column(
        UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=True
    )
    data_sources = Column(JSON, default=list)  # List of data sources used
    code_version = Column(String(255), nullable=True)  # Git commit hash

    # Tags and metadata
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)

    # Audit information
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    model = relationship("Model", back_populates="experiments")
    versions = relationship("ModelVersion", back_populates="experiment")
    parent_experiment = relationship("Experiment", remote_side=[id])
    artifacts = relationship(
        "Artifact", back_populates="experiment", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Experiment(id={self.id}, name={self.name}, status={self.status})>"

    def to_dict(self) -> Dict:
        """Convert experiment to dictionary representation"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "model_id": str(self.model_id),
            "status": self.status.value if self.status else None,
            "experiment_type": self.experiment_type,
            "run_id": self.run_id,
            "execution_environment": self.execution_environment or {},
            "parameters": self.parameters or {},
            "data_config": self.data_config or {},
            "model_config": self.model_config or {},
            "metrics": self.metrics or {},
            "final_metrics": self.final_metrics or {},
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "compute_resources": self.compute_resources or {},
            "cost_estimate": self.cost_estimate,
            "parent_experiment_id": (
                str(self.parent_experiment_id) if self.parent_experiment_id else None
            ),
            "data_sources": self.data_sources or [],
            "code_version": self.code_version,
            "tags": self.tags or [],
            "metadata": self.metadata or {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
