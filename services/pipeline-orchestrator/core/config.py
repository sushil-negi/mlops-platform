"""
Configuration settings for Pipeline Orchestrator service
"""

import os
from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application settings
    APP_NAME: str = "MLOps Pipeline Orchestrator"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8001, env="PORT")  # Different port from Model Registry
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # CORS settings
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")

    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")

    # Redis settings (for task queue and caching)
    REDIS_URL: str = Field(..., env="REDIS_URL")
    REDIS_TTL: int = Field(default=3600, env="REDIS_TTL")
    REDIS_TASK_QUEUE: str = Field(default="mlops_tasks", env="REDIS_TASK_QUEUE")

    # Storage settings (for pipeline definitions and artifacts)
    STORAGE_ENDPOINT: str = Field(..., env="MINIO_ENDPOINT")
    STORAGE_ACCESS_KEY: str = Field(..., env="MINIO_ACCESS_KEY")
    STORAGE_SECRET_KEY: str = Field(..., env="MINIO_SECRET_KEY")
    STORAGE_SECURE: bool = Field(default=False, env="MINIO_SECURE")
    STORAGE_BUCKET_PIPELINES: str = Field(
        default="pipelines", env="STORAGE_BUCKET_PIPELINES"
    )
    STORAGE_BUCKET_ARTIFACTS: str = Field(
        default="pipeline-artifacts", env="STORAGE_BUCKET_ARTIFACTS"
    )

    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production", env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Scheduler settings
    MAX_CONCURRENT_RUNS: int = Field(default=10, env="MAX_CONCURRENT_RUNS")
    MAX_WORKERS: int = Field(default=5, env="MAX_WORKERS")
    TASK_TIMEOUT_SECONDS: int = Field(
        default=3600, env="TASK_TIMEOUT_SECONDS"
    )  # 1 hour
    HEARTBEAT_INTERVAL_SECONDS: int = Field(
        default=30, env="HEARTBEAT_INTERVAL_SECONDS"
    )

    # Resource limits
    MAX_CPU_CORES: float = Field(default=8.0, env="MAX_CPU_CORES")
    MAX_MEMORY_GB: float = Field(default=16.0, env="MAX_MEMORY_GB")
    MAX_GPU_COUNT: int = Field(default=2, env="MAX_GPU_COUNT")

    # Pipeline settings
    SUPPORTED_OPERATORS: List[str] = Field(
        default=[
            "data_ingestion",
            "data_validation",
            "data_transformation",
            "feature_engineering",
            "model_training",
            "model_validation",
            "model_registration",
            "model_deployment",
            "monitoring_setup",
            "notification",
            "conditional",
            "parallel",
            "loop",
        ],
        env="SUPPORTED_OPERATORS",
    )

    # Default resource requirements for tasks
    DEFAULT_TASK_RESOURCES: Dict[str, Dict] = Field(
        default={
            "data_ingestion": {"cpu": 1.0, "memory_gb": 2.0, "gpu": 0},
            "data_validation": {"cpu": 0.5, "memory_gb": 1.0, "gpu": 0},
            "data_transformation": {"cpu": 2.0, "memory_gb": 4.0, "gpu": 0},
            "feature_engineering": {"cpu": 1.0, "memory_gb": 2.0, "gpu": 0},
            "model_training": {"cpu": 4.0, "memory_gb": 8.0, "gpu": 1},
            "model_validation": {"cpu": 1.0, "memory_gb": 2.0, "gpu": 0},
            "model_registration": {"cpu": 0.5, "memory_gb": 1.0, "gpu": 0},
            "model_deployment": {"cpu": 1.0, "memory_gb": 2.0, "gpu": 0},
            "monitoring_setup": {"cpu": 0.5, "memory_gb": 1.0, "gpu": 0},
        }
    )

    # External service URLs
    MODEL_REGISTRY_URL: str = Field(
        default="http://localhost:8000", env="MODEL_REGISTRY_URL"
    )
    FEATURE_STORE_URL: Optional[str] = Field(default=None, env="FEATURE_STORE_URL")
    NOTIFICATION_WEBHOOK_URL: Optional[str] = Field(
        default=None, env="NOTIFICATION_WEBHOOK_URL"
    )

    # Monitoring and metrics
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9091, env="METRICS_PORT")
    ENABLE_TRACING: bool = Field(default=True, env="ENABLE_TRACING")

    # Pipeline execution settings
    ENABLE_DAG_VALIDATION: bool = Field(default=True, env="ENABLE_DAG_VALIDATION")
    ENABLE_CHECKPOINT_RECOVERY: bool = Field(
        default=True, env="ENABLE_CHECKPOINT_RECOVERY"
    )
    CHECKPOINT_INTERVAL_SECONDS: int = Field(
        default=300, env="CHECKPOINT_INTERVAL_SECONDS"
    )  # 5 minutes

    # Retry and error handling
    DEFAULT_RETRY_COUNT: int = Field(default=3, env="DEFAULT_RETRY_COUNT")
    DEFAULT_RETRY_DELAY_SECONDS: int = Field(
        default=60, env="DEFAULT_RETRY_DELAY_SECONDS"
    )
    ENABLE_CIRCUIT_BREAKER: bool = Field(default=True, env="ENABLE_CIRCUIT_BREAKER")

    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @validator("SUPPORTED_OPERATORS", pre=True)
    def parse_supported_operators(cls, v):
        """Parse SUPPORTED_OPERATORS from string or list"""
        if isinstance(v, str):
            return [op.strip() for op in v.split(",")]
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    @validator("MAX_CONCURRENT_RUNS")
    def validate_max_concurrent_runs(cls, v):
        """Validate max concurrent runs"""
        if v < 1:
            raise ValueError("MAX_CONCURRENT_RUNS must be at least 1")
        return v

    @validator("MAX_WORKERS")
    def validate_max_workers(cls, v):
        """Validate max workers"""
        if v < 1:
            raise ValueError("MAX_WORKERS must be at least 1")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


class DevelopmentSettings(Settings):
    """Development environment settings"""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    MAX_CONCURRENT_RUNS: int = 3
    MAX_WORKERS: int = 2


class ProductionSettings(Settings):
    """Production environment settings"""

    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    MAX_CONCURRENT_RUNS: int = 20
    MAX_WORKERS: int = 10


class TestingSettings(Settings):
    """Testing environment settings"""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "sqlite:///./test_orchestrator.db"
    REDIS_URL: str = "redis://localhost:6379/14"  # Different DB for testing
    MAX_CONCURRENT_RUNS: int = 2
    MAX_WORKERS: int = 1


@lru_cache()
def get_settings() -> Settings:
    """Get application settings based on environment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
