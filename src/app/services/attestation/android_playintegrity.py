"""
Android Play Integrity validator for device attestation.

Validates Play Integrity tokens from Google's Play Integrity API to ensure
requests are coming from legitimate, unmodified Android devices.
"""

import json
import logging
from typing import Optional, Dict, Any
import httpx
import base64
from datetime import datetime

from .base import AttestationValidator, AttestationResult, AttestationResultStatus
from .config import AttestationConfig

logger = logging.getLogger(__name__)


class PlayIntegrityValidator(AttestationValidator):
    """
    Validator for Android Play Integrity tokens.
    
    Validates tokens using Google's Play Integrity API to verify device and app integrity.
    Supports both production validation and stub mode for testing.
    """
    
    PLAY_INTEGRITY_API_URL = "https://playintegrity.googleapis.com/v1/projects/{project_id}:decodeIntegrityToken"
    
    def __init__(self, config: AttestationConfig):
        super().__init__(config)
        self.android_config = config.get_android_config()
        
    def get_validator_type(self) -> str:
        return "playintegrity"
    
    def get_platform(self) -> str:
        return "android"
    
    def validate(self, token: str, device_id: Optional[str] = None, 
                metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate a Play Integrity token.
        
        Args:
            token: The Play Integrity token to validate
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
            error_msg = f"Play Integrity validation error: {str(e)}"
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
        Validate token using Google's Play Integrity API.
        
        Args:
            token: The Play Integrity token
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status
        """
        # Validate configuration
        if not all([self.android_config["project_id"], self.android_config["credentials_path"]]):
            return self._create_error_result(
                "Play Integrity configuration incomplete - missing Google credentials",
                device_id,
                metadata
            )
        
        try:
            # Get access token for Google API
            access_token = self._get_google_access_token()
            if not access_token:
                return self._create_error_result(
                    "Failed to obtain Google access token",
                    device_id,
                    metadata
                )
            
            # Decode the integrity token
            decoded_token = self._decode_integrity_token(token, access_token)
            if not decoded_token:
                return self._create_error_result(
                    "Failed to decode Play Integrity token",
                    device_id,
                    metadata
                )
            
            # Validate the decoded token
            validation_result = self._validate_decoded_token(decoded_token, device_id, metadata)
            if validation_result:
                return validation_result
            
            # All validations passed
            return self._create_valid_result(
                device_id,
                {**(metadata or {}), "play_integrity_response": decoded_token}
            )
            
        except httpx.RequestError as e:
            return self._create_error_result(f"Play Integrity API request failed: {str(e)}", device_id, metadata)
        except Exception as e:
            return self._create_error_result(f"Play Integrity validation failed: {str(e)}", device_id, metadata)
    
    def _get_google_access_token(self) -> Optional[str]:
        """
        Get Google access token for API authentication.
        
        Returns:
            Access token string or None if failed
        """
        # In a real implementation, this would use Google's OAuth2 flow
        # For now, we'll return a mock token for testing
        logger.warning("Using mock Google access token for testing")
        return "mock_google_access_token"
    
    def _decode_integrity_token(self, token: str, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Decode Play Integrity token using Google API.
        
        Args:
            token: The Play Integrity token
            access_token: Google access token
            
        Returns:
            Decoded token data or None if failed
        """
        url = self.PLAY_INTEGRITY_API_URL.format(project_id=self.android_config["project_id"])
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "integrityToken": token
        }
        
        try:
            with httpx.Client(timeout=self.config.api_timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Play Integrity API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to decode Play Integrity token: {str(e)}")
            return None
    
    def _validate_decoded_token(self, decoded_token: Dict[str, Any], 
                              device_id: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> Optional[AttestationResult]:
        """
        Validate decoded Play Integrity token.
        
        Args:
            decoded_token: Decoded token data from Google API
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult if validation fails, None if successful
        """
        # Check for required fields
        if "tokenPayloadExternal" not in decoded_token:
            return self._create_invalid_result(
                "Play Integrity token missing payload",
                device_id,
                metadata
            )
        
        payload = decoded_token["tokenPayloadExternal"]
        
        # Validate device integrity
        device_integrity = payload.get("deviceIntegrity", {})
        if not self._check_device_integrity(device_integrity):
            return self._create_invalid_result(
                f"Device integrity check failed: {device_integrity}",
                device_id,
                {**(metadata or {}), "device_integrity": device_integrity}
            )
        
        # Validate app integrity
        app_integrity = payload.get("appIntegrity", {})
        if not self._check_app_integrity(app_integrity):
            return self._create_invalid_result(
                f"App integrity check failed: {app_integrity}",
                device_id,
                {**(metadata or {}), "app_integrity": app_integrity}
            )
        
        # Validate request details (if present)
        request_details = payload.get("requestDetails", {})
        if request_details:
            validation_result = self._validate_request_details(request_details, device_id, metadata)
            if validation_result:
                return validation_result
        
        return None  # Validation successful
    
    def _check_device_integrity(self, device_integrity: Dict[str, Any]) -> bool:
        """
        Check device integrity verdict.
        
        Args:
            device_integrity: Device integrity data from token
            
        Returns:
            True if device integrity is acceptable
        """
        # Check for MEETS_DEVICE_INTEGRITY verdict
        device_recognition_variant = device_integrity.get("deviceRecognitionVariant", [])
        
        # Accept if MEETS_DEVICE_INTEGRITY is present
        if "MEETS_DEVICE_INTEGRITY" in device_recognition_variant:
            return True
        
        # In stub mode, be more lenient
        if self.android_config["stub_mode"]:
            return True
        
        # Reject if no valid verdict
        return False
    
    def _check_app_integrity(self, app_integrity: Dict[str, Any]) -> bool:
        """
        Check app integrity verdict.
        
        Args:
            app_integrity: App integrity data from token
            
        Returns:
            True if app integrity is acceptable
        """
        # Check for PLAY_RECOGNIZED verdict (app is licensed and not tampered)
        app_recognition_variant = app_integrity.get("appRecognitionVariant", [])
        
        # Accept if PLAY_RECOGNIZED is present
        if "PLAY_RECOGNIZED" in app_recognition_variant:
            return True
        
        # In stub mode, be more lenient
        if self.android_config["stub_mode"]:
            return True
        
        # Reject if no valid verdict
        return False
    
    def _validate_request_details(self, request_details: Dict[str, Any],
                                device_id: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> Optional[AttestationResult]:
        """
        Validate request details from token.
        
        Args:
            request_details: Request details from token
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult if validation fails, None if successful
        """
        # Check nonce if present
        nonce = request_details.get("nonce")
        if nonce:
            # In a real implementation, we'd verify the nonce matches what we sent
            logger.debug(f"Play Integrity token contains nonce: {nonce}")
        
        # Check request hash if present
        request_hash = request_details.get("requestHash")
        if request_hash:
            # In a real implementation, we'd verify the request hash
            logger.debug(f"Play Integrity token contains request hash: {request_hash}")
        
        return None  # Validation successful
    
    def is_configured(self) -> bool:
        """
        Check if validator is properly configured for production use.
        
        Returns:
            True if all required configuration is present
        """
        if self.android_config["stub_mode"]:
            return True
        
        return all([
            self.android_config["project_id"],
            self.android_config["credentials_path"]
        ])
    
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
            "has_project_id": bool(self.android_config["project_id"]),
            "has_credentials": bool(self.android_config["credentials_path"]),
            "stub_allow_emulator": self.android_config["stub_allow_emulator"]
        }
