"""
iOS App Attest validator for device attestation.

Validates App Attest assertions from iOS 14+ devices to ensure
requests are coming from legitimate, unmodified iOS apps.
"""

import json
import logging
from typing import Optional, Dict, Any
import jwt
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature

from .base import AttestationValidator, AttestationResult, AttestationResultStatus
from .config import AttestationConfig

logger = logging.getLogger(__name__)


class AppAttestValidator(AttestationValidator):
    """
    Validator for iOS App Attest assertions.
    
    Validates App Attest assertions to verify app integrity and device legitimacy.
    Supports both production validation and stub mode for testing.
    """
    
    def __init__(self, config: AttestationConfig):
        super().__init__(config)
        self.ios_config = config.get_ios_config()
        
    def get_validator_type(self) -> str:
        return "appattest"
    
    def get_platform(self) -> str:
        return "ios"
    
    def validate(self, assertion: str, device_id: Optional[str] = None, 
                metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate an App Attest assertion.
        
        Args:
            assertion: The App Attest assertion (JWT) to validate
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status
        """
        token_hash = self._calculate_token_hash(assertion)
        self._log_validation_attempt(token_hash, device_id)
        
        try:
            # Check if running in stub mode
            if self.ios_config["stub_mode"]:
                result = self._validate_stub_mode(assertion, device_id, metadata)
            else:
                result = self._validate_production(assertion, device_id, metadata)
            
            self._log_validation_result(result, token_hash)
            return result
            
        except Exception as e:
            error_msg = f"App Attest validation error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result = self._create_error_result(error_msg, device_id, metadata)
            self._log_validation_result(result, token_hash)
            return result
    
    def _validate_stub_mode(self, assertion: str, device_id: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate assertion in stub mode (for testing).
        
        Stub mode behavior:
        - Reject 'emulator' assertions if stub_allow_emulator=False
        - Accept all other assertions
        """
        if assertion == "emulator" and not self.ios_config["stub_allow_emulator"]:
            return self._create_invalid_result(
                "Emulator assertions not allowed in stub mode",
                device_id,
                {**(metadata or {}), "stub_mode": True, "reason": "emulator_rejected"}
            )
        
        # Accept all other assertions in stub mode
        return self._create_valid_result(
            device_id,
            {**(metadata or {}), "stub_mode": True, "reason": "stub_accepted"}
        )
    
    def _validate_production(self, assertion: str, device_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate assertion using App Attest verification.
        
        Args:
            assertion: The App Attest assertion (JWT)
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status
        """
        # Validate configuration
        if not self.ios_config["app_id"]:
            return self._create_error_result(
                "App Attest configuration incomplete - missing app ID",
                device_id,
                metadata
            )
        
        try:
            # Decode JWT header to get key ID
            header = jwt.get_unverified_header(assertion)
            key_id = header.get("kid")
            
            if not key_id:
                return self._create_invalid_result(
                    "App Attest assertion missing key ID",
                    device_id,
                    metadata
                )
            
            # Get Apple's public key for verification
            public_key = self._get_apple_public_key(key_id)
            if not public_key:
                return self._create_error_result(
                    f"Failed to retrieve Apple public key for key ID: {key_id}",
                    device_id,
                    metadata
                )
            
            # Verify JWT signature
            try:
                payload = jwt.decode(
                    assertion,
                    public_key,
                    algorithms=["ES256"],
                    options={"verify_exp": True, "verify_iat": True}
                )
            except jwt.ExpiredSignatureError:
                return self._create_invalid_result(
                    "App Attest assertion has expired",
                    device_id,
                    metadata
                )
            except jwt.InvalidTokenError as e:
                return self._create_invalid_result(
                    f"App Attest assertion is invalid: {str(e)}",
                    device_id,
                    metadata
                )
            
            # Validate payload structure
            validation_result = self._validate_assertion_payload(payload, device_id, metadata)
            if validation_result:
                return validation_result
            
            # All validations passed
            return self._create_valid_result(
                device_id,
                {**(metadata or {}), "app_id": payload.get("iss"), "key_id": key_id}
            )
            
        except Exception as e:
            return self._create_error_result(f"App Attest validation failed: {str(e)}", device_id, metadata)
    
    def _get_apple_public_key(self, key_id: str) -> Optional[ec.EllipticCurvePublicKey]:
        """
        Retrieve Apple's public key for App Attest verification.
        
        Args:
            key_id: The key ID from the JWT header
            
        Returns:
            Apple's public key or None if not found
        """
        # In a real implementation, this would fetch the key from Apple's servers
        # For now, we'll create a mock key for testing
        try:
            # Generate a mock EC key for testing
            # In production, this would be fetched from Apple's key server
            private_key = ec.generate_private_key(ec.SECP256R1())
            public_key = private_key.public_key()
            
            logger.warning(f"Using mock Apple public key for key ID: {key_id}")
            return public_key
            
        except Exception as e:
            logger.error(f"Failed to get Apple public key for key ID {key_id}: {str(e)}")
            return None
    
    def _validate_assertion_payload(self, payload: dict, device_id: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> Optional[AttestationResult]:
        """
        Validate App Attest assertion payload.
        
        Args:
            payload: Decoded JWT payload
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult if validation fails, None if successful
        """
        # Check required fields
        required_fields = ["iss", "iat", "exp"]
        for field in required_fields:
            if field not in payload:
                return self._create_invalid_result(
                    f"App Attest assertion missing required field: {field}",
                    device_id,
                    metadata
                )
        
        # Validate app ID
        if payload.get("iss") != self.ios_config["app_id"]:
            return self._create_invalid_result(
                f"App Attest assertion app ID mismatch: expected {self.ios_config['app_id']}, got {payload.get('iss')}",
                device_id,
                metadata
            )
        
        # Validate timestamp (not too old)
        iat = payload.get("iat")
        if iat:
            issued_at = datetime.fromtimestamp(iat)
            if datetime.utcnow() - issued_at > timedelta(hours=1):
                return self._create_invalid_result(
                    "App Attest assertion is too old",
                    device_id,
                    metadata
                )
        
        # Check for challenge (if present)
        challenge = payload.get("challenge")
        if challenge:
            # In a real implementation, we'd verify the challenge matches what we sent
            logger.debug(f"App Attest assertion contains challenge: {challenge}")
        
        return None  # Validation successful
    
    def is_configured(self) -> bool:
        """
        Check if validator is properly configured for production use.
        
        Returns:
            True if all required configuration is present
        """
        if self.ios_config["stub_mode"]:
            return True
        
        return bool(self.ios_config["app_id"])
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """
        Get detailed configuration status.
        
        Returns:
            Dictionary with configuration status details
        """
        return {
            "validator_type": self.get_validator_type(),
            "platform": self.get_platform(),
            "stub_mode": self.ios_config["stub_mode"],
            "configured": self.is_configured(),
            "has_app_id": bool(self.ios_config["app_id"]),
            "stub_allow_emulator": self.ios_config["stub_allow_emulator"]
        }
