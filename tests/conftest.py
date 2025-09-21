"""
Pytest configuration and fixtures for FireMode Compliance Platform tests.

This module provides common test fixtures and configuration for the test suite.
"""

import pytest
import asyncio
import os
import uuid
from typing import Generator
from unittest.mock import AsyncMock, Mock, patch

# Set test environment variables
os.environ["INTERNAL_JWT_SECRET_KEY"] = "test_secret_key_for_internal_jwt_testing"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_testing_authentication"
os.environ["DATABASE_URL"] = "postgresql://test_user:test_password@localhost:5432/test_firemode"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_user_id() -> str:
    """Provide a test user ID for tests."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def test_token_id() -> str:
    """Provide a test token ID for tests."""
    return "test_token_abcdef123456"


@pytest.fixture
def test_user_data(test_user_id: str) -> dict:
    """Provide test user data for token creation."""
    return {
        "sub": "testuser",
        "user_id": test_user_id,
        "username": "testuser"
    }


@pytest.fixture
def valid_jwt_token(test_user_data: dict) -> str:
    """Create a valid JWT token for testing."""
    from src.app.dependencies import create_access_token
    return create_access_token(test_user_data)


@pytest.fixture
def auth_headers(valid_jwt_token: str) -> dict:
    """Create authentication headers with valid JWT token."""
    return {"Authorization": f"Bearer {valid_jwt_token}"}


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = Mock()
    return mock_session


@pytest.fixture(autouse=True)
def mock_get_current_active_user(test_user_data: dict):
    """Mock authentication dependency for all tests."""
    from src.app.schemas.auth import TokenPayload
    
    token_payload = TokenPayload(
        user_id=uuid.UUID(test_user_data["user_id"]),
        username=test_user_data["username"],
        jti=uuid.uuid4(),
        exp=None
    )
    
    with patch("src.app.dependencies.get_current_active_user", return_value=token_payload):
        yield token_payload


@pytest.fixture(autouse=True)
def mock_database_dependencies():
    """Mock database connection for all tests using FastAPI dependency overrides."""
    from src.app.main import app
    from src.app.database.core import get_db
    
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = Mock()
    
    # Use FastAPI dependency_overrides instead of patch
    async def override_get_db():
        yield mock_session
    
    # Override the dependency properly
    app.dependency_overrides[get_db] = override_get_db
    
    yield mock_session
    
    # Clean up dependency override
    app.dependency_overrides.clear()