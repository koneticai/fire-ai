"""
Configuration settings for FireMode Compliance Platform
"""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support and validation"""
    
    # JWT Configuration
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    internal_jwt_secret_key: str = os.getenv("INTERNAL_JWT_SECRET_KEY", "")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # PII Encryption
    pii_encryption_key: str = os.getenv("PII_ENCRYPTION_KEY", "")
    
    # Go Service
    go_service_url: str = "http://localhost:9091"
    
    class Config:
        env_file = ".env"
        
    def validate_secrets(self):
        """Fail fast if critical secrets are not configured"""
        if not self.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY not configured in secrets")
        if not self.internal_jwt_secret_key:
            raise ValueError("INTERNAL_JWT_SECRET_KEY not configured in secrets")
        if not self.database_url:
            raise ValueError("DATABASE_URL not configured in secrets")

settings = Settings()
settings.validate_secrets()