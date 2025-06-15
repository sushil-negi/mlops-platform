"""
Feature Store 2.0 - Real-time Feature Management Platform
Centralized feature repository with versioning, lineage, and serving
"""

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import feature_sets, features, health, monitoring, serving
from core.config import settings
from core.database import init_db
from core.logging import setup_logging

# Setup logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Feature Store 2.0...")

    # Initialize database with retry logic
    max_retries = 10
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            await init_db()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(
                    f"Failed to initialize database after {max_retries} attempts: {e}"
                )
                raise
            logger.warning(
                f"Database initialization attempt {attempt + 1} failed: {e}. "
                f"Retrying in {retry_delay}s..."
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)  # Cap at 30 seconds

    # Initialize feature storage
    from storage.feature_storage import FeatureStorage

    storage = FeatureStorage()
    await storage.initialize()
    app.state.storage = storage

    # Initialize serving engine
    from core.serving_engine import ServingEngine

    serving_engine = ServingEngine(storage)
    await serving_engine.start()
    app.state.serving_engine = serving_engine

    logger.info("Feature Store 2.0 started successfully")

    yield

    # Cleanup
    logger.info("Shutting down Feature Store 2.0...")
    await serving_engine.stop()
    await storage.close()


# Create FastAPI app
app = FastAPI(
    title="Feature Store 2.0",
    description="Enterprise Feature Management Platform for MLOps",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(features.router, prefix="/api/v1/features", tags=["features"])
app.include_router(
    feature_sets.router, prefix="/api/v1/feature-sets", tags=["feature-sets"]
)
app.include_router(serving.router, prefix="/api/v1/serving", tags=["serving"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Feature Store 2.0",
        "version": "2.0.0",
        "status": "operational",
        "description": "Enterprise Feature Management Platform",
        "documentation": "/docs",
        "health": "/health",
    }


def main():
    """Run the Feature Store service"""
    logger.info(f"Starting Feature Store on {settings.HOST}:{settings.PORT}")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
