"""
Token Revocation List (RTL) management router.

This router provides endpoints for managing token revocation,
allowing administrators to revoke JWT tokens for security purposes.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dependencies import get_current_active_user, get_database_connection
from ..models.rtl import TokenRevocationList


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["token_revocation"])


class TokenRevocationRequest(BaseModel):
    """Request model for token revocation."""
    token_jti: str
    reason: str
    expires_in_hours: Optional[int] = 24


class TokenRevocationResponse(BaseModel):
    """Response model for token revocation."""
    token_jti: str
    revoked_at: datetime
    reason: str
    expires_at: datetime
    message: str


class RevokedTokenInfo(BaseModel):
    """Information about a revoked token."""
    token_jti: str
    user_id: str
    revoked_at: datetime
    reason: str
    revoked_by: str
    expires_at: datetime


@router.post("/revoke-token", response_model=TokenRevocationResponse)
async def revoke_token(
    request: TokenRevocationRequest,
    current_user = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """
    Revoke a JWT token by adding it to the revocation list.
    
    This endpoint allows administrators to revoke specific tokens,
    making them invalid for future authentication attempts.
    """
    try:
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)
        
        # Insert revocation record
        with conn.cursor() as cursor:
            # Check if token is already revoked
            cursor.execute(
                "SELECT COUNT(*) FROM token_revocation_list WHERE token_jti = %s",
                (request.token_jti,)
            )
            if cursor.fetchone()[0] > 0:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token is already revoked"
                )
            
            # Insert revocation record
            cursor.execute("""
                INSERT INTO token_revocation_list 
                (token_jti, user_id, revoked_at, reason, revoked_by, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                request.token_jti,
                str(current_user.user_id),
                datetime.utcnow(),
                request.reason,
                str(current_user.user_id),
                expires_at
            ))
            conn.commit()
        
        conn.close()
        
        logger.info(f"Token {request.token_jti} revoked by user {current_user.user_id}")
        
        return TokenRevocationResponse(
            token_jti=request.token_jti,
            revoked_at=datetime.utcnow(),
            reason=request.reason,
            expires_at=expires_at,
            message="Token successfully revoked"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Token revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token revocation failed"
        )


@router.post("/revoke-my-token")
async def revoke_my_token(
    reason: str = "user_logout",
    current_user = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """
    Revoke the current user's token (logout).
    
    This endpoint allows users to revoke their own current token,
    effectively logging themselves out.
    """
    try:
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO token_revocation_list 
                (token_jti, user_id, revoked_at, reason, revoked_by, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                current_user.jti,
                str(current_user.user_id),
                datetime.utcnow(),
                reason,
                str(current_user.user_id),
                expires_at
            ))
            conn.commit()
        
        conn.close()
        
        logger.info(f"User {current_user.user_id} revoked their own token")
        
        return {
            "message": "Token revoked successfully. You are now logged out.",
            "token_jti": current_user.jti,
            "revoked_at": datetime.utcnow()
        }
        
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Self token revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token revocation failed"
        )


@router.get("/revoked-tokens", response_model=List[RevokedTokenInfo])
async def list_revoked_tokens(
    limit: int = 100,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """
    List revoked tokens (admin endpoint).
    
    This endpoint allows administrators to view revoked tokens
    for monitoring and audit purposes.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT token_jti, user_id, revoked_at, reason, revoked_by, expires_at
                FROM token_revocation_list
                WHERE expires_at > CURRENT_TIMESTAMP
                ORDER BY revoked_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            results = cursor.fetchall()
            
        conn.close()
        
        revoked_tokens = []
        for row in results:
            revoked_tokens.append(RevokedTokenInfo(
                token_jti=row[0],
                user_id=row[1],
                revoked_at=row[2],
                reason=row[3],
                revoked_by=row[4],
                expires_at=row[5]
            ))
        
        return revoked_tokens
        
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to list revoked tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve revoked tokens"
        )


@router.delete("/cleanup-expired-tokens")
async def cleanup_expired_tokens(
    current_user = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """
    Clean up expired token revocation entries.
    
    This maintenance endpoint removes expired entries from the RTL
    to keep the table size manageable.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM token_revocation_list
                WHERE expires_at <= CURRENT_TIMESTAMP
            """)
            deleted_count = cursor.rowcount
            conn.commit()
        
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} expired token revocation entries")
        
        return {
            "message": f"Cleaned up {deleted_count} expired entries",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Token cleanup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token cleanup failed"
        )