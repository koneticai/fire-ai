"""
Authentication router for FireMode Compliance Platform
Handles user authentication, logout, and token management
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..schemas.token import TokenData, APIResponse
from ..dependencies import get_current_active_user
from ..database.core import get_db
from ..middleware.rate_limiter import limiter
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Authentication"])

@router.get("/debug/config")
async def debug_config():
    """Debug endpoint to verify JWT configuration"""
    from ..config import settings
    return {
        "jwt_secret_loaded": bool(settings.jwt_secret_key),
        "jwt_secret_length": len(settings.jwt_secret_key),
        "jwt_secret_prefix": settings.jwt_secret_key[:8] + "...",
        "algorithm": settings.algorithm
    }

@router.post("/logout", response_model=APIResponse, summary="Logout User", description="Revoke the current user's JWT token by adding it to the revocation list")
@limiter.limit("5/minute")
async def logout(
    request: Request,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revokes the current user's token by adding its JTI to the revocation list.
    After logout, the token will be invalid for all future requests.
    """
    
    try:
        with conn.cursor() as cursor:
            # Calculate token expiration time (24 hours from revocation)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Add token to revocation list
            cursor.execute("""
                INSERT INTO token_revocation_list 
                (token_jti, user_id, expires_at) 
                VALUES (%s, %s, %s)
                ON CONFLICT (token_jti) DO NOTHING
            """, (
                current_user.jti,
                current_user.user_id,
                expires_at
            ))
            
            # Log the logout action in audit log
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            cursor.execute("""
                INSERT INTO audit_log 
                (user_id, action, resource_type, resource_id, new_values, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                current_user.user_id,
                "logout",
                "token",
                None,
                json.dumps({
                    "token_jti": current_user.jti,
                    "revoked_at": datetime.utcnow().isoformat()
                }),
                client_ip,
                user_agent
            ))
            
            conn.commit()
        
        conn.close()
        
        return APIResponse(
            status="success",
            message="Successfully logged out"
        )
        
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )