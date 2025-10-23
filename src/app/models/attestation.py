"""
SQLAlchemy models for device attestation logging and trust scoring.
"""

import uuid
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class AttestationLog(Base):
    """
    SQLAlchemy model for attestation_logs table.
    
    Stores audit trail of all device attestation attempts.
    """
    __tablename__ = 'attestation_logs'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Device and platform information
    device_id = Column(
        String(255), 
        nullable=False,
        doc="Device identifier (hash or UUID)"
    )
    platform = Column(
        String(20), 
        nullable=False,
        doc="Platform: 'ios' or 'android'"
    )
    validator_type = Column(
        String(50), 
        nullable=False,
        doc="Validator type: 'devicecheck', 'appattest', 'playintegrity', 'safetynet'"
    )
    
    # Token information
    token_hash = Column(
        String(64), 
        nullable=False,
        doc="SHA-256 hash of the attestation token"
    )
    
    # Validation result
    result = Column(
        String(20), 
        nullable=False,
        doc="Validation result: 'valid', 'invalid', 'error'"
    )
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if validation failed"
    )
    
    # Additional metadata
    metadata = Column(
        JSONB, 
        nullable=True, 
        default={},
        doc="Additional validation metadata"
    )
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the attestation was attempted"
    )
    
    def __repr__(self):
        return f"<AttestationLog(id={self.id}, device={self.device_id}, platform={self.platform}, result={self.result})>"


class DeviceTrustScore(Base):
    """
    SQLAlchemy model for device_trust_scores table.
    
    Tracks trust scores and validation history for devices.
    """
    __tablename__ = 'device_trust_scores'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Device information
    device_id = Column(
        String(255), 
        unique=True, 
        nullable=False,
        doc="Device identifier (hash or UUID)"
    )
    platform = Column(
        String(20), 
        nullable=False,
        doc="Platform: 'ios' or 'android'"
    )
    
    # Trust scoring
    trust_score = Column(
        Integer, 
        nullable=False, 
        default=100,
        doc="Trust score 0-100 (100 = fully trusted)"
    )
    total_validations = Column(
        Integer, 
        nullable=False, 
        default=0,
        doc="Total number of validation attempts"
    )
    failed_validations = Column(
        Integer, 
        nullable=False, 
        default=0,
        doc="Number of failed validation attempts"
    )
    
    # Timestamps
    last_validation_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last validation attempt"
    )
    first_seen_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When this device was first seen"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When this record was last updated"
    )
    
    @property
    def success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.total_validations == 0:
            return 1.0
        return (self.total_validations - self.failed_validations) / self.total_validations
    
    @property
    def is_trusted(self) -> bool:
        """Check if device is considered trusted (score >= 70)."""
        return self.trust_score >= 70
    
    def update_trust_score(self, validation_successful: bool) -> None:
        """
        Update trust score based on validation result.
        
        Args:
            validation_successful: Whether the validation was successful
        """
        self.total_validations += 1
        if not validation_successful:
            self.failed_validations += 1
        
        # Calculate new trust score based on success rate
        success_rate = self.success_rate
        
        # Trust score algorithm:
        # - Start at 100
        # - Decrease by 5 points for each failure
        # - Increase by 1 point for each success (up to max 100)
        if validation_successful:
            self.trust_score = min(100, self.trust_score + 1)
        else:
            self.trust_score = max(0, self.trust_score - 5)
        
        # Update timestamp
        from datetime import datetime
        self.last_validation_at = datetime.utcnow()
    
    def __repr__(self):
        return f"<DeviceTrustScore(device={self.device_id}, platform={self.platform}, score={self.trust_score})>"
