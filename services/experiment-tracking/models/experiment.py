"""
Experiment data models for Experiment Tracking service
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ExperimentStatus(str, Enum):
    """Experiment status enumeration"""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ExperimentType(str, Enum):
    """Experiment type enumeration"""

    TRAINING = "training"
    HYPERPARAMETER_TUNING = "hyperparameter_tuning"
    MODEL_COMPARISON = "model_comparison"
    FEATURE_ENGINEERING = "feature_engineering"
    DATA_ANALYSIS = "data_analysis"
    BASELINE = "baseline"
    PRODUCTION_TEST = "production_test"


# SQLAlchemy ORM Models


class Experiment(Base):
    """Experiment ORM model"""

    __tablename__ = "experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    hypothesis = Column(Text)

    # Experiment configuration
    experiment_type = Column(
        String(50), nullable=False, default=ExperimentType.TRAINING
    )
    status = Column(String(20), nullable=False, default=ExperimentStatus.CREATED)

    # Metadata
    tags = Column(JSON, default=list)
    meta_data = Column(JSON, default=dict)
    parameters = Column(JSON, default=dict)

    # Configuration
    objectives = Column(JSON, default=dict)
    success_criteria = Column(JSON, default=dict)
    environment = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Results
    best_metric_value = Column(Float, nullable=True)
    best_metric_name = Column(String(100), nullable=True)
    final_status = Column(String(100), nullable=True)

    # MLOps integration
    registry_model_id = Column(String(255), nullable=True)
    pipeline_run_id = Column(String(255), nullable=True)
    feature_store_snapshot = Column(JSON, default=dict)

    # Relationships
    project = relationship("Project", back_populates="experiments")
    runs = relationship(
        "ExperimentRun", back_populates="experiment", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Experiment(id={self.id}, name='{self.name}', status='{self.status}')>"


# Pydantic Models for API


class ExperimentBase(BaseModel):
    """Base experiment model"""

    project_id: uuid.UUID = Field(..., description="Project ID")
    name: str = Field(..., min_length=1, max_length=255, description="Experiment name")
    description: Optional[str] = Field(None, description="Experiment description")
    hypothesis: Optional[str] = Field(None, description="Experiment hypothesis")

    experiment_type: ExperimentType = Field(
        default=ExperimentType.TRAINING, description="Experiment type"
    )
    tags: List[str] = Field(default_factory=list, description="Experiment tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Experiment parameters"
    )

    # Configuration
    objectives: Dict[str, Any] = Field(
        default_factory=dict, description="Experiment objectives"
    )
    success_criteria: Dict[str, Any] = Field(
        default_factory=dict, description="Success criteria"
    )
    environment: Dict[str, Any] = Field(
        default_factory=dict, description="Environment info"
    )


class ExperimentCreate(ExperimentBase):
    """Experiment creation model"""

    pass


class ExperimentUpdate(BaseModel):
    """Experiment update model"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    hypothesis: Optional[str] = None
    experiment_type: Optional[ExperimentType] = None
    status: Optional[ExperimentStatus] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    objectives: Optional[Dict[str, Any]] = None
    success_criteria: Optional[Dict[str, Any]] = None
    environment: Optional[Dict[str, Any]] = None


class ExperimentResponse(ExperimentBase):
    """Experiment response model"""

    id: uuid.UUID
    status: ExperimentStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    best_metric_value: Optional[float] = None
    best_metric_name: Optional[str] = None
    final_status: Optional[str] = None

    # Statistics
    total_runs: int = Field(default=0, description="Total number of runs")
    successful_runs: int = Field(default=0, description="Number of successful runs")
    failed_runs: int = Field(default=0, description="Number of failed runs")

    # MLOps integration
    registry_model_id: Optional[str] = None
    pipeline_run_id: Optional[str] = None

    class Config:
        from_attributes = True


class ExperimentSummary(BaseModel):
    """Experiment summary model for listings"""

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str]
    experiment_type: ExperimentType
    status: ExperimentStatus
    tags: List[str]
    created_at: datetime

    # Quick stats
    run_count: int = Field(default=0)
    best_metric_value: Optional[float] = None
    best_metric_name: Optional[str] = None

    class Config:
        from_attributes = True


