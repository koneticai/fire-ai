"""
Pydantic schemas for device attestation data.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AttestationResultSchema(BaseModel):
    """Schema for attestation validation result."""
    
    status: str = Field(..., description="Validation status: 'valid', 'invalid', 'error'")
    device_id: Optional[str] = Field(None, description="Device identifier")
    platform: Optional[str] = Field(None, description="Platform: 'ios' or 'android'")
    validator_type: Optional[str] = Field(None, description="Validator type used")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional validation metadata")
    validated_at: Optional[datetime] = Field(None, description="When validation was performed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AttestationLogSchema(BaseModel):
    """Schema for attestation log entry."""
    
    id: str = Field(..., description="Log entry ID")
    device_id: str = Field(..., description="Device identifier")
    platform: str = Field(..., description="Platform: 'ios' or 'android'")
    validator_type: str = Field(..., description="Validator type used")
    token_hash: str = Field(..., description="SHA-256 hash of attestation token")
    result: str = Field(..., description="Validation result")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="When the attestation was attempted")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeviceTrustScoreSchema(BaseModel):
    """Schema for device trust score."""
    
    id: str = Field(..., description="Trust score record ID")
    device_id: str = Field(..., description="Device identifier")
    platform: str = Field(..., description="Platform: 'ios' or 'android'")
    trust_score: int = Field(..., description="Trust score 0-100")
    total_validations: int = Field(..., description="Total validation attempts")
    failed_validations: int = Field(..., description="Failed validation attempts")
    success_rate: float = Field(..., description="Validation success rate")
    is_trusted: bool = Field(..., description="Whether device is considered trusted")
    last_validation_at: Optional[datetime] = Field(None, description="Last validation timestamp")
    first_seen_at: datetime = Field(..., description="When device was first seen")
    updated_at: datetime = Field(..., description="When record was last updated")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AttestationStatsSchema(BaseModel):
    """Schema for attestation statistics."""
    
    total_validations: int = Field(..., description="Total validation attempts")
    successful_validations: int = Field(..., description="Successful validations")
    failed_validations: int = Field(..., description="Failed validations")
    success_rate: float = Field(..., description="Overall success rate")
    platform_breakdown: Dict[str, int] = Field(..., description="Validations by platform")
    validator_breakdown: Dict[str, int] = Field(..., description="Validations by validator type")
    cache_stats: Optional[Dict[str, Any]] = Field(None, description="Cache statistics")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AttestationConfigSchema(BaseModel):
    """Schema for attestation configuration (read-only)."""
    
    enabled: bool = Field(..., description="Whether attestation is enabled")
    stub_mode: bool = Field(..., description="Whether running in stub mode")
    feature_flag_percentage: int = Field(..., description="Feature flag percentage")
    cache_size: int = Field(..., description="Cache size")
    cache_ttl: int = Field(..., description="Cache TTL in seconds")
    rate_limit_per_device: int = Field(..., description="Rate limit per device per hour")
    is_production_ready: bool = Field(..., description="Whether config is production ready")
    
    class Config:
        from_attributes = True
