"""
Database core functionality for async SQLAlchemy
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import func

# Database URL from environment - convert to async
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Convert PostgreSQL URL to async version and handle SSL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Remove sslmode parameter if present (asyncpg handles SSL differently)
if "?sslmode=" in DATABASE_URL or "&sslmode=" in DATABASE_URL:
    import re
    DATABASE_URL = re.sub(r'[?&]sslmode=\w+', '', DATABASE_URL)

# Create async SQLAlchemy engine with production-grade pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    connect_args={"ssl": "require"} if "neon" in DATABASE_URL or ".aws" in DATABASE_URL else {}
)

# Create async SessionLocal class
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create Base class for models
Base = declarative_base()

async def get_db():
    """Async dependency to get database session"""
    async with AsyncSessionLocal() as session:
        yield session