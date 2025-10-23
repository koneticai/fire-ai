"""
iOS DeviceCheck validator for device attestation.

Validates DeviceCheck tokens from Apple's DeviceCheck API to ensure
requests are coming from legitimate iOS devices.
"""

import json
import logging
from typing import Optional, Dict, Any
import httpx
import jwt
from datetime import datetime, timedelta

from .base import AttestationValidator, AttestationResult, AttestationResultStatus
from .config import AttestationConfig

logger = logging.getLogger(__name__)


class DeviceCheckValidator(AttestationValidator):
    """
    Validator for iOS DeviceCheck tokens.
    
    Validates tokens using Apple's DeviceCheck API to verify device legitimacy.
    Supports both production validation and stub mode for testing.
    """
    
    DEVICECHECK_API_URL = "https://api.development.devicecheck.apple.com/v1/validate_device_token"
    DEVICECHECK_PROD_URL = "https://api.devicecheck.apple.com/v1/validate_device_token"
    
    def __init__(self, config: AttestationConfig):
        super().__init__(config)
        self.ios_config = config.get_ios_config()
        
    def get_validator_type(self) -> str:
        return "devicecheck"
    
    def get_platform(self) -> str:
        return "ios"
    
    def validate(self, token: str, device_id: Optional[str] = None, 
                metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate a DeviceCheck token.
        
        Args:
            token: The DeviceCheck token to validate
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status
        """
        token_hash = self._calculate_token_hash(token)
        self._log_validation_attempt(token_hash, device_id)
        
        try:
            # Check if running in stub mode
            if self.ios_config["stub_mode"]:
                result = self._validate_stub_mode(token, device_id, metadata)
            else:
                result = self._validate_production(token, device_id, metadata)
            
            self._log_validation_result(result, token_hash)
            return result
            
        except Exception as e:
            error_msg = f"DeviceCheck validation error: {str(e)}"
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
        if token == "emulator" and not self.ios_config["stub_allow_emulator"]:
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
        Validate token using Apple's DeviceCheck API.
        
        Args:
            token: The DeviceCheck token
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status
        """
        # Validate configuration
        if not all([self.ios_config["team_id"], self.ios_config["key_id"], 
                   self.ios_config["private_key_path"]]):
            return self._create_error_result(
                "DeviceCheck configuration incomplete - missing Apple credentials",
                device_id,
                metadata
            )
        
        try:
            # Create JWT for Apple API authentication
            jwt_token = self._create_apple_jwt()
            
            # Prepare request payload
            payload = {
                "device_token": token,
                "transaction_id": f"firemode_{datetime.utcnow().timestamp()}",
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            }
            
            # Make request to Apple DeviceCheck API
            response = self._make_devicecheck_request(jwt_token, payload)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Check if device is valid
                if response_data.get("bit0") == 0 and response_data.get("bit1") == 0:
                    return self._create_valid_result(
                        device_id,
                        {**(metadata or {}), "apple_response": response_data}
                    )
                else:
                    return self._create_invalid_result(
                        f"DeviceCheck validation failed - bits: {response_data}",
                        device_id,
                        {**(metadata or {}), "apple_response": response_data}
                    )
            else:
                error_msg = f"DeviceCheck API error: {response.status_code} - {response.text}"
                return self._create_error_result(error_msg, device_id, metadata)
                
        except httpx.RequestError as e:
            return self._create_error_result(f"DeviceCheck API request failed: {str(e)}", device_id, metadata)
        except Exception as e:
            return self._create_error_result(f"DeviceCheck validation failed: {str(e)}", device_id, metadata)
    
    def _create_apple_jwt(self) -> str:
        """
        Create JWT token for Apple DeviceCheck API authentication.
        
        Returns:
            JWT token string
        """
        # Load private key
        try:
            with open(self.ios_config["private_key_path"], 'r') as f:
                private_key = f.read()
        except FileNotFoundError:
            raise ValueError(f"Apple private key file not found: {self.ios_config['private_key_path']}")
        except Exception as e:
            raise ValueError(f"Failed to read Apple private key: {str(e)}")
        
        # Create JWT payload
        now = datetime.utcnow()
        payload = {
            "iss": self.ios_config["team_id"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp())
        }
        
        # Create JWT token
        try:
            token = jwt.encode(
                payload,
                private_key,
                algorithm="ES256",
                headers={"kid": self.ios_config["key_id"]}
            )
            return token
        except Exception as e:
            raise ValueError(f"Failed to create Apple JWT: {str(e)}")
    
    def _make_devicecheck_request(self, jwt_token: str, payload: dict) -> httpx.Response:
        """
        Make HTTP request to Apple DeviceCheck API.
        
        Args:
            jwt_token: JWT token for authentication
            payload: Request payload
            
        Returns:
            HTTP response
        """
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        # Use production URL if not in development mode
        url = self.DEVICECHECK_PROD_URL
        if self.config.stub_mode:  # Use development URL in stub mode
            url = self.DEVICECHECK_API_URL
        
        # Make request with timeout
        with httpx.Client(timeout=self.config.api_timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            return response
    
    def is_configured(self) -> bool:
        """
        Check if validator is properly configured for production use.
        
        Returns:
            True if all required configuration is present
        """
        if self.ios_config["stub_mode"]:
            return True
        
        return all([
            self.ios_config["team_id"],
            self.ios_config["key_id"],
            self.ios_config["private_key_path"]
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
            "stub_mode": self.ios_config["stub_mode"],
            "configured": self.is_configured(),
            "has_team_id": bool(self.ios_config["team_id"]),
            "has_key_id": bool(self.ios_config["key_id"]),
            "has_private_key": bool(self.ios_config["private_key_path"]),
            "stub_allow_emulator": self.ios_config["stub_allow_emulator"]
        }
