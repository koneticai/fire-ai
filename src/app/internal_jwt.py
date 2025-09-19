"""
Internal JWT generation for secure inter-service communication.

This module handles JWT token generation for authentication between
the Python FastAPI service and the embedded Go service.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Optional

import jwt
from pydantic import BaseModel


class InternalJWTConfig(BaseModel):
    """Configuration for internal JWT generation."""
    secret_key: str
    algorithm: str = "HS256"
    expiration_minutes: int = 15


class InternalJWTManager:
    """Manages internal JWT tokens for service-to-service communication."""
    
    def __init__(self):
        self.secret_key = os.getenv("INTERNAL_JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("INTERNAL_JWT_SECRET_KEY environment variable is required")
        
        self.algorithm = "HS256"
        self.expiration_minutes = 15
    
    def generate_token(self, service_name: str = "fastapi", user_id: Optional[str] = None) -> str:
        """
        Generate an internal JWT token for service communication.
        
        Args:
            service_name: Name of the calling service
            user_id: Optional user ID for context
            
        Returns:
            JWT token string
        """
        import uuid
        
        now = datetime.utcnow()
        jti = str(uuid.uuid4())  # JWT ID for revocation tracking
        
        payload = {
            "iss": service_name,  # Issuer
            "aud": "go-service",  # Audience
            "iat": int(now.timestamp()),  # Issued at
            "exp": int((now + timedelta(minutes=self.expiration_minutes)).timestamp()),  # Expiry
            "jti": jti,  # JWT ID for revocation
            "service": service_name,
            "purpose": "internal_communication"
        }
        
        if user_id:
            payload["user_id"] = user_id
            
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> dict:
        """
        Validate an internal JWT token with proper audience and issuer checks.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        return jwt.decode(
            token, 
            self.secret_key, 
            algorithms=[self.algorithm],
            audience="go-service",
            issuer="fastapi"
        )
    
    def is_token_valid(self, token: str) -> bool:
        """
        Check if a token is valid without raising exceptions.
        
        Args:
            token: JWT token string
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self.validate_token(token)
            return True
        except jwt.InvalidTokenError:
            return False


# Global instance
internal_jwt_manager = InternalJWTManager()


def get_internal_jwt_token(user_id: Optional[str] = None) -> str:
    """
    Generate an internal JWT token for making requests to the Go service.
    
    Args:
        user_id: Optional user ID for context
        
    Returns:
        JWT token string
    """
    return internal_jwt_manager.generate_token(user_id=user_id)