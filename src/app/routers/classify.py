"""
Classification router for FireMode Compliance Platform
High-performance classification endpoint (proxied to Go service)
"""

import httpx
from fastapi import APIRouter, Depends, status, Request, HTTPException
from fastapi.responses import JSONResponse

from ..models import FaultDataInput, ClassificationResult, TokenData
from ..dependencies import get_current_active_user
from ..internal_jwt import get_internal_jwt_token

router = APIRouter(tags=["Classification"])

# Global Go service client reference (set by main app)
go_service_client = None

def set_go_service_client(client: httpx.AsyncClient):
    """Set the Go service client for this router"""
    global go_service_client
    go_service_client = client

@router.post("", response_model=ClassificationResult, status_code=status.HTTP_200_OK,
             summary="Classify Fault",
             description="High-performance fault classification endpoint (proxied to Go service). Classifies a fault based on the latest active AS1851 rule and creates an immutable audit log of the transaction.")
async def create_classification(
    fault_data: FaultDataInput,
    request: Request,
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    High-performance fault classification (proxied to Go service).
    
    Classifies a fault based on the latest active AS1851 rule
    and creates an immutable audit log of the transaction.
    """
    if not go_service_client:
        raise HTTPException(status_code=503, detail="High-performance classification service unavailable")
    
    try:
        # Prepare request body
        body = fault_data.model_dump_json()
        
        # Prepare headers for Go service with internal JWT authentication
        headers = {
            "Content-Type": "application/json",
            "X-Internal-Authorization": get_internal_jwt_token(str(current_user.user_id)),
            "X-User-ID": str(current_user.user_id),
            "User-Agent": request.headers.get("user-agent", "FastAPI-Proxy")
        }
        
        # Add client IP forwarding
        client_ip = request.client.host if request.client else "unknown"
        headers["X-Forwarded-For"] = client_ip
        
        # Forward the request to Go service
        response = await go_service_client.post(
            "/v1/classify",
            content=body,
            headers=headers,
            timeout=30.0
        )
        
        # Filter response headers to only include safe headers
        safe_headers = {
            k: v for k, v in response.headers.items() 
            if k.lower() in ["content-type", "content-length", "cache-control"]
        }
        
        # Handle JSON and non-JSON responses from Go service
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                content = response.json()
            except Exception:
                content = {"detail": "Invalid JSON response from classification service"}
        else:
            content = {"detail": response.text}
        
        return JSONResponse(
            content=content,
            status_code=response.status_code,
            headers=safe_headers
        )
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Classification request timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="High-performance classification service error")