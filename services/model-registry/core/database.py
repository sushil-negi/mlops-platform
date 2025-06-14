"""
Database configuration and connection management
"""

import logging
from typing import AsyncGenerator

import databases
import sqlalchemy
from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Database setup
database = databases.Database(settings.DATABASE_URL)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Create engine
engine = sqlalchemy.create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_database() -> databases.Database:
    """Get database connection"""
    return database


async def get_db_session() -> AsyncGenerator:
    """Get database session for dependency injection"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


async def init_db():
    """Initialize database tables"""
    try:
        # Import all models to register them with SQLAlchemy
        pass

        # Create tables
        metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def check_db_connection():
    """Check database connection health"""
    try:
        await database.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
