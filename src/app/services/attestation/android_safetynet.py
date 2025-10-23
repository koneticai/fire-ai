"""
Android SafetyNet validator for device attestation.

Validates SafetyNet attestation tokens from Google's SafetyNet API to ensure
requests are coming from legitimate, unmodified Android devices.
This is the legacy validator for older Android versions.
"""

import json
import logging
from typing import Optional, Dict, Any
import httpx
import base64
import jwt
from datetime import datetime

from .base import AttestationValidator, AttestationResult, AttestationResultStatus
from .config import AttestationConfig

logger = logging.getLogger(__name__)


class SafetyNetValidator(AttestationValidator):
    """
    Validator for Android SafetyNet attestation tokens.
    
    Validates tokens using Google's SafetyNet API to verify device and app integrity.
    This is the legacy validator for older Android versions that don't support Play Integrity.
    Supports both production validation and stub mode for testing.
    """
    
    SAFETYNET_API_URL = "https://www.googleapis.com/androidcheck/v1/attestations/verify"
    
    def __init__(self, config: AttestationConfig):
        super().__init__(config)
        self.android_config = config.get_android_config()
        
    def get_validator_type(self) -> str:
        return "safetynet"
    
    def get_platform(self) -> str:
        return "android"
    
    def validate(self, token: str, device_id: Optional[str] = None, 
                metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate a SafetyNet attestation token.
        
        Args:
            token: The SafetyNet attestation token to validate
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status
        """
        token_hash = self._calculate_token_hash(token)
        self._log_validation_attempt(token_hash, device_id)
        
        try:
            # Check if running in stub mode
            if self.android_config["stub_mode"]:
                result = self._validate_stub_mode(token, device_id, metadata)
            else:
                result = self._validate_production(token, device_id, metadata)
            
            self._log_validation_result(result, token_hash)
            return result
            
        except Exception as e:
            error_msg = f"SafetyNet validation error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result = self._create_error_result(error_msg, device_id, metadata)
            self._log_validation_result(result, token_hash)
            return result
    
    def _validate_stub_mode(self, token: str, device_id: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate token in stub mode (for testing).
        
        Stub mode behavior:
        - Reject 'emulator' tokens if stub_allow_emulator=False
        - Accept all other tokens
        """
        if token == "emulator" and not self.android_config["stub_allow_emulator"]:
            return self._create_invalid_result(
                "Emulator tokens not allowed in stub mode",
                device_id,
                {**(metadata or {}), "stub_mode": True, "reason": "emulator_rejected"}
            )
        
        # Accept all other tokens in stub mode
        return self._create_valid_result(
            device_id,
            {**(metadata or {}), "stub_mode": True, "reason": "stub_accepted"}
        )
    
    def _validate_production(self, token: str, device_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate token using Google's SafetyNet API.
        
        Args:
            token: The SafetyNet attestation token
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status
        """
        # Validate configuration
        if not self.android_config["safetynet_api_key"]:
            return self._create_error_result(
                "SafetyNet configuration incomplete - missing API key",
                device_id,
                metadata
            )
        
        try:
            # Verify the JWS signature
            verified_payload = self._verify_jws_signature(token)
            if not verified_payload:
                return self._create_invalid_result(
                    "SafetyNet token signature verification failed",
                    device_id,
                    metadata
                )
            
            # Validate the payload
            validation_result = self._validate_safetynet_payload(verified_payload, device_id, metadata)
            if validation_result:
                return validation_result
            
            # All validations passed
            return self._create_valid_result(
                device_id,
                {**(metadata or {}), "safetynet_payload": verified_payload}
            )
            
        except Exception as e:
            return self._create_error_result(f"SafetyNet validation failed: {str(e)}", device_id, metadata)
    
    def _verify_jws_signature(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify SafetyNet JWS signature.
        
        Args:
            token: The SafetyNet attestation token (JWS)
            
        Returns:
            Verified payload or None if verification failed
        """
        try:
            # Decode JWT without verification first to get header
            unverified_header = jwt.get_unverified_header(token)
            unverified_payload = jwt.get_unverified_claims(token)
            
            # Get Google's public key for verification
            public_key = self._get_google_public_key(unverified_header.get("kid"))
            if not public_key:
                logger.error("Failed to get Google public key for SafetyNet verification")
                return None
            
            # Verify the JWT signature
            try:
                verified_payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    options={"verify_exp": True, "verify_iat": True}
                )
                return verified_payload
            except jwt.ExpiredSignatureError:
                logger.error("SafetyNet token has expired")
                return None
            except jwt.InvalidTokenError as e:
                logger.error(f"SafetyNet token is invalid: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to verify SafetyNet JWS signature: {str(e)}")
            return None
    
    def _get_google_public_key(self, key_id: str) -> Optional[str]:
        """
        Get Google's public key for SafetyNet verification.
        
        Args:
            key_id: The key ID from the JWT header
            
        Returns:
            Public key string or None if not found
        """
        # In a real implementation, this would fetch the key from Google's key server
        # For now, we'll return a mock key for testing
        logger.warning(f"Using mock Google public key for SafetyNet key ID: {key_id}")
        return "mock_google_public_key"
    
    def _validate_safetynet_payload(self, payload: Dict[str, Any],
                                  device_id: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> Optional[AttestationResult]:
        """
        Validate SafetyNet payload.
        
        Args:
            payload: Verified SafetyNet payload
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult if validation fails, None if successful
        """
        # Check required fields
        required_fields = ["nonce", "timestampMs", "apkPackageName", "ctsProfileMatch", "basicIntegrity"]
        for field in required_fields:
            if field not in payload:
                return self._create_invalid_result(
                    f"SafetyNet payload missing required field: {field}",
                    device_id,
                    metadata
                )
        
        # Validate nonce (if present in metadata)
        nonce = payload.get("nonce")
        if nonce and metadata and "expected_nonce" in metadata:
            if nonce != metadata["expected_nonce"]:
                return self._create_invalid_result(
                    "SafetyNet nonce mismatch",
                    device_id,
                    metadata
                )
        
        # Validate timestamp (not too old)
        timestamp_ms = payload.get("timestampMs")
        if timestamp_ms:
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
            if datetime.utcnow() - timestamp > timedelta(hours=1):
                return self._create_invalid_result(
                    "SafetyNet token is too old",
                    device_id,
                    metadata
                )
        
        # Validate CTS profile match (device is certified)
        cts_profile_match = payload.get("ctsProfileMatch", False)
        if not cts_profile_match:
            return self._create_invalid_result(
                "SafetyNet CTS profile match failed - device not certified",
                device_id,
                {**(metadata or {}), "cts_profile_match": cts_profile_match}
            )
        
        # Validate basic integrity
        basic_integrity = payload.get("basicIntegrity", False)
        if not basic_integrity:
            return self._create_invalid_result(
                "SafetyNet basic integrity check failed",
                device_id,
                {**(metadata or {}), "basic_integrity": basic_integrity}
            )
        
        # Check for evaluation type (if present)
        evaluation_type = payload.get("evaluationType", "BASIC")
        if evaluation_type not in ["BASIC", "HARDWARE_BACKED"]:
            logger.warning(f"Unknown SafetyNet evaluation type: {evaluation_type}")
        
        return None  # Validation successful
    
    def is_configured(self) -> bool:
        """
        Check if validator is properly configured for production use.
        
        Returns:
            True if all required configuration is present
        """
        if self.android_config["stub_mode"]:
            return True
        
        return bool(self.android_config["safetynet_api_key"])
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """
        Get detailed configuration status.
        
        Returns:
            Dictionary with configuration status details
        """
        return {
            "validator_type": self.get_validator_type(),
            "platform": self.get_platform(),
            "stub_mode": self.android_config["stub_mode"],
            "configured": self.is_configured(),
            "has_api_key": bool(self.android_config["safetynet_api_key"]),
            "stub_allow_emulator": self.android_config["stub_allow_emulator"]
        }
