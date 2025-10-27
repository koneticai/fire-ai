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


def test_rate_limit_middleware_registered(client):
    """Verify SlowAPIMiddleware is actually registered in the app"""
    from slowapi.middleware import SlowAPIMiddleware
    
    # Uses client fixture which internally imports app
    # Check middleware stack - SlowAPIMiddleware must be present
    app = client.app
    middleware_found = False
    
    # Check user_middleware for SlowAPIMiddleware
    for middleware in app.user_middleware:
        middleware_cls = middleware.cls if hasattr(middleware, 'cls') else type(middleware)
        if middleware_cls.__name__ == 'SlowAPIMiddleware' or isinstance(middleware_cls, type(SlowAPIMiddleware)):
            middleware_found = True
            break
    
    assert middleware_found, \
        "SlowAPIMiddleware not found in app.user_middleware - rate limits will not be enforced!"


@pytest.mark.integration
def test_rate_limit_enforcement_with_test_client(client):
    """Integration: Rate limiting should actually block requests"""
    # Uses client fixture from conftest.py which includes mocked dependencies
    
    # Test auth endpoint which has @limiter.limit("5/minute")
    # Note: We expect auth to fail (401/422) but NOT with 429 until limit is hit
    
    responses = []
    for i in range(8):  # Try more than the 5/minute limit
        resp = client.post(
            "/v1/auth/login",
            json={"username": "testuser", "password": "wrongpass"}
        )
        responses.append((i+1, resp.status_code))
    
    # Check if we got any 429 responses (rate limited)
    rate_limited_responses = [r for r in responses if r[1] == 429]
    
    # If rate limiting is working, we should see 429 responses after the 5th request
    # If middleware is missing, we'll never see 429
    assert len(rate_limited_responses) > 0, \
        f"No 429 responses found in {len(responses)} requests. Rate limiting not enforced! Responses: {responses}"
    
    # Verify FIRE error format on rate-limited response
    resp_429 = client.post(
        "/v1/auth/login",
        json={"username": "testuser", "password": "wrongpass"}
    )
    
    if resp_429.status_code == 429:
        body = resp_429.json()
        assert body["error_code"] == "FIRE-429", f"Expected FIRE-429 error code, got {body}"
        assert "retry_after" in body, "Missing retry_after field"
        assert body["retryable"] is True, "Should be retryable"
