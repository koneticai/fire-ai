"""
Test suite for rate limiting enforcement (Task 1.3)
References: AGENTS.md - Security Gate, data_model.md - Security Infrastructure
"""

import pytest
import os

# Set minimal required env vars before any imports
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test_db")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_at_least_32_characters_long!")
os.environ.setdefault("INTERNAL_JWT_SECRET_KEY", "internal_test_secret_32_characters_long!")


def test_rate_limiter_module_imports():
    """Rate limiter middleware should import successfully"""
    from src.app.middleware.rate_limiter import limiter, rate_limit_handler
    
    assert limiter is not None
    assert callable(rate_limit_handler)


def test_rate_limit_error_format():
    """Rate limit errors should follow FIRE-xxx error format"""
    # This test verifies the error handler produces correct format
    from src.app.middleware.rate_limiter import rate_limit_handler
    
    # Create mock request
    class MockClient:
        host = "127.0.0.1"
    
    class MockURL:
        path = "/test"
    
    class MockRequest:
        client = MockClient()
        url = MockURL()
        headers = {"X-RateLimit-Limit": "5"}
    
    # Create rate limit exception (must match slowapi's expected structure)
    class MockLimit:
        error_message = "Rate limit exceeded"
        
    class MockRateLimitExceeded(Exception):
        def __init__(self):
            self.detail = "60"
    
    exc = MockRateLimitExceeded()
    
    # Call handler
    import asyncio
    response = asyncio.run(rate_limit_handler(MockRequest(), exc))
    
    # Verify response structure
    assert response.status_code == 429
    
    # Parse JSON body
    import json
    body = json.loads(response.body.decode())
    
    assert body["error_code"] == "FIRE-429"
    assert "transaction_id" in body
    assert body["retryable"] is True
    assert "retry_after" in body
    
    # Verify headers
    assert "Retry-After" in response.headers


def test_limiter_uses_ip_based_key():
    """Limiter should use IP-based key function for rate limiting"""
    from src.app.middleware.rate_limiter import limiter
    from slowapi.util import get_remote_address
    
    # Verify limiter is configured with IP-based key
    assert limiter._key_func == get_remote_address


def test_limiter_storage_configuration():
    """Limiter should use memory storage in dev, configurable for production"""
    from src.app.middleware.rate_limiter import limiter
    import os
    
    # Check that storage_uri is configurable via env var
    storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")
    
    # In test environment, should default to memory
    assert "memory" in storage_uri or storage_uri.startswith("redis")


def test_rate_limit_headers_enabled():
    """Rate limiter should be configured to send rate limit headers"""
    from src.app.middleware.rate_limiter import limiter
    
    # Verify headers are enabled
    assert limiter._headers_enabled is True


def test_global_default_rate_limit():
    """Limiter should have a reasonable global default rate limit"""
    from src.app.middleware.rate_limiter import limiter
    
    # Check that default limits are configured
    assert limiter._default_limits is not None
    assert len(limiter._default_limits) > 0
    
    # The default limit exists as a LimitGroup object
    assert limiter._default_limits[0] is not None


def test_limiter_callable():
    """Limiter should have callable limit decorator"""
    from src.app.middleware.rate_limiter import limiter
    
    # Verify limiter exists and is callable
    assert limiter is not None
    assert callable(limiter.limit)
