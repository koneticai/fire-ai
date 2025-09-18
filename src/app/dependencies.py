"""
FastAPI dependencies for authentication and database
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
import psycopg2
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import TokenData

# Security configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
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
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify JWT token and return token data"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        jti: str = payload.get("jti")
        exp: int = payload.get("exp")
        
        if username is None or user_id is None or jti is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(
            username=username,
            user_id=user_id,
            jti=jti,
            exp=datetime.fromtimestamp(exp)
        )
        return token_data
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
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
    current_user: TokenData = Depends(get_current_user),
    conn = Depends(get_database_connection)
) -> TokenData:
    """Get current active user (additional check for user status)"""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT is_active FROM users WHERE id = %s",
                (current_user.user_id,)
            )
            result = cursor.fetchone()
            
            if not result or not result[0]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is inactive"
                )
        
        conn.close()
        return current_user
        
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User verification failed"
        )