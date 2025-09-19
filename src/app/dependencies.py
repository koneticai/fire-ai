"""
FastAPI dependencies for authentication and database
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import jwt, JWTError, ExpiredSignatureError
import psycopg2
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import TokenData

# Security configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is required")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()

def get_database_connection():
    """Get database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database configuration error"
        )
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"
        )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with jti for revocation tracking"""
    import uuid
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    # Add JWT ID for revocation tracking
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify JWT token and return token data"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("user_id")
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        # Require all critical claims to be present and non-empty
        if not username or not user_id or not jti or not exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token - missing required claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate user_id is a valid UUID format
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token - malformed user_id",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(
            username=username,
            user_id=user_uuid,
            jti=jti,
            exp=datetime.fromtimestamp(exp)
        )
        return token_data
    
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def check_token_revocation(jti: str, conn) -> bool:
    """Check if token is in revocation list"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM token_revocation_list WHERE token_jti = %s AND expires_at > CURRENT_TIMESTAMP",
                (jti,)
            )
            count = cursor.fetchone()[0]
            return count > 0
    except Exception:
        # If we can't check revocation, err on the side of caution
        return True

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn = Depends(get_database_connection)
) -> TokenData:
    """Get current authenticated user from JWT token with RTL check"""
    
    token = credentials.credentials
    token_data = verify_token(token)
    
    # Check token revocation list
    if check_token_revocation(token_data.jti, conn):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    conn.close()
    return token_data

async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn = Depends(get_database_connection)
) -> TokenData:
    """
    Foundational JWT Authorizer with Token Revocation List (RTL) check.
    
    Extracts JWT from Authorization: Bearer header, validates the token,
    and checks against revocation list before returning token payload.
    """
    
    token = credentials.credentials
    
    try:
        # Delegate to verify_token for consistent validation
        token_data = verify_token(token)
        
        # Critical RTL Check - query database for revoked tokens
        if check_token_revocation(token_data.jti, conn):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Close connection and return token payload if valid and not revoked
        conn.close()
        return token_data
        
    except HTTPException:
        # Close connection on HTTP exceptions and re-raise
        if conn:
            conn.close()
        raise
    except Exception as e:
        # Close connection on any other exception and return 401
        if conn:
            conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )