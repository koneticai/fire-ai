"""
Pytest configuration and fixtures for FireMode Compliance Platform tests.

This module provides common test fixtures and configuration for the test suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncio
import os

# Set test environment
os.environ["TESTING"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-12345678901234567890123456789012"
os.environ["INTERNAL_JWT_SECRET_KEY"] = "test-internal-key-12345678901234567890123456789012"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def async_session():
    """Mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    
    # Mock query results for pagination tests
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = 0
    
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    
    return session

@pytest.fixture
def override_get_current_user():
    """Override authentication for tests."""
    import types
    async def mock_user():
        # Return object with .id attribute to match app expectations
        return types.SimpleNamespace(
            id="test-user",
            user_id="test-user", 
            email="test@example.com"
        )
    return mock_user

@pytest.fixture
def client(override_get_current_user, async_session):
    """Test client with mocked dependencies."""
    from src.app.main import app
    from src.app.dependencies import get_current_active_user
    from src.app.database.core import get_db
    
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    
    # Fix async session dependency override
    async def override_get_db():
        yield async_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    return TestClient(app)

@pytest.fixture
def authenticated_headers():
    """Headers with valid test token."""
    return {"Authorization": "Bearer test-token"}

@pytest.fixture
def auth_headers():
    """Alias for authenticated_headers for compatibility."""
    return {"Authorization": "Bearer test-token"}

@pytest.fixture
def db_session():
    """Alias for async_session for compatibility."""
    session = AsyncMock(spec=AsyncSession)
    
    # Mock query results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = 0
    mock_result.scalar_one_or_none.return_value = None
    
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    
    return session