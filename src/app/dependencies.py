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
        username: str = payload.get("sub") or ""
        user_id: str = payload.get("user_id") or ""
        jti: str = payload.get("jti") or ""
        exp: int = payload.get("exp") or 0
        
        if username is None or user_id is None or jti is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(
            username=username,
            user_id=UUID(user_id),
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
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Foundational JWT Authorizer with Token Revocation List (RTL) check.
    
    Extracts JWT from Authorization: Bearer header, validates the token,
    and checks against revocation list before returning token payload.
    """
    
    # Extract JWT from Authorization: Bearer header
    token = credentials.credentials
    
    try:
        # Decode and validate the JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        user_id = payload.get("user_id")
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        if not username or not user_id or not jti or not exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create token data object
        token_data = TokenData(
            username=username,
            user_id=UUID(user_id),
            jti=jti,
            exp=datetime.fromtimestamp(exp)
        )
        
        # Functional RTL Check - query database for revoked tokens
        conn = None
        try:
            conn = get_database_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM token_revocation_list 
                    WHERE token_jti = %s AND expires_at > CURRENT_TIMESTAMP
                """, (token_data.jti,))
                
                result = cursor.fetchone()
                revoked_count = result[0] if result else 0
                if revoked_count > 0:
                    conn.close()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            conn.close()
        except HTTPException:
            if conn:
                conn.close()
            raise
        except Exception as e:
            if conn:
                conn.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token validation failed"
            )
        
        # Return token payload if valid and not revoked
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