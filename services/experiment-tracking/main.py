"""
Experiment Tracking 2.0 - Main application entry point
"""

import logging
import time

import uvicorn
from api.routes import experiments, health, projects, runs, visualizations
from core.config import get_settings
from core.logging import setup_logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="Experiment Tracking 2.0",
    description="Comprehensive ML experiment management platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_server_error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", "unknown"),
            }
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(
    experiments.router, prefix="/api/v1/experiments", tags=["experiments"]
)
app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
app.include_router(
    visualizations.router, prefix="/api/v1/visualizations", tags=["visualizations"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "experiment-tracking",
        "version": "2.0.0",
        "description": "Comprehensive ML experiment management platform",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


# Service discovery endpoint
@app.get("/info")
async def service_info():
    """Service information for discovery"""
    return {
        "name": "experiment-tracking",
        "version": "2.0.0",
        "description": "ML experiment tracking and management",
        "capabilities": [
            "experiment_management",
            "run_tracking",
            "metric_logging",
            "artifact_storage",
            "visualization",
            "model_comparison",
            "hyperparameter_optimization",
        ],
        "integrations": ["model-registry", "pipeline-orchestrator", "feature-store"],
        "endpoints": {
            "health": "/health",
            "projects": "/api/v1/projects",
            "experiments": "/api/v1/experiments",
            "runs": "/api/v1/runs",
            "visualizations": "/api/v1/visualizations",
        },
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("Starting Experiment Tracking 2.0 service")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize database connections, caches, etc.
    # TODO: Add actual initialization code

    logger.info("Experiment Tracking service started successfully")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Shutting down Experiment Tracking service")

    # Cleanup resources
    # TODO: Add cleanup code

    logger.info("Experiment Tracking service stopped")


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
