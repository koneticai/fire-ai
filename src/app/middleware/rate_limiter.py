"""
Rate limiting middleware per OWASP recommendations.
References: data_model.md - Security Infrastructure, AGENTS.md - Security Gate
"""

import os
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import uuid

logger = logging.getLogger(__name__)

# Initialize limiter with IP-based key
storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Global default
    storage_uri=storage_uri,
    headers_enabled=True
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom rate limit exceeded handler with structured FIRE error response.
    Aligns with: AGENTS.md - Security Gate, data_model.md - Error Standards
    """
    logger.warning(
        f"Rate limit exceeded: {request.client.host if request.client else 'unknown'} -> {request.url.path}"
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "transaction_id": str(uuid.uuid4()),
            "error_code": "FIRE-429",
            "message": "Rate limit exceeded. Please try again later.",
            "retryable": True,
            "retry_after": exc.detail if hasattr(exc, 'detail') else "60"
        },
        headers={
            "Retry-After": str(exc.detail) if hasattr(exc, 'detail') else "60",
            "X-RateLimit-Limit": request.headers.get("X-RateLimit-Limit", "unknown"),
            "X-RateLimit-Remaining": "0"
        }
    )
