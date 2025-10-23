"""
Unit tests for iOS DeviceCheck validator.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import httpx
from datetime import datetime, timedelta

from src.app.services.attestation.ios_devicecheck import DeviceCheckValidator
from src.app.services.attestation.config import AttestationConfig
from src.app.services.attestation.base import AttestationResultStatus


class TestDeviceCheckValidator:
    """Test cases for DeviceCheckValidator."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AttestationConfig(
            enabled=True,
            stub_mode=True,
            stub_allow_emulator=False,
            apple_team_id="TEST_TEAM_ID",
            apple_key_id="TEST_KEY_ID",
            apple_private_key_path="/test/path/key.p8"
        )
    
    @pytest.fixture
    def validator(self, config):
        """Create DeviceCheckValidator instance."""
        return DeviceCheckValidator(config)
    
    def test_get_validator_type(self, validator):
        """Test validator type identification."""
        assert validator.get_validator_type() == "devicecheck"
    
    def test_get_platform(self, validator):
        """Test platform identification."""
        assert validator.get_platform() == "ios"
    
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
        validator = DeviceCheckValidator(config)
        
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
    
    @patch('src.app.services.attestation.ios_devicecheck.open', new_callable=mock_open)
    @patch('src.app.services.attestation.ios_devicecheck.jwt.encode')
    @patch('src.app.services.attestation.ios_devicecheck.httpx.Client')
    def test_validate_production_success(self, mock_client, mock_jwt_encode, mock_file, config):
        """Test production validation with successful response."""
        # Configure for production mode
        config.stub_mode = False
        validator = DeviceCheckValidator(config)
        
        # Mock file read
        mock_file.return_value.read.return_value = "test_private_key"
        
        # Mock JWT encoding
        mock_jwt_encode.return_value = "test_jwt_token"
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bit0": 0, "bit1": 0}
        mock_response.text = "OK"
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        result = validator.validate("production_token")
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["apple_response"]["bit0"] == 0
        assert result.metadata["apple_response"]["bit1"] == 0
    
    @patch('src.app.services.attestation.ios_devicecheck.open', new_callable=mock_open)
    @patch('src.app.services.attestation.ios_devicecheck.jwt.encode')
    @patch('src.app.services.attestation.ios_devicecheck.httpx.Client')
    def test_validate_production_device_invalid(self, mock_client, mock_jwt_encode, mock_file, config):
        """Test production validation with invalid device response."""
        # Configure for production mode
        config.stub_mode = False
        validator = DeviceCheckValidator(config)
        
        # Mock file read
        mock_file.return_value.read.return_value = "test_private_key"
        
        # Mock JWT encoding
        mock_jwt_encode.return_value = "test_jwt_token"
        
        # Mock HTTP response with invalid device
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bit0": 1, "bit1": 0}
        mock_response.text = "OK"
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        result = validator.validate("production_token")
        
        assert result.status == AttestationResultStatus.INVALID
        assert "validation failed" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_devicecheck.open', new_callable=mock_open)
    @patch('src.app.services.attestation.ios_devicecheck.jwt.encode')
    @patch('src.app.services.attestation.ios_devicecheck.httpx.Client')
    def test_validate_production_api_error(self, mock_client, mock_jwt_encode, mock_file, config):
        """Test production validation with API error."""
        # Configure for production mode
        config.stub_mode = False
        validator = DeviceCheckValidator(config)
        
        # Mock file read
        mock_file.return_value.read.return_value = "test_private_key"
        
        # Mock JWT encoding
        mock_jwt_encode.return_value = "test_jwt_token"
        
        # Mock HTTP response with error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        result = validator.validate("production_token")
        
        assert result.status == AttestationResultStatus.ERROR
        assert "api error" in result.error_message.lower()
        assert "400" in result.error_message
    
    def test_validate_production_missing_config(self, config):
        """Test production validation with missing configuration."""
        # Configure for production mode but remove required config
        config.stub_mode = False
        config.apple_team_id = None
        validator = DeviceCheckValidator(config)
        
        result = validator.validate("production_token")
        
        assert result.status == AttestationResultStatus.ERROR
        assert "configuration incomplete" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_devicecheck.open', side_effect=FileNotFoundError)
    def test_validate_production_missing_key_file(self, mock_file, config):
        """Test production validation with missing private key file."""
        # Configure for production mode
        config.stub_mode = False
        validator = DeviceCheckValidator(config)
        
        result = validator.validate("production_token")
        
        assert result.status == AttestationResultStatus.ERROR
        assert "private key file not found" in result.error_message.lower()
    
    @patch('src.app.services.attestation.ios_devicecheck.httpx.Client')
    def test_validate_production_request_error(self, mock_client, config):
        """Test production validation with request error."""
        # Configure for production mode
        config.stub_mode = False
        validator = DeviceCheckValidator(config)
        
        # Mock request error
        mock_client_instance = Mock()
        mock_client_instance.post.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        result = validator.validate("production_token")
        
        assert result.status == AttestationResultStatus.ERROR
        assert "private key file not found" in result.error_message.lower()
    
    def test_is_configured_stub_mode(self, validator):
        """Test configuration check in stub mode."""
        assert validator.is_configured() is True
    
    def test_is_configured_production_mode(self, config):
        """Test configuration check in production mode."""
        config.stub_mode = False
        validator = DeviceCheckValidator(config)
        
        assert validator.is_configured() is True
    
    def test_is_configured_missing_config(self, config):
        """Test configuration check with missing config."""
        config.stub_mode = False
        config.apple_team_id = None
        validator = DeviceCheckValidator(config)
        
        assert validator.is_configured() is False
    
    def test_get_configuration_status(self, validator):
        """Test configuration status reporting."""
        status = validator.get_configuration_status()
        
        assert status["validator_type"] == "devicecheck"
        assert status["platform"] == "ios"
        assert status["stub_mode"] is True
        assert status["configured"] is True
        assert status["has_team_id"] is True
        assert status["has_key_id"] is True
        assert status["has_private_key"] is True
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
        assert result.platform == "ios"
        assert result.validator_type == "devicecheck"
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
        assert result.validator_type == "devicecheck"
        assert result.metadata["test"] == "value"
    
    def test_create_valid_result(self, validator):
        """Test valid result creation."""
        device_id = "test_device"
        metadata = {"test": "value"}
        
        result = validator._create_valid_result(device_id, metadata)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.device_id == device_id
        assert result.platform == "ios"
        assert result.validator_type == "devicecheck"
        assert result.metadata["test"] == "value"
        assert result.is_valid is True
