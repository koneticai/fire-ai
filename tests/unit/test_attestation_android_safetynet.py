"""
Unit tests for Android SafetyNet validator.
"""

import pytest
from unittest.mock import Mock, patch
import jwt
from datetime import datetime, timedelta

from src.app.services.attestation.android_safetynet import SafetyNetValidator
from src.app.services.attestation.config import AttestationConfig
from src.app.services.attestation.base import AttestationResultStatus


class TestSafetyNetValidator:
    """Test cases for SafetyNetValidator."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AttestationConfig(
            enabled=True,
            stub_mode=True,
            stub_allow_emulator=False,
            safetynet_api_key="test_api_key_123"
        )
    
    @pytest.fixture
    def validator(self, config):
        """Create SafetyNetValidator instance."""
        return SafetyNetValidator(config)
    
    def test_get_validator_type(self, validator):
        """Test validator type identification."""
        assert validator.get_validator_type() == "safetynet"
    
    def test_get_platform(self, validator):
        """Test platform identification."""
        assert validator.get_platform() == "android"
    
    def test_validate_stub_mode_emulator_rejected(self, validator):
        """Test stub mode rejects emulator tokens."""
        result = validator.validate("emulator")
        
        assert result.status == AttestationResultStatus.INVALID
        assert "emulator" in result.error_message.lower()
        assert result.metadata["stub_mode"] is True
        assert result.metadata["reason"] == "emulator_rejected"
    
    def test_validate_stub_mode_emulator_allowed(self, config):
        """Test stub mode allows emulator when configured."""
        config.stub_allow_emulator = True
        validator = SafetyNetValidator(config)
        
        result = validator.validate("emulator")
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["stub_mode"] is True
        assert result.metadata["reason"] == "stub_accepted"
    
    def test_validate_stub_mode_valid_token(self, validator):
        """Test stub mode accepts valid tokens."""
        result = validator.validate("valid_token_123")
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["stub_mode"] is True
        assert result.metadata["reason"] == "stub_accepted"
    
    def test_validate_stub_mode_with_device_id(self, validator):
        """Test stub mode with device ID."""
        device_id = "test_device_123"
        result = validator.validate("valid_token", device_id=device_id)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.device_id == device_id
    
    def test_validate_stub_mode_with_metadata(self, validator):
        """Test stub mode with metadata."""
        metadata = {"test_key": "test_value"}
        result = validator.validate("valid_token", metadata=metadata)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["test_key"] == "test_value"
        assert result.metadata["stub_mode"] is True
    
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_header')
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_claims')
    @patch('src.app.services.attestation.android_safetynet.jwt.decode')
    def test_validate_production_success(self, mock_jwt_decode, mock_jwt_claims, mock_jwt_header, config):
        """Test production validation with successful response."""
        # Configure for production mode
        config.stub_mode = False
        validator = SafetyNetValidator(config)
        
        # Mock JWT header and claims
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        mock_jwt_claims.return_value = {"iss": "google"}
        
        # Mock JWT decode with valid payload
        current_time = datetime.utcnow()
        mock_jwt_decode.return_value = {
            "nonce": "test_nonce",
            "timestampMs": int(current_time.timestamp() * 1000),
            "apkPackageName": "com.test.app",
            "ctsProfileMatch": True,
            "basicIntegrity": True,
            "evaluationType": "BASIC"
        }
        
        # Mock public key retrieval
        with patch.object(validator, '_get_google_public_key') as mock_get_key:
            mock_get_key.return_value = "mock_public_key"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.VALID
            assert "safetynet_payload" in result.metadata
    
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_header')
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_claims')
    @patch('src.app.services.attestation.android_safetynet.jwt.decode')
    def test_validate_production_cts_profile_failed(self, mock_jwt_decode, mock_jwt_claims, mock_jwt_header, config):
        """Test production validation with CTS profile failure."""
        # Configure for production mode
        config.stub_mode = False
        validator = SafetyNetValidator(config)
        
        # Mock JWT header and claims
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        mock_jwt_claims.return_value = {"iss": "google"}
        
        # Mock JWT decode with CTS profile failure
        current_time = datetime.utcnow()
        mock_jwt_decode.return_value = {
            "nonce": "test_nonce",
            "timestampMs": int(current_time.timestamp() * 1000),
            "apkPackageName": "com.test.app",
            "ctsProfileMatch": False,  # CTS profile failed
            "basicIntegrity": True,
            "evaluationType": "BASIC"
        }
        
        # Mock public key retrieval
        with patch.object(validator, '_get_google_public_key') as mock_get_key:
            mock_get_key.return_value = "mock_public_key"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "cts profile match failed" in result.error_message.lower()
    
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_header')
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_claims')
    @patch('src.app.services.attestation.android_safetynet.jwt.decode')
    def test_validate_production_basic_integrity_failed(self, mock_jwt_decode, mock_jwt_claims, mock_jwt_header, config):
        """Test production validation with basic integrity failure."""
        # Configure for production mode
        config.stub_mode = False
        validator = SafetyNetValidator(config)
        
        # Mock JWT header and claims
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        mock_jwt_claims.return_value = {"iss": "google"}
        
        # Mock JWT decode with basic integrity failure
        current_time = datetime.utcnow()
        mock_jwt_decode.return_value = {
            "nonce": "test_nonce",
            "timestampMs": int(current_time.timestamp() * 1000),
            "apkPackageName": "com.test.app",
            "ctsProfileMatch": True,
            "basicIntegrity": False,  # Basic integrity failed
            "evaluationType": "BASIC"
        }
        
        # Mock public key retrieval
        with patch.object(validator, '_get_google_public_key') as mock_get_key:
            mock_get_key.return_value = "mock_public_key"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "basic integrity check failed" in result.error_message.lower()
    
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_header')
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_claims')
    @patch('src.app.services.attestation.android_safetynet.jwt.decode')
    def test_validate_production_expired_token(self, mock_jwt_decode, mock_jwt_claims, mock_jwt_header, config):
        """Test production validation with expired token."""
        # Configure for production mode
        config.stub_mode = False
        validator = SafetyNetValidator(config)
        
        # Mock JWT header and claims
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        mock_jwt_claims.return_value = {"iss": "google"}
        
        # Mock JWT decode with expired token
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError("Token has expired")
        
        # Mock public key retrieval
        with patch.object(validator, '_get_google_public_key') as mock_get_key:
            mock_get_key.return_value = "mock_public_key"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "signature verification failed" in result.error_message.lower()
    
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_header')
    @patch('src.app.services.attestation.android_safetynet.jwt.get_unverified_claims')
    def test_validate_production_failed_key_retrieval(self, mock_jwt_claims, mock_jwt_header, config):
        """Test production validation with failed key retrieval."""
        # Configure for production mode
        config.stub_mode = False
        validator = SafetyNetValidator(config)
        
        # Mock JWT header and claims
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        mock_jwt_claims.return_value = {"iss": "google"}
        
        # Mock failed key retrieval
        with patch.object(validator, '_get_google_public_key') as mock_get_key:
            mock_get_key.return_value = None
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "signature verification failed" in result.error_message.lower()
    
    def test_validate_production_missing_config(self, config):
        """Test production validation with missing configuration."""
        # Configure for production mode but remove required config
        config.stub_mode = False
        config.safetynet_api_key = None
        validator = SafetyNetValidator(config)
        
        result = validator.validate("production_token")
        
        assert result.status == AttestationResultStatus.ERROR
        assert "configuration incomplete" in result.error_message.lower()
    
    def test_validate_safetynet_payload_missing_field(self, validator):
        """Test SafetyNet payload validation with missing required field."""
        payload = {
            "nonce": "test_nonce",
            "timestampMs": int(datetime.utcnow().timestamp() * 1000),
            "apkPackageName": "com.test.app",
            "ctsProfileMatch": True,
            # Missing "basicIntegrity" field
        }
        
        result = validator._validate_safetynet_payload(payload)
        
        assert result is not None
        assert result.status == AttestationResultStatus.INVALID
        assert "missing required field" in result.error_message.lower()
    
    def test_validate_safetynet_payload_nonce_mismatch(self, validator):
        """Test SafetyNet payload validation with nonce mismatch."""
        payload = {
            "nonce": "wrong_nonce",
            "timestampMs": int(datetime.utcnow().timestamp() * 1000),
            "apkPackageName": "com.test.app",
            "ctsProfileMatch": True,
            "basicIntegrity": True
        }
        
        metadata = {"expected_nonce": "correct_nonce"}
        
        result = validator._validate_safetynet_payload(payload, metadata=metadata)
        
        assert result is not None
        assert result.status == AttestationResultStatus.INVALID
        assert "nonce mismatch" in result.error_message.lower()
    
    def test_validate_safetynet_payload_old_timestamp(self, validator):
        """Test SafetyNet payload validation with old timestamp."""
        old_time = datetime.utcnow() - timedelta(hours=2)
        payload = {
            "nonce": "test_nonce",
            "timestampMs": int(old_time.timestamp() * 1000),
            "apkPackageName": "com.test.app",
            "ctsProfileMatch": True,
            "basicIntegrity": True
        }
        
        result = validator._validate_safetynet_payload(payload)
        
        assert result is not None
        assert result.status == AttestationResultStatus.INVALID
        assert "too old" in result.error_message.lower()
    
    def test_validate_safetynet_payload_valid(self, validator):
        """Test SafetyNet payload validation with valid payload."""
        current_time = datetime.utcnow()
        payload = {
            "nonce": "test_nonce",
            "timestampMs": int(current_time.timestamp() * 1000),
            "apkPackageName": "com.test.app",
            "ctsProfileMatch": True,
            "basicIntegrity": True,
            "evaluationType": "BASIC"
        }
        
        result = validator._validate_safetynet_payload(payload)
        
        assert result is None  # Should pass validation
    
    def test_get_google_public_key_mock(self, validator):
        """Test Google public key retrieval (mock implementation)."""
        key = validator._get_google_public_key("test_key_id")
        
        # Should return a mock key in test environment
        assert key is not None
        assert key == "mock_google_public_key"
    
    def test_is_configured_stub_mode(self, validator):
        """Test configuration check in stub mode."""
        assert validator.is_configured() is True
    
    def test_is_configured_production_mode(self, config):
        """Test configuration check in production mode."""
        config.stub_mode = False
        validator = SafetyNetValidator(config)
        
        assert validator.is_configured() is True
    
    def test_is_configured_missing_config(self, config):
        """Test configuration check with missing config."""
        config.stub_mode = False
        config.safetynet_api_key = None
        validator = SafetyNetValidator(config)
        
        assert validator.is_configured() is False
    
    def test_get_configuration_status(self, validator):
        """Test configuration status reporting."""
        status = validator.get_configuration_status()
        
        assert status["validator_type"] == "safetynet"
        assert status["platform"] == "android"
        assert status["stub_mode"] is True
        assert status["configured"] is True
        assert status["has_api_key"] is True
        assert status["stub_allow_emulator"] is False
    
    def test_calculate_token_hash(self, validator):
        """Test token hash calculation."""
        token = "test_token_123"
        hash1 = validator._calculate_token_hash(token)
        hash2 = validator._calculate_token_hash(token)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
        assert hash1 != token  # Should be hashed
    
    def test_create_error_result(self, validator):
        """Test error result creation."""
        error_msg = "Test error message"
        device_id = "test_device"
        metadata = {"test": "value"}
        
        result = validator._create_error_result(error_msg, device_id, metadata)
        
        assert result.status == AttestationResultStatus.ERROR
        assert result.error_message == error_msg
        assert result.device_id == device_id
        assert result.platform == "android"
        assert result.validator_type == "safetynet"
        assert result.metadata["test"] == "value"
    
    def test_create_invalid_result(self, validator):
        """Test invalid result creation."""
        reason = "Test invalid reason"
        device_id = "test_device"
        metadata = {"test": "value"}
        
        result = validator._create_invalid_result(reason, device_id, metadata)
        
        assert result.status == AttestationResultStatus.INVALID
        assert result.error_message == reason
        assert result.device_id == device_id
        assert result.platform == "android"
        assert result.validator_type == "safetynet"
        assert result.metadata["test"] == "value"
    
    def test_create_valid_result(self, validator):
        """Test valid result creation."""
        device_id = "test_device"
        metadata = {"test": "value"}
        
        result = validator._create_valid_result(device_id, metadata)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.device_id == device_id
        assert result.platform == "android"
        assert result.validator_type == "safetynet"
        assert result.metadata["test"] == "value"
        assert result.is_valid is True
