"""
Configuration settings for FireMode Compliance Platform
"""

import os
import sys
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Required secrets - no defaults allowed
    jwt_secret_key: str
    internal_jwt_secret_key: str
    database_url: str
    
    # Configuration
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        # Do NOT use .env file in production
        env_file = None
    
    @classmethod
    def load_and_validate(cls):
        """Load settings and fail fast if secrets missing"""
        instance = cls(
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", ""),
            internal_jwt_secret_key=os.getenv("INTERNAL_JWT_SECRET_KEY", ""),
            database_url=os.getenv("DATABASE_URL", "")
        )
        
        if not instance.jwt_secret_key:
            print("ERROR: JWT_SECRET_KEY not configured in Replit Secrets")
            sys.exit(1)
        if not instance.internal_jwt_secret_key:
            print("ERROR: INTERNAL_JWT_SECRET_KEY not configured in Replit Secrets")
            sys.exit(1)
        if not instance.database_url:
            print("ERROR: DATABASE_URL not configured in Replit Secrets")
            sys.exit(1)
            
        return instance

settings = Settings.load_and_validate()