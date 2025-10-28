"""
Configuration settings for FireMode Compliance Platform
"""

import os
import sys
from pydantic_settings import BaseSettings
from pydantic import field_validator

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
    
    @field_validator('jwt_secret_key', 'internal_jwt_secret_key')
    @classmethod
    def validate_secret_strength(cls, v: str, info) -> str:
        """Enforce minimum 32-character secret keys per OWASP guidelines"""
        if len(v) < 32:
            raise ValueError(
                f"{info.field_name} must be at least 32 characters "
                f"(current: {len(v)}). Generate with: openssl rand -hex 32"
            )
        # Check for common weak patterns (repeated or contained)
        weak_patterns = ['test', 'secret', 'password', 'changeme']
        v_lower = v.lower()
        for pattern in weak_patterns:
            # Check if pattern appears 3+ times (indicating repetition)
            if v_lower.count(pattern) >= 3:
                raise ValueError(f"{info.field_name} contains weak pattern")
        return v
    
    @field_validator('attestation_stub_mode')
    @classmethod
    def block_stub_mode_in_production(cls, v: bool) -> bool:
        """Block stub mode in production environment per AS 1851-2012 requirements"""
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production' and v:
            raise ValueError(
                "attestation_stub_mode=True is FORBIDDEN in production. "
                "Device attestation is required for compliance evidence. "
                "Set ATTESTATION_STUB_MODE=false in environment."
            )
        return v
    
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

# Only auto-load settings if not in test mode
# Tests can import Settings class without triggering validation
_in_test_mode = os.getenv('PYTEST_CURRENT_TEST') is not None

if not _in_test_mode:
    settings = Settings.load_and_validate()
else:
    # In test mode, provide a lazy loader
    settings = None  # Tests should instantiate Settings directly