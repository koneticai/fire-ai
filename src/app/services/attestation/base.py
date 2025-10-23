"""
Base classes and common functionality for device attestation validators.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AttestationResultStatus(Enum):
    """Attestation validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


@dataclass
class AttestationResult:
    """Result of device attestation validation."""
    
    status: AttestationResultStatus
    device_id: Optional[str] = None
    platform: Optional[str] = None
    validator_type: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    validated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.validated_at is None:
            self.validated_at = datetime.utcnow()
    
    @property
    def is_valid(self) -> bool:
        """Check if attestation is valid."""
        return self.status == AttestationResultStatus.VALID
    
    @property
    def is_invalid(self) -> bool:
        """Check if attestation is invalid."""
        return self.status == AttestationResultStatus.INVALID
    
    @property
    def is_error(self) -> bool:
        """Check if attestation resulted in error."""
        return self.status == AttestationResultStatus.ERROR


class AttestationValidator(ABC):
    """
    Abstract base class for device attestation validators.
    
    All platform-specific validators must implement this interface.
    """
    
    def __init__(self, config: 'AttestationConfig'):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def validate(self, token: str, device_id: Optional[str] = None, 
                metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate a device attestation token.
        
        Args:
            token: The attestation token to validate
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status and details
        """
        pass
    
    @abstractmethod
    def get_validator_type(self) -> str:
        """Get the validator type identifier."""
        pass
    
    @abstractmethod
    def get_platform(self) -> str:
        """Get the platform this validator supports."""
        pass
    
    def _calculate_token_hash(self, token: str) -> str:
        """Calculate SHA-256 hash of token for caching and logging."""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    def _create_error_result(self, error_message: str, 
                           device_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """Create an error result with consistent formatting."""
        return AttestationResult(
            status=AttestationResultStatus.ERROR,
            device_id=device_id,
            platform=self.get_platform(),
            validator_type=self.get_validator_type(),
            error_message=error_message,
            metadata=metadata
        )
    
    def _create_invalid_result(self, reason: str,
                             device_id: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """Create an invalid result with consistent formatting."""
        return AttestationResult(
            status=AttestationResultStatus.INVALID,
            device_id=device_id,
            platform=self.get_platform(),
            validator_type=self.get_validator_type(),
            error_message=reason,
            metadata=metadata
        )
    
    def _create_valid_result(self, device_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """Create a valid result with consistent formatting."""
        return AttestationResult(
            status=AttestationResultStatus.VALID,
            device_id=device_id,
            platform=self.get_platform(),
            validator_type=self.get_validator_type(),
            metadata=metadata
        )
    
    def _log_validation_attempt(self, token_hash: str, device_id: Optional[str] = None):
        """Log validation attempt for audit purposes."""
        self.logger.info(
            f"Validation attempt - Validator: {self.get_validator_type()}, "
            f"Platform: {self.get_platform()}, "
            f"Token hash: {token_hash[:8]}..., "
            f"Device ID: {device_id or 'unknown'}"
        )
    
    def _log_validation_result(self, result: AttestationResult, token_hash: str):
        """Log validation result for audit purposes."""
        self.logger.info(
            f"Validation result - Status: {result.status.value}, "
            f"Validator: {result.validator_type}, "
            f"Platform: {result.platform}, "
            f"Token hash: {token_hash[:8]}..., "
            f"Device ID: {result.device_id or 'unknown'}, "
            f"Error: {result.error_message or 'none'}"
        )
