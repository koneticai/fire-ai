"""
Authentication schemas for FireMode Compliance Platform
"""

from pydantic import BaseModel, Field
import uuid
from typing import Optional


class TokenPayload(BaseModel):
    """Token payload schema - renamed from TokenData to avoid import collision"""
    user_id: uuid.UUID = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    jti: Optional[uuid.UUID] = Field(None, description="JWT ID for revocation list")
    exp: Optional[int] = Field(None, description="Expiration timestamp")


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")