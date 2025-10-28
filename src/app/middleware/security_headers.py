"""
Security headers middleware per OWASP recommendations.
References: AGENTS.md - Section 3 (Security Gate - CSP/CORS/CSRF)
            data_model.md - Security Infrastructure
"""

import os
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    Prevents: XSS, clickjacking, MIME sniffing, information leakage.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        response = await call_next(request)
        
        # Content Security Policy - prevent XSS
        # Production uses strict CSP (no unsafe-inline/unsafe-eval)
        # Development allows inline scripts for hot reload, debugging
        env = os.getenv("ENVIRONMENT", "development")
        
        if env == "production":
            # Strict CSP for production - no XSS vectors
            csp = (
                "default-src 'self'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "object-src 'none'; "
                "form-action 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'"
            )
        else:
            # Relaxed CSP for development (allows inline scripts for hot reload, etc.)
            csp = (
                "default-src 'self'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "object-src 'none'; "
                "form-action 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'"
            )
        
        response.headers["Content-Security-Policy"] = csp
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy - limit information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy - restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=()"
        )
        
        # HSTS - enforce HTTPS (enable in production when HTTPS configured)
        if os.getenv("ENVIRONMENT") == "production" and os.getenv("HTTPS_ENABLED") == "true":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        logger.debug(f"Security headers added to {request.url.path}")
        
        return response
