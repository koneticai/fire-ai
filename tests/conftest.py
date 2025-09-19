"""
Pytest configuration and fixtures for FireMode Compliance Platform tests.

This module provides common test fixtures and configuration for the test suite.
"""

import pytest
import asyncio
import os
from typing import Generator

# Set test environment variables
os.environ["INTERNAL_JWT_SECRET_KEY"] = "test_secret_key_for_internal_jwt_testing"
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
    return "test_user_12345"


@pytest.fixture
def test_token_id() -> str:
    """Provide a test token ID for tests."""
    return "test_token_abcdef123456"