class ExperimentListResponse(BaseModel):
    """Experiment list response model"""

    experiments: List[ExperimentSummary]
    total: int
    page: int
    size: int
    total_pages: int


class ExperimentComparison(BaseModel):
    """Experiment comparison model"""

    experiments: List[uuid.UUID]
    comparison_metrics: List[str]

    # Results
    best_experiment: Optional[uuid.UUID] = None
    metric_comparison: Dict[str, Dict[uuid.UUID, float]] = Field(default_factory=dict)
    statistical_significance: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Visualization
    visualization_url: Optional[str] = None
    comparison_chart: Optional[Dict[str, Any]] = None


class ExperimentMetrics(BaseModel):
    """Experiment metrics summary"""

    experiment_id: uuid.UUID

    # Performance metrics
    best_run_metrics: Dict[str, float] = Field(default_factory=dict)
    average_metrics: Dict[str, float] = Field(default_factory=dict)
    metric_trends: Dict[str, List[float]] = Field(default_factory=dict)

    # Run statistics
    total_runs: int
    successful_runs: int
    failed_runs: int
    average_run_duration_minutes: Optional[float]

    # Resource usage
    total_compute_hours: Optional[float]
    average_memory_usage_gb: Optional[float]
    total_storage_mb: Optional[float]


# Healthcare-specific experiment models


class HealthcareExperimentConfig(BaseModel):
    """Healthcare-specific experiment configuration"""

    validate_crisis_detection: bool = True
    min_crisis_detection_rate: float = 0.99
    validate_response_quality: bool = True
    min_response_quality_score: float = 0.8
    require_medical_disclaimers: bool = True

    # Safety checks
    enable_safety_monitoring: bool = True
    max_false_positive_rate: float = 0.05
    max_false_negative_rate: float = 0.01

    # Compliance
    log_all_predictions: bool = True
    enable_audit_trail: bool = True


class HealthcareExperiment(ExperimentBase):
    """Healthcare-specific experiment model"""

    domain: str = Field(default="healthcare", description="Domain type")
    healthcare_config: HealthcareExperimentConfig = Field(
        default_factory=HealthcareExperimentConfig,
        description="Healthcare-specific configuration",
    )

    # Healthcare-specific objectives
    healthcare_objectives: Dict[str, Any] = Field(
        default_factory=lambda: {
            "accuracy": {"target": 0.95, "required": True},
            "crisis_detection_rate": {"target": 0.99, "required": True},
            "response_quality": {"target": 0.8, "required": False},
        },
        description="Healthcare-specific objectives",
    )


# Experiment templates

EXPERIMENT_TEMPLATES = {
    "healthcare_baseline": {
        "name": "Healthcare Baseline Experiment",
        "description": "Baseline healthcare classification model",
        "experiment_type": ExperimentType.BASELINE,
        "tags": ["healthcare", "baseline", "classification"],
        "objectives": {"primary_metric": "accuracy", "target_accuracy": 0.95},
        "success_criteria": {
            "accuracy": ">= 0.95",
            "crisis_detection_rate": ">= 0.99",
            "response_quality_score": ">= 0.8",
        },
        "healthcare_config": {
            "validate_crisis_detection": True,
            "min_crisis_detection_rate": 0.99,
            "require_medical_disclaimers": True,
        },
    },
    "hyperparameter_optimization": {
        "name": "Hyperparameter Optimization",
        "description": "Systematic hyperparameter tuning",
        "experiment_type": ExperimentType.HYPERPARAMETER_TUNING,
        "tags": ["hpo", "optimization"],
        "objectives": {
            "optimization_metric": "accuracy",
            "optimization_direction": "maximize",
        },
        "success_criteria": {"improvement_threshold": 0.01},
    },
    "model_comparison": {
        "name": "Model Comparison",
        "description": "Compare different model architectures",
        "experiment_type": ExperimentType.MODEL_COMPARISON,
        "tags": ["comparison", "evaluation"],
        "objectives": {
            "compare_metrics": ["accuracy", "f1_score", "precision", "recall"],
            "statistical_significance": True,
        },
    },
    "feature_engineering": {
        "name": "Feature Engineering",
        "description": "Feature selection and engineering experiments",
        "experiment_type": ExperimentType.FEATURE_ENGINEERING,
        "tags": ["features", "engineering"],
        "objectives": {"feature_importance": True, "feature_selection": True},
    },
}
