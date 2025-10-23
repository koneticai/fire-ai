"""
Unit tests for iOS App Attest validator.
"""

import pytest
from unittest.mock import Mock, patch
import jwt
from datetime import datetime, timedelta

from src.app.services.attestation.ios_appattest import AppAttestValidator
from src.app.services.attestation.config import AttestationConfig
from src.app.services.attestation.base import AttestationResultStatus


class TestAppAttestValidator:
    """Test cases for AppAttestValidator."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AttestationConfig(
            enabled=True,
            stub_mode=True,
            stub_allow_emulator=False,
            app_attest_app_id="com.test.app"
        )
    
    @pytest.fixture
    def validator(self, config):
        """Create AppAttestValidator instance."""
        return AppAttestValidator(config)
    
    def test_get_validator_type(self, validator):
        """Test validator type identification."""
        assert validator.get_validator_type() == "appattest"
    
    def test_get_platform(self, validator):
        """Test platform identification."""
        assert validator.get_platform() == "ios"
    
    def test_validate_stub_mode_emulator_rejected(self, validator):
        """Test stub mode rejects emulator assertions."""
        result = validator.validate("emulator")
        
        assert result.status == AttestationResultStatus.INVALID
        assert "emulator" in result.error_message.lower()
        assert result.metadata["stub_mode"] is True
        assert result.metadata["reason"] == "emulator_rejected"
    
    def test_validate_stub_mode_emulator_allowed(self, config):
        """Test stub mode allows emulator when configured."""
        config.stub_allow_emulator = True
        validator = AppAttestValidator(config)
        
        result = validator.validate("emulator")
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["stub_mode"] is True
        assert result.metadata["reason"] == "stub_accepted"
    
    def test_validate_stub_mode_valid_assertion(self, validator):
        """Test stub mode accepts valid assertions."""
        result = validator.validate("valid_assertion_123")
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["stub_mode"] is True
        assert result.metadata["reason"] == "stub_accepted"
    
    def test_validate_stub_mode_with_device_id(self, validator):
        """Test stub mode with device ID."""
        device_id = "test_device_123"
        result = validator.validate("valid_assertion", device_id=device_id)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.device_id == device_id
    
    def test_validate_stub_mode_with_metadata(self, validator):
        """Test stub mode with metadata."""
        metadata = {"test_key": "test_value"}
        result = validator.validate("valid_assertion", metadata=metadata)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["test_key"] == "test_value"
        assert result.metadata["stub_mode"] is True
    
    @patch('src.app.services.attestation.ios_appattest.jwt.get_unverified_header')
    @patch('src.app.services.attestation.ios_appattest.jwt.decode')
    def test_validate_production_success(self, mock_jwt_decode, mock_jwt_header, config):
        """Test production validation with successful assertion."""
        # Configure for production mode
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        # Mock JWT header
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        
        # Mock JWT decode
        mock_jwt_decode.return_value = {
            "iss": "com.test.app",
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(minutes=10)).timestamp()),
            "challenge": "test_challenge"
        }
        
        # Mock public key retrieval
        with patch.object(validator, '_get_apple_public_key') as mock_get_key:
            mock_get_key.return_value = Mock()  # Mock public key
            
            result = validator.validate("production_assertion")
            
            assert result.status == AttestationResultStatus.VALID
            assert result.metadata["app_id"] == "com.test.app"
            assert result.metadata["key_id"] == "test_key_id"
    
    @patch('src.app.services.attestation.ios_appattest.jwt.get_unverified_header')
    def test_validate_production_missing_key_id(self, mock_jwt_header, config):
        """Test production validation with missing key ID."""
        # Configure for production mode
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        # Mock JWT header without key ID
        mock_jwt_header.return_value = {}
        
        result = validator.validate("production_assertion")
        
        assert result.status == AttestationResultStatus.INVALID
        assert "missing key id" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_appattest.jwt.get_unverified_header')
    def test_validate_production_failed_key_retrieval(self, mock_jwt_header, config):
        """Test production validation with failed key retrieval."""
        # Configure for production mode
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        # Mock JWT header
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        
        # Mock failed key retrieval
        with patch.object(validator, '_get_apple_public_key') as mock_get_key:
            mock_get_key.return_value = None
            
            result = validator.validate("production_assertion")
            
            assert result.status == AttestationResultStatus.ERROR
            assert "failed to retrieve apple public key" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_appattest.jwt.get_unverified_header')
    @patch('src.app.services.attestation.ios_appattest.jwt.decode')
    def test_validate_production_expired_assertion(self, mock_jwt_decode, mock_jwt_header, config):
        """Test production validation with expired assertion."""
        # Configure for production mode
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        # Mock JWT header
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        
        # Mock JWT decode with expired token
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError("Token has expired")
        
        # Mock public key retrieval
        with patch.object(validator, '_get_apple_public_key') as mock_get_key:
            mock_get_key.return_value = Mock()
            
            result = validator.validate("production_assertion")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "expired" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_appattest.jwt.get_unverified_header')
    @patch('src.app.services.attestation.ios_appattest.jwt.decode')
    def test_validate_production_invalid_token(self, mock_jwt_decode, mock_jwt_header, config):
        """Test production validation with invalid token."""
        # Configure for production mode
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        # Mock JWT header
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        
        # Mock JWT decode with invalid token
        mock_jwt_decode.side_effect = jwt.InvalidTokenError("Invalid token")
        
        # Mock public key retrieval
        with patch.object(validator, '_get_apple_public_key') as mock_get_key:
            mock_get_key.return_value = Mock()
            
            result = validator.validate("production_assertion")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "invalid" in result.error_message.lower()
    
    def test_validate_production_missing_config(self, config):
        """Test production validation with missing configuration."""
        # Configure for production mode but remove required config
        config.stub_mode = False
        config.app_attest_app_id = None
        validator = AppAttestValidator(config)
        
        result = validator.validate("production_assertion")
        
        assert result.status == AttestationResultStatus.ERROR
        assert "configuration incomplete" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_appattest.jwt.get_unverified_header')
    @patch('src.app.services.attestation.ios_appattest.jwt.decode')
    def test_validate_assertion_payload_missing_field(self, mock_jwt_decode, mock_jwt_header, config):
        """Test assertion payload validation with missing required field."""
        # Configure for production mode
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        # Mock JWT header
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        
        # Mock JWT decode with missing field
        mock_jwt_decode.return_value = {
            "iss": "com.test.app",
            "iat": int(datetime.utcnow().timestamp()),
            # Missing "exp" field
        }
        
        # Mock public key retrieval
        with patch.object(validator, '_get_apple_public_key') as mock_get_key:
            mock_get_key.return_value = Mock()
            
            result = validator.validate("production_assertion")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "missing required field" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_appattest.jwt.get_unverified_header')
    @patch('src.app.services.attestation.ios_appattest.jwt.decode')
    def test_validate_assertion_payload_wrong_app_id(self, mock_jwt_decode, mock_jwt_header, config):
        """Test assertion payload validation with wrong app ID."""
        # Configure for production mode
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        # Mock JWT header
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        
        # Mock JWT decode with wrong app ID
        mock_jwt_decode.return_value = {
            "iss": "com.wrong.app",  # Wrong app ID
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(minutes=10)).timestamp())
        }
        
        # Mock public key retrieval
        with patch.object(validator, '_get_apple_public_key') as mock_get_key:
            mock_get_key.return_value = Mock()
            
            result = validator.validate("production_assertion")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "app id mismatch" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_appattest.jwt.get_unverified_header')
    @patch('src.app.services.attestation.ios_appattest.jwt.decode')
    def test_validate_assertion_payload_old_timestamp(self, mock_jwt_decode, mock_jwt_header, config):
        """Test assertion payload validation with old timestamp."""
        # Configure for production mode
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        # Mock JWT header
        mock_jwt_header.return_value = {"kid": "test_key_id"}
        
        # Mock JWT decode with old timestamp
        old_time = datetime.utcnow() - timedelta(hours=2)
        mock_jwt_decode.return_value = {
            "iss": "com.test.app",
            "iat": int(old_time.timestamp()),
            "exp": int((old_time + timedelta(minutes=10)).timestamp())
        }
        
        # Mock public key retrieval
        with patch.object(validator, '_get_apple_public_key') as mock_get_key:
            mock_get_key.return_value = Mock()
            
            result = validator.validate("production_assertion")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "too old" in result.error_message.lower()
    
    def test_get_apple_public_key_mock(self, validator):
        """Test Apple public key retrieval (mock implementation)."""
        key = validator._get_apple_public_key("test_key_id")
        
        # Should return a mock key in test environment
        assert key is not None
    
    def test_is_configured_stub_mode(self, validator):
        """Test configuration check in stub mode."""
        assert validator.is_configured() is True
    
    def test_is_configured_production_mode(self, config):
        """Test configuration check in production mode."""
        config.stub_mode = False
        validator = AppAttestValidator(config)
        
        assert validator.is_configured() is True
    
    def test_is_configured_missing_config(self, config):
        """Test configuration check with missing config."""
        config.stub_mode = False
        config.app_attest_app_id = None
        validator = AppAttestValidator(config)
        
        assert validator.is_configured() is False
    
    def test_get_configuration_status(self, validator):
        """Test configuration status reporting."""
        status = validator.get_configuration_status()
        
        assert status["validator_type"] == "appattest"
        assert status["platform"] == "ios"
        assert status["stub_mode"] is True
        assert status["configured"] is True
        assert status["has_app_id"] is True
        assert status["stub_allow_emulator"] is False
    
    def test_calculate_token_hash(self, validator):
        """Test token hash calculation."""
        assertion = "test_assertion_123"
        hash1 = validator._calculate_token_hash(assertion)
        hash2 = validator._calculate_token_hash(assertion)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
        assert hash1 != assertion  # Should be hashed
    
    def test_create_error_result(self, validator):
        """Test error result creation."""
        error_msg = "Test error message"
        device_id = "test_device"
        metadata = {"test": "value"}
        
        result = validator._create_error_result(error_msg, device_id, metadata)
        
        assert result.status == AttestationResultStatus.ERROR
        assert result.error_message == error_msg
        assert result.device_id == device_id
        assert result.platform == "ios"
        assert result.validator_type == "appattest"
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
        assert result.platform == "ios"
        assert result.validator_type == "appattest"
        assert result.metadata["test"] == "value"
    
    def test_create_valid_result(self, validator):
        """Test valid result creation."""
        device_id = "test_device"
        metadata = {"test": "value"}
        
        result = validator._create_valid_result(device_id, metadata)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.device_id == device_id
        assert result.platform == "ios"
        assert result.validator_type == "appattest"
        assert result.metadata["test"] == "value"
        assert result.is_valid is True
