"""
Standardized error handling for FireMode Compliance Platform
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import uuid
from typing import Dict, Any

ERROR_REGISTRY = {
    400: ("FIRE-400", "Bad Request: General validation error", False),
    401: ("FIRE-401", "Unauthorized: Invalid or expired JWT", False),
    403: ("FIRE-403", "Forbidden: Insufficient permissions", False),
    404: ("FIRE-404", "Not Found: Resource does not exist", True),
    409: ("FIRE-409", "Conflict: CRDT merge conflict or idempotency key reuse", False),
    422: ("FIRE-422", "Unprocessable Entity: Semantic validation error", False),
    429: ("FIRE-429", "Too Many Requests: Rate limit exceeded", True),
    500: ("FIRE-500", "Internal Server Error: Generic server failure", True),
    503: ("FIRE-503", "Service Unavailable: Downstream dependency failure", True),
}

async def error_handler(request: Request, exc: HTTPException):
    """Standardized error handler for all HTTP exceptions"""
    error_code, message, retryable = ERROR_REGISTRY.get(
        exc.status_code, 
        ("FIRE-500", "Internal Server Error", True)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "transaction_id": str(uuid.uuid4()),
            "error_code": error_code,
            "message": exc.detail or message,
            "retryable": retryable
        }
    )