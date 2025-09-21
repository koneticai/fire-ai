from fastapi import Request, HTTPException
from ..utils.vector_clock import VectorClock

async def detect_concurrent_writes(request: Request, call_next):
    """Middleware to detect concurrent modifications using vector clocks"""
    if request.method in ["PUT", "PATCH", "DELETE"]:
        if_match = request.headers.get("If-Match")
        if if_match:
            # Parse vector clock from ETag
            try:
                client_clock = VectorClock.from_json(if_match)
                request.state.vector_clock = client_clock
            except:
                raise HTTPException(
                    status_code=412,
                    detail="Invalid vector clock in If-Match header"
                )
    
    response = await call_next(request)
    
    # Add vector clock to response if present
    if hasattr(request.state, "updated_clock"):
        response.headers["ETag"] = request.state.updated_clock.to_json()
    
    return response