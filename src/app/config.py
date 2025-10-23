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
    
    # Device Attestation Configuration
    attestation_enabled: bool = True
    attestation_stub_mode: bool = True
    attestation_stub_allow_emulator: bool = False
    
    # C&E Module Configuration
    ce_module_enabled: bool = True
    ce_default_standard: str = "AS1851-2012"
    ce_workflow_timeout_days: int = 30
    ce_auto_archive_days: int = 365
    ce_visual_designer_max_nodes: int = 100
    
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