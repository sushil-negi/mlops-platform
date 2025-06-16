"""
MLOps Pipeline Orchestrator - Main Service
Advanced workflow engine for ML pipeline orchestration
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import health, monitoring, pipelines, runs
from core.config import get_settings
from core.database import database, init_db
from core.logging import setup_logging
from core.metrics import create_metrics_response
from core.scheduler import PipelineScheduler

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

# Global scheduler instance
scheduler: Optional[PipelineScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global scheduler

    # Startup
    logger.info("Starting Pipeline Orchestrator Service")
    await database.connect()
    await init_db()

    # Initialize scheduler
    scheduler = PipelineScheduler()
    await scheduler.start()
    logger.info("Pipeline scheduler started")

    logger.info("Pipeline Orchestrator Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Pipeline Orchestrator Service")
    if scheduler:
        await scheduler.stop()
        logger.info("Pipeline scheduler stopped")

    await database.disconnect()
    logger.info("Pipeline Orchestrator Service stopped")


# Create FastAPI application
app = FastAPI(
    title="MLOps Pipeline Orchestrator",
    description="Advanced workflow engine for ML pipeline orchestration and execution",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for UI
if os.path.exists("ui/static"):
    app.mount("/static", StaticFiles(directory="ui/static"), name="static")


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTPException",
                "timestamp": str(
                    request.state.start_time
                    if hasattr(request.state, "start_time")
                    else None
                ),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "InternalServerError",
                "timestamp": str(
                    request.state.start_time
                    if hasattr(request.state, "start_time")
                    else None
                ),
            }
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["Pipelines"])
app.include_router(runs.router, prefix="/api/v1/runs", tags=["Pipeline Runs"])


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return create_metrics_response()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MLOps Pipeline Orchestrator",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "features": [
            "DAG-based workflow engine",
            "ML-specific operators",
            "Intelligent scheduling",
            "Event-driven triggers",
            "Real-time monitoring",
        ],
    }


@app.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status"""
    if not scheduler:
        return {"status": "not_initialized"}

    return {
        "status": "running" if scheduler.is_running else "stopped",
        "active_runs": scheduler.get_active_run_count(),
        "queued_tasks": scheduler.get_queued_task_count(),
        "completed_runs_24h": scheduler.get_completed_runs_count(hours=24),
        "resource_usage": scheduler.get_resource_usage(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
    )
