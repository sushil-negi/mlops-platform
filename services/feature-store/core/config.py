"""
Configuration management for Feature Store 2.0
"""

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Feature Store configuration settings"""

    # Service settings
    SERVICE_NAME: str = "feature-store"
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8002, env="PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/feature_store",
        env="DATABASE_URL",
    )
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_POOL_OVERFLOW: int = Field(default=10, env="DATABASE_POOL_OVERFLOW")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_CACHE_TTL: int = Field(default=3600, env="REDIS_CACHE_TTL")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")

    # Storage
    STORAGE_BACKEND: str = Field(default="s3", env="STORAGE_BACKEND")  # s3, local, gcs
    STORAGE_PATH: str = Field(default="/tmp/feature_store", env="STORAGE_PATH")

    # S3/MinIO settings
    S3_ENDPOINT: Optional[str] = Field(
        default="http://localhost:9000", env="S3_ENDPOINT"
    )
    S3_ACCESS_KEY: Optional[str] = Field(default="minioadmin", env="S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = Field(default="minioadmin", env="S3_SECRET_KEY")
    S3_BUCKET: str = Field(default="feature-store", env="S3_BUCKET")
    S3_USE_SSL: bool = Field(default=False, env="S3_USE_SSL")

    # Feature serving
    SERVING_BATCH_SIZE: int = Field(default=1000, env="SERVING_BATCH_SIZE")
    SERVING_CACHE_ENABLED: bool = Field(default=True, env="SERVING_CACHE_ENABLED")
    SERVING_CACHE_TTL: int = Field(default=300, env="SERVING_CACHE_TTL")
    ONLINE_STORE_ENABLED: bool = Field(default=True, env="ONLINE_STORE_ENABLED")

    # Feature computation
    COMPUTE_ENGINE: str = Field(default="duckdb", env="COMPUTE_ENGINE")  # duckdb, spark
    MAX_COMPUTE_THREADS: int = Field(default=4, env="MAX_COMPUTE_THREADS")
    MATERIALIZATION_BATCH_SIZE: int = Field(
        default=10000, env="MATERIALIZATION_BATCH_SIZE"
    )

    # Feature validation
    VALIDATION_ENABLED: bool = Field(default=True, env="VALIDATION_ENABLED")
    VALIDATION_SAMPLE_SIZE: int = Field(default=1000, env="VALIDATION_SAMPLE_SIZE")

    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    ENABLE_TRACING: bool = Field(default=True, env="ENABLE_TRACING")
    METRICS_PORT: int = Field(default=8003, env="METRICS_PORT")

    # Security
    API_KEY_ENABLED: bool = Field(default=False, env="API_KEY_ENABLED")
    API_KEYS: List[str] = Field(default_factory=list, env="API_KEYS")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], env="CORS_ORIGINS"
    )

    # Feature Store specific
    MAX_FEATURE_SETS: int = Field(default=1000, env="MAX_FEATURE_SETS")
    MAX_FEATURES_PER_SET: int = Field(default=1000, env="MAX_FEATURES_PER_SET")
    MAX_POINT_IN_TIME_DAYS: int = Field(default=365, env="MAX_POINT_IN_TIME_DAYS")
    DEFAULT_TTL_DAYS: int = Field(default=30, env="DEFAULT_TTL_DAYS")

    # Time series
    TIME_SERIES_ENABLED: bool = Field(default=True, env="TIME_SERIES_ENABLED")
    TIME_SERIES_RETENTION_DAYS: int = Field(
        default=90, env="TIME_SERIES_RETENTION_DAYS"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
