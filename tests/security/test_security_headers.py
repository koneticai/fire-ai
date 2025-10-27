"""
Test suite for security headers middleware (Task 1.4)
References: AGENTS.md - Security Gate (CSP/CORS/CSRF)
            data_model.md - Security Infrastructure
"""

import pytest
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Set minimal required env vars before any imports
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test_db")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_at_least_32_characters_long!")
os.environ.setdefault("INTERNAL_JWT_SECRET_KEY", "internal_test_secret_32_characters_long!")


def test_security_headers_middleware_imports():
    """Security headers middleware should import successfully"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    
    assert SecurityHeadersMiddleware is not None


def test_security_headers_middleware_callable():
    """Middleware should be a valid BaseHTTPMiddleware subclass"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from starlette.middleware.base import BaseHTTPMiddleware
    
    assert issubclass(SecurityHeadersMiddleware, BaseHTTPMiddleware)


def test_security_headers_applied():
    """Test that all security headers are applied to responses"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI, Response
    from fastapi.testclient import TestClient
    
    # Create minimal app
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Check all required headers
    assert "Content-Security-Policy" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Referrer-Policy" in response.headers
    assert "Permissions-Policy" in response.headers


def test_csp_header_value():
    """CSP header should have correct directives"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    csp = response.headers["Content-Security-Policy"]
    
    # Check critical directives
    assert "default-src 'self'" in csp
    assert "script-src" in csp
    assert "img-src" in csp
    assert "connect-src" in csp


def test_frame_options_deny():
    """X-Frame-Options should be DENY to prevent clickjacking"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    assert response.headers["X-Frame-Options"] == "DENY"


def test_content_type_options_nosniff():
    """X-Content-Type-Options should be nosniff"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_xss_protection_enabled():
    """X-XSS-Protection should be enabled with blocking mode"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    assert response.headers["X-XSS-Protection"] == "1; mode=block"


def test_referrer_policy_set():
    """Referrer-Policy should limit information leakage"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_permissions_policy_set():
    """Permissions-Policy should restrict browser features"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    permissions = response.headers["Permissions-Policy"]
    
    # Check that dangerous features are disabled
    assert "geolocation=()" in permissions
    assert "microphone=()" in permissions
    assert "camera=()" in permissions


def test_headers_on_error_responses():
    """Security headers should be present even on error responses"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/error")
    def error_endpoint():
        raise HTTPException(status_code=404, detail="Not found")
    
    client = TestClient(app)
    response = client.get("/error")
    assert response.status_code == 404
    assert "X-Frame-Options" in response.headers
    assert "Content-Security-Policy" in response.headers
    assert "X-Content-Type-Options" in response.headers


def test_hsts_not_in_dev_environment():
    """HSTS should not be enabled in development environment"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    # Make sure we're not in production mode
    original_env = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "development"
    
    try:
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        # HSTS should NOT be present in dev
        assert "Strict-Transport-Security" not in response.headers
    finally:
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)


def test_hsts_in_production_with_https():
    """HSTS should be enabled when in production with HTTPS"""
    from src.app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    # Set production environment
    original_env = os.environ.get("ENVIRONMENT")
    original_https = os.environ.get("HTTPS_ENABLED")
    
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["HTTPS_ENABLED"] = "true"
        
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        # HSTS should be present in production with HTTPS
        assert "Strict-Transport-Security" in response.headers
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
        
    finally:
        # Restore original environment
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)
            
        if original_https:
            os.environ["HTTPS_ENABLED"] = original_https
        else:
            os.environ.pop("HTTPS_ENABLED", None)
