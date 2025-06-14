"""
Configuration settings for Model Registry service
"""

import os
from functools import lru_cache
from typing import List

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application settings
    APP_NAME: str = "MLOps Model Registry"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # CORS settings
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")

    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")

    # Redis settings
    REDIS_URL: str = Field(..., env="REDIS_URL")
    REDIS_TTL: int = Field(default=3600, env="REDIS_TTL")  # 1 hour

    # Storage settings (MinIO/S3)
    STORAGE_ENDPOINT: str = Field(..., env="MINIO_ENDPOINT")
    STORAGE_ACCESS_KEY: str = Field(..., env="MINIO_ACCESS_KEY")
    STORAGE_SECRET_KEY: str = Field(..., env="MINIO_SECRET_KEY")
    STORAGE_SECURE: bool = Field(default=False, env="MINIO_SECURE")
    STORAGE_BUCKET_MODELS: str = Field(default="models", env="STORAGE_BUCKET_MODELS")
    STORAGE_BUCKET_ARTIFACTS: str = Field(
        default="artifacts", env="STORAGE_BUCKET_ARTIFACTS"
    )

    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production", env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Model settings
    MAX_MODEL_SIZE_MB: int = Field(default=500, env="MAX_MODEL_SIZE_MB")
    SUPPORTED_FRAMEWORKS: List[str] = Field(
        default=["tensorflow", "pytorch", "sklearn", "xgboost", "lightgbm", "onnx"],
        env="SUPPORTED_FRAMEWORKS",
    )

    # Metrics and monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")

    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @validator("SUPPORTED_FRAMEWORKS", pre=True)
    def parse_supported_frameworks(cls, v):
        """Parse SUPPORTED_FRAMEWORKS from string or list"""
        if isinstance(v, str):
            return [fw.strip() for fw in v.split(",")]
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


class DevelopmentSettings(Settings):
    """Development environment settings"""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionSettings(Settings):
    """Production environment settings"""

    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"


class TestingSettings(Settings):
    """Testing environment settings"""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "sqlite:///./test.db"
    REDIS_URL: str = "redis://localhost:6379/15"  # Use different DB for testing


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
