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
    
    Note: slowapi's RateLimitExceeded doesn't expose retry_after or limit details,
    so we use sensible defaults. For production, consider implementing a rate limit
    registry to map endpoints to their configured limits.
    """
    logger.warning(
        f"Rate limit exceeded: {request.client.host if request.client else 'unknown'} -> {request.url.path}"
    )
    
    # Default values (slowapi doesn't expose limit details in exception)
    retry_after = 60  # Conservative default
    rate_limit = "1000"  # Global default from limiter configuration
    
    # Try to determine endpoint-specific limits from common patterns
    if "/auth/login" in request.url.path:
        retry_after = 60  # 5/minute limit
        rate_limit = "5"
    elif "/evidence" in request.url.path:
        retry_after = 3600  # 100/hour limit
        rate_limit = "100"
    elif "/reports" in request.url.path:
        retry_after = 3600  # 10/hour limit
        rate_limit = "10"
    
    return JSONResponse(
        status_code=429,
        content={
            "transaction_id": str(uuid.uuid4()),
            "error_code": "FIRE-429",
            "message": "Rate limit exceeded. Please try again later.",
            "retryable": True,
            "retry_after": str(retry_after)
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": rate_limit,
            "X-RateLimit-Remaining": "0"
        }
    )
