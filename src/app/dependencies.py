"""
FastAPI dependencies for authentication and database
Consolidated version with async-only JWT validation and proper RTL checking
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import settings
from .database.core import get_db
from .models.rtl import TokenRevocationList
from .schemas.token import TokenData
from .schemas.auth import TokenPayload

ALLOWED_JWT_ALGORITHMS = ("HS256",)

security = HTTPBearer()


async def is_token_revoked(db: AsyncSession, jti: Optional[UUID]) -> bool:
    """Check revocation status per token_revocation_list semantics (data_model.md)."""
    if jti is None:
        return False

    result = await db.execute(
        select(TokenRevocationList).where(
            TokenRevocationList.token_jti == str(jti),
            TokenRevocationList.expires_at > datetime.now(timezone.utc)
        )
    )
    return result.scalar_one_or_none() is not None

async def get_current_active_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> TokenPayload:
    """Validate JWT and check revocation list using async database operations"""
    try:
        # Use verify_token for consistent validation logic
        token_data = verify_token(token.credentials)
        
        # Check RTL using async SQLAlchemy operations
        if token_data.jti and await is_token_revoked(db, token_data.jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        return token_data
        
    except HTTPException:
        # Re-raise HTTP exceptions (including those from verify_token)
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with jti for revocation tracking"""
    import uuid
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    # Add JWT ID for revocation tracking
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> TokenPayload:
    """Verify JWT token and return token data"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=list(ALLOWED_JWT_ALGORITHMS),
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "require_exp": True,
            },
        )
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
        
        # Validate jti is a valid UUID format
        try:
            jti_uuid = UUID(jti) if jti else None
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token - malformed jti",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenPayload(
            username=username,
            user_id=user_uuid,
            jti=jti_uuid,
            exp=exp
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

def get_password_hash(password: str) -> str:
    """Hash password for storage"""
    import bcrypt
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    return password_hash.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    import bcrypt
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )