"""
Project data models for Experiment Tracking service
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ProjectStatus(str, Enum):
    """Project status enumeration"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class ProjectPriority(str, Enum):
    """Project priority enumeration"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# SQLAlchemy ORM Models


class Project(Base):
    """Project ORM model"""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    team = Column(String(100), nullable=False)
    owner = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default=ProjectStatus.ACTIVE)
    priority = Column(String(20), nullable=False, default=ProjectPriority.MEDIUM)

    # Metadata
    tags = Column(JSON, default=list)
    meta_data = Column(JSON, default=dict)
    objectives = Column(Text)
    success_criteria = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at = Column(DateTime, nullable=True)

    # Settings
    auto_cleanup_days = Column(Integer, default=365)
    enable_notifications = Column(Boolean, default=True)

    # Relationships
    experiments = relationship(
        "Experiment", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', team='{self.team}')>"


# Pydantic Models for API


class ProjectBase(BaseModel):
    """Base project model"""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    team: str = Field(..., min_length=1, max_length=100, description="Team name")
    owner: str = Field(..., min_length=1, max_length=100, description="Project owner")
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE, description="Project status"
    )
    priority: ProjectPriority = Field(
        default=ProjectPriority.MEDIUM, description="Project priority"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Project tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    objectives: Optional[str] = Field(None, description="Project objectives")
    success_criteria: Dict[str, Any] = Field(
        default_factory=dict, description="Success criteria"
    )

    # Settings
    auto_cleanup_days: int = Field(
        default=365, ge=1, description="Auto cleanup period in days"
    )
    enable_notifications: bool = Field(default=True, description="Enable notifications")


class ProjectCreate(ProjectBase):
    """Project creation model"""

    pass


class ProjectUpdate(BaseModel):
    """Project update model"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    team: Optional[str] = Field(None, min_length=1, max_length=100)
    owner: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[ProjectStatus] = None
    priority: Optional[ProjectPriority] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    objectives: Optional[str] = None
    success_criteria: Optional[Dict[str, Any]] = None
    auto_cleanup_days: Optional[int] = Field(None, ge=1)
    enable_notifications: Optional[bool] = None


class ProjectResponse(ProjectBase):
    """Project response model"""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    # Statistics
    total_experiments: int = Field(default=0, description="Total number of experiments")
    active_experiments: int = Field(
        default=0, description="Number of active experiments"
    )
    total_runs: int = Field(default=0, description="Total number of runs")

    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    """Project summary model for listings"""

    id: uuid.UUID
    name: str
    description: Optional[str]
    team: str
    owner: str
    status: ProjectStatus
    priority: ProjectPriority
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    # Quick stats
    experiment_count: int = Field(default=0)
    recent_activity: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Project list response model"""

    projects: List[ProjectSummary]
    total: int
    page: int
    size: int
    total_pages: int


class ProjectStats(BaseModel):
    """Project statistics model"""

    project_id: uuid.UUID

    # Experiment statistics
    total_experiments: int
    active_experiments: int
    completed_experiments: int

    # Run statistics
    total_runs: int
    successful_runs: int
    failed_runs: int
    running_runs: int

    # Time statistics
    avg_experiment_duration_hours: Optional[float]
    total_compute_hours: Optional[float]

    # Resource usage
    total_artifacts_mb: Optional[float]
    total_metrics_logged: int

    # Team statistics
    unique_contributors: int
    experiments_per_contributor: Dict[str, int]

    # Recent activity
    last_experiment_date: Optional[datetime]
    experiments_last_7_days: int
    experiments_last_30_days: int


class ProjectHealthCheck(BaseModel):
    """Project health check model"""

    project_id: uuid.UUID
    health_status: str  # healthy, warning, critical

    # Health indicators
    recent_activity: bool
    failing_experiments: int
    resource_utilization: float

    # Recommendations
    recommendations: List[str]
    warnings: List[str]

    # Last check
    checked_at: datetime


# Healthcare-specific project models


class HealthcareProjectConfig(BaseModel):
    """Healthcare-specific project configuration"""

    enable_crisis_detection_validation: bool = True
    min_accuracy_threshold: float = 0.95
    min_crisis_detection_rate: float = 0.99
    required_medical_disclaimers: bool = True
    enable_response_quality_scoring: bool = True

    # Compliance settings
    hipaa_compliance_enabled: bool = True
    audit_trail_retention_days: int = 2555  # 7 years

    # Safety settings
    auto_flag_low_performance: bool = True
    require_human_review: bool = True


class HealthcareProject(ProjectBase):
    """Healthcare-specific project model"""

    domain: str = Field(default="healthcare", description="Domain type")
    compliance_requirements: List[str] = Field(
        default=["HIPAA", "Medical_Disclaimers"], description="Compliance requirements"
    )
    healthcare_config: HealthcareProjectConfig = Field(
        default_factory=HealthcareProjectConfig,
        description="Healthcare-specific configuration",
    )


# Project templates

PROJECT_TEMPLATES = {
    "healthcare_classification": {
        "name": "Healthcare Classification Project",
        "description": "Template for healthcare AI classification projects",
        "tags": ["healthcare", "classification", "ai"],
        "objectives": "Develop accurate healthcare classification models with safety compliance",
        "success_criteria": {
            "min_accuracy": 0.95,
            "min_crisis_detection_rate": 0.99,
            "response_quality_score": 0.8,
        },
        "healthcare_config": {
            "enable_crisis_detection_validation": True,
            "min_accuracy_threshold": 0.95,
            "require_human_review": True,
        },
    },
    "general_ml": {
        "name": "General ML Project",
        "description": "Template for general machine learning projects",
        "tags": ["ml", "general"],
        "objectives": "Develop and deploy machine learning models",
        "success_criteria": {"target_metric": "accuracy", "target_value": 0.9},
    },
    "research": {
        "name": "Research Project",
        "description": "Template for research and experimentation",
        "tags": ["research", "experimental"],
        "objectives": "Explore new approaches and methodologies",
        "success_criteria": {"publication_ready": True, "reproducible_results": True},
    },
}
