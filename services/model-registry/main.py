"""
Cirruslabs MLOps - Model Registry Service
Main application entry point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import health, metrics, models
from core.config import get_settings
from core.database import database, init_db
from core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Model Registry Service")
    await database.connect()
    await init_db()
    logger.info("Model Registry Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Model Registry Service")
    await database.disconnect()
    logger.info("Model Registry Service stopped")


# Create FastAPI application
app = FastAPI(
    title="MLOps Model Registry",
    description="Centralized model versioning and lifecycle management service",
    version="1.0.0",
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
            }
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
app.include_router(models.router, prefix="/api/v1/models", tags=["Models"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MLOps Model Registry",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
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
