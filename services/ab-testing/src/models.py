"""
Data models for A/B Testing Service
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class SafetyThresholds(BaseModel):
    """Healthcare safety thresholds that must be maintained"""

    crisis_detection_rate: float = Field(
        default=0.99,
        ge=0.99,
        description="Minimum crisis detection rate (must be >= 99%)",
    )
    empathy_score: float = Field(
        default=0.65, ge=0.0, le=1.0, description="Minimum empathy score"
    )
    accuracy: float = Field(
        default=0.90, ge=0.0, le=1.0, description="Minimum model accuracy"
    )
    response_time_95th: float = Field(
        default=0.5, gt=0, description="95th percentile response time in seconds"
    )
    harmful_response_rate: float = Field(
        default=0.001,
        ge=0.0,
        le=0.01,
        description="Maximum allowed harmful response rate",
    )


class ExperimentConfig(BaseModel):
    """Configuration for creating a new experiment"""

    name: str = Field(..., description="Experiment name")
    description: str = Field(..., description="Detailed description")
    model_a: str = Field(..., description="Control model identifier")
    model_b: str = Field(..., description="Treatment model identifier")
    traffic_split: int = Field(
        default=50, ge=1, le=99, description="Percentage of traffic to route to model A"
    )
    safety_thresholds: SafetyThresholds = Field(
        default_factory=SafetyThresholds, description="Safety thresholds for healthcare"
    )
    min_sample_size: int = Field(
        default=1000, ge=100, description="Minimum samples needed for analysis"
    )
    max_duration_hours: int = Field(
        default=168, ge=1, description="Maximum experiment duration in hours"  # 7 days
    )
    created_by: str = Field(..., description="User who created the experiment")
    target_metrics: List[str] = Field(
        default=["accuracy", "empathy_score", "response_time"],
        description="Metrics to optimize for",
    )


class Experiment(BaseModel):
    """A/B testing experiment"""

    id: str
    name: str
    description: str
    model_a: str
    model_b: str
    traffic_split: int
    safety_thresholds: SafetyThresholds
    status: ExperimentStatus
    created_at: datetime
    created_by: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    failure_reason: Optional[str] = None
    target_metrics: List[str] = ["accuracy", "empathy_score", "response_time"]
    min_sample_size: int = 1000
    max_duration_hours: int = 168

    @validator("traffic_split")
    def validate_traffic_split(cls, v):
        if not 1 <= v <= 99:
            raise ValueError("Traffic split must be between 1 and 99")
        return v

    @property
    def duration_hours(self) -> Optional[float]:
        """Get experiment duration in hours"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 3600
        elif self.start_time:
            return (datetime.utcnow() - self.start_time).total_seconds() / 3600
        return None

    @property
    def is_active(self) -> bool:
        """Check if experiment is currently active"""
        return self.status == ExperimentStatus.RUNNING


class RoutingDecision(BaseModel):
    """Result of routing decision for a user"""

    model: str = Field(..., description="Model identifier to use")
    experiment_id: Optional[str] = Field(None, description="Active experiment ID")
    variant: Optional[str] = Field(None, description="control or treatment")
    reason: str = Field(..., description="Reason for routing decision")


class MetricSnapshot(BaseModel):
    """Snapshot of metrics at a point in time"""

    timestamp: datetime
    model: str
    accuracy: Optional[float] = None
    empathy_score: Optional[float] = None
    response_time_p50: Optional[float] = None
    response_time_p95: Optional[float] = None
    response_time_p99: Optional[float] = None
    crisis_detection_rate: Optional[float] = None
    error_rate: Optional[float] = None
    sample_count: int = 0


class ExperimentMetrics(BaseModel):
    """Aggregated metrics for an experiment"""

    experiment_id: str
    model_a_metrics: List[MetricSnapshot] = []
    model_b_metrics: List[MetricSnapshot] = []
    total_requests_a: int = 0
    total_requests_b: int = 0

    def get_latest_metrics(self, model: str) -> Optional[MetricSnapshot]:
        """Get most recent metrics for a model"""
        metrics = self.model_a_metrics if model == "a" else self.model_b_metrics
        return metrics[-1] if metrics else None


class SafetyViolation(BaseModel):
    """Record of a safety threshold violation"""

    timestamp: datetime
    experiment_id: str
    metric: str
    threshold: float
    actual_value: float
    model: str
    severity: str = "critical"
    action_taken: str = "emergency_stop"


class ExperimentResult(BaseModel):
    """Final results of an A/B test"""

    experiment_id: str
    winner: Optional[str] = None  # model_a, model_b, or None (inconclusive)
    confidence_level: float = 0.95
    metrics_comparison: Dict[str, Dict] = {}
    safety_violations: List[SafetyViolation] = []
    recommendation: str
    statistical_summary: Dict = {}

    @property
    def is_conclusive(self) -> bool:
        """Check if results are statistically conclusive"""
        return self.winner is not None
