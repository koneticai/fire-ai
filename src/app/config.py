"""
Configuration settings for FireMode Compliance Platform
"""

import os
import secrets
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # JWT Configuration
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    INTERNAL_JWT_SECRET_KEY: str = os.getenv("INTERNAL_JWT_SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # PII Encryption
    PII_ENCRYPTION_KEY: str = os.getenv("PII_ENCRYPTION_KEY", secrets.token_urlsafe(32))
    
    # Go Service
    GO_SERVICE_URL: str = "http://localhost:9091"
    
    class Config:
        env_file = ".env"

settings = Settings()