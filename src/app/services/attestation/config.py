"""
Configuration management for device attestation service.
"""

import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


class AttestationConfig(BaseSettings):
    """
    Configuration for device attestation service.
    
    Loads from environment variables with sensible defaults for development.
    """
    
    # Feature flags
    enabled: bool = Field(default=True, env="ATTESTATION_ENABLED")
    stub_mode: bool = Field(default=True, env="ATTESTATION_STUB_MODE")
    stub_allow_emulator: bool = Field(default=False, env="ATTESTATION_STUB_ALLOW_EMULATOR")
    feature_flag_percentage: int = Field(default=100, env="ATTESTATION_FEATURE_FLAG_PERCENTAGE")
    
    # iOS DeviceCheck configuration
    apple_team_id: Optional[str] = Field(default=None, env="APPLE_TEAM_ID")
    apple_key_id: Optional[str] = Field(default=None, env="APPLE_KEY_ID")
    apple_private_key_path: Optional[str] = Field(default=None, env="APPLE_PRIVATE_KEY_PATH")
    
    # iOS App Attest configuration
    app_attest_app_id: Optional[str] = Field(default=None, env="APP_ATTEST_APP_ID")
    
    # Android Play Integrity configuration
    google_cloud_project_id: Optional[str] = Field(default=None, env="GOOGLE_CLOUD_PROJECT_ID")
    google_application_credentials: Optional[str] = Field(default=None, env="GOOGLE_APPLICATION_CREDENTIALS")
    play_integrity_decryption_key: Optional[str] = Field(default=None, env="PLAY_INTEGRITY_DECRYPTION_KEY")
    
    # Android SafetyNet configuration (legacy)
    safetynet_api_key: Optional[str] = Field(default=None, env="SAFETYNET_API_KEY")
    
    # Cache configuration
    cache_size: int = Field(default=10000, env="ATTESTATION_CACHE_SIZE")
    cache_ttl: int = Field(default=3600, env="ATTESTATION_CACHE_TTL")  # 1 hour
    
    # Rate limiting configuration
    rate_limit_per_device: int = Field(default=100, env="ATTESTATION_RATE_LIMIT")
    rate_limit_window: int = Field(default=3600, env="ATTESTATION_RATE_LIMIT_WINDOW")  # 1 hour
    
    # API timeout configuration
    api_timeout: int = Field(default=30, env="ATTESTATION_API_TIMEOUT")
    
    class Config:
        env_file = None  # Don't use .env files in production
        case_sensitive = False
    
    def is_production_ready(self) -> bool:
        """
        Check if configuration is ready for production use.
        
        Returns:
            True if all required credentials are configured
        """
        if self.stub_mode:
            return True
        
        # Check iOS credentials
        ios_ready = all([
            self.apple_team_id,
            self.apple_key_id,
            self.apple_private_key_path,
            self.app_attest_app_id
        ])
        
        # Check Android credentials
        android_ready = all([
            self.google_cloud_project_id,
            self.google_application_credentials,
            self.play_integrity_decryption_key
        ]) or self.safetynet_api_key
        
        return ios_ready and android_ready
    
    def get_ios_config(self) -> dict:
        """Get iOS-specific configuration."""
        return {
            "team_id": self.apple_team_id,
            "key_id": self.apple_key_id,
            "private_key_path": self.apple_private_key_path,
            "app_id": self.app_attest_app_id,
            "stub_mode": self.stub_mode,
            "stub_allow_emulator": self.stub_allow_emulator
        }
    
    def get_android_config(self) -> dict:
        """Get Android-specific configuration."""
        return {
            "project_id": self.google_cloud_project_id,
            "credentials_path": self.google_application_credentials,
            "decryption_key_path": self.play_integrity_decryption_key,
            "safetynet_api_key": self.safetynet_api_key,
            "stub_mode": self.stub_mode,
            "stub_allow_emulator": self.stub_allow_emulator
        }
    
    def validate_config(self) -> list[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of configuration issues (empty if valid)
        """
        issues = []
        
        if not self.enabled:
            return issues  # No validation needed if disabled
        
        if self.stub_mode:
            logger.info("Attestation running in stub mode - no credential validation needed")
            return issues
        
        # Validate iOS configuration
        if not self.apple_team_id:
            issues.append("APPLE_TEAM_ID is required for iOS DeviceCheck")
        if not self.apple_key_id:
            issues.append("APPLE_KEY_ID is required for iOS DeviceCheck")
        if not self.apple_private_key_path:
            issues.append("APPLE_PRIVATE_KEY_PATH is required for iOS DeviceCheck")
        if not self.app_attest_app_id:
            issues.append("APP_ATTEST_APP_ID is required for iOS App Attest")
        
        # Validate Android configuration
        if not self.safetynet_api_key and not all([
            self.google_cloud_project_id,
            self.google_application_credentials,
            self.play_integrity_decryption_key
        ]):
            issues.append("Either SAFETYNET_API_KEY or Google Play Integrity credentials are required")
        
        return issues
    
    def log_config_summary(self):
        """Log configuration summary for debugging."""
        logger.info(f"Attestation config - Enabled: {self.enabled}, "
                   f"Stub mode: {self.stub_mode}, "
                   f"Feature flag: {self.feature_flag_percentage}%, "
                   f"Cache size: {self.cache_size}, "
                   f"Cache TTL: {self.cache_ttl}s, "
                   f"Rate limit: {self.rate_limit_per_device}/hour")
        
        if not self.stub_mode:
            logger.info(f"iOS config - Team ID: {self.apple_team_id}, "
                       f"Key ID: {self.apple_key_id}, "
                       f"App ID: {self.app_attest_app_id}")
            logger.info(f"Android config - Project ID: {self.google_cloud_project_id}, "
                       f"SafetyNet key: {'configured' if self.safetynet_api_key else 'not configured'}")


# Global configuration instance
config = AttestationConfig()
