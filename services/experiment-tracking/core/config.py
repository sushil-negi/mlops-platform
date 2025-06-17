"""
Configuration management for Experiment Tracking service
"""

import os
from typing import Optional

from pydantic import BaseModel, Field

# Type ignore for environments without pydantic-settings package
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
except ImportError:
    # Fallback implementation for CI/environments without pydantic-settings
    BaseSettings = BaseModel
    SettingsConfigDict = dict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application settings
    app_name: str = "experiment-tracking"
    environment: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8003
    log_level: str = "INFO"

    # Database settings
    database_url: str = Field(
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://mlops:password@localhost:5432/experiment_tracking",
        ),
        description="Database connection URL - set via DATABASE_URL env var",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 0

    # Redis settings (optional for caching)
    redis_url: Optional[str] = "redis://localhost:6379"
    redis_ttl: int = 3600  # 1 hour default
    redis_enabled: bool = True

    # Storage settings (MinIO/S3)
    storage_backend: str = "minio"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = Field(
        default=os.getenv("MINIO_ACCESS_KEY", ""),
        description="MinIO access key - must be set via MINIO_ACCESS_KEY env var",
    )
    minio_secret_key: str = Field(
        default=os.getenv("MINIO_SECRET_KEY", ""),
        description="MinIO secret key - must be set via MINIO_SECRET_KEY env var",
    )
    minio_secure: bool = False

    # Storage buckets
    storage_bucket_experiments: str = "experiments"
    storage_bucket_artifacts: str = "artifacts"
    storage_bucket_visualizations: str = "visualizations"

    # MLOps service integration
    registry_service_url: str = "http://model-registry:8000"
    pipeline_orchestrator_url: str = "http://pipeline-orchestrator:8004"
    feature_store_url: str = "http://feature-store:8002"

    # Experiment settings
    max_concurrent_experiments: int = 50
    max_runs_per_experiment: int = 1000
    default_experiment_ttl_days: int = 365

    # Metrics and logging
    max_metrics_per_run: int = 10000
    metric_batch_size: int = 100
    enable_real_time_metrics: bool = True

    # Visualization settings
    enable_real_time_plots: bool = True
    plot_backend: str = "plotly"  # plotly, matplotlib
    max_concurrent_visualizations: int = 50

    # Security settings
    secret_key: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", "dev-secret-key"),
        env="SECRET_KEY",
    )
    access_token_expire_minutes: int = 30
    api_key_header: str = "X-API-Key"

    # Hyperparameter optimization
    enable_hpo: bool = True
    max_hpo_trials: int = 1000
    hpo_backend: str = "optuna"  # optuna, hyperopt

    # Resource limits
    max_artifact_size_mb: int = 1000  # 1GB
    max_log_size_mb: int = 100  # 100MB

    # Integration timeouts
    service_timeout_seconds: int = 30
    registry_service_timeout: int = 10
    pipeline_orchestrator_timeout: int = 30
    feature_store_timeout: int = 5

    # Monitoring and observability
    enable_metrics: bool = True
    enable_tracing: bool = True
    metrics_port: int = 9003

    # Healthcare-specific settings
    enable_healthcare_validation: bool = True
    required_healthcare_metrics: list = [
        "accuracy",
        "crisis_detection_rate",
        "response_quality",
    ]
    min_crisis_detection_rate: float = 0.99
    min_response_quality_score: float = 0.8

    model_config = SettingsConfigDict(case_sensitive=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings (useful for testing)"""
    global _settings
    _settings = Settings()
    return _settings


# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment settings"""

    environment: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"


class ProductionSettings(Settings):
    """Production environment settings"""

    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"

    # Production security
    minio_secure: bool = True
    redis_enabled: bool = True

    # Production performance
    database_pool_size: int = 50
    max_concurrent_experiments: int = 200
    max_concurrent_visualizations: int = 100


class TestingSettings(Settings):
    """Testing environment settings"""

    environment: str = "testing"
    debug: bool = True
    log_level: str = "DEBUG"

    # Use in-memory databases for testing
    database_url: str = "sqlite:///:memory:"
    redis_enabled: bool = False


def get_environment_settings() -> Settings:
    """Get environment-specific settings"""
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
