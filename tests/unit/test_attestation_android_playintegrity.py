"""
Unit tests for Android Play Integrity validator.
"""

import pytest
from unittest.mock import Mock, patch
import httpx
from datetime import datetime

from src.app.services.attestation.android_playintegrity import PlayIntegrityValidator
from src.app.services.attestation.config import AttestationConfig
from src.app.services.attestation.base import AttestationResultStatus


class TestPlayIntegrityValidator:
    """Test cases for PlayIntegrityValidator."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AttestationConfig(
            enabled=True,
            stub_mode=True,
            stub_allow_emulator=False,
            google_cloud_project_id="test-project",
            google_application_credentials="/test/path/credentials.json"
        )
    
    @pytest.fixture
    def validator(self, config):
        """Create PlayIntegrityValidator instance."""
        return PlayIntegrityValidator(config)
    
    def test_get_validator_type(self, validator):
        """Test validator type identification."""
        assert validator.get_validator_type() == "playintegrity"
    
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
        validator = PlayIntegrityValidator(config)
        
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
    
    @patch('src.app.services.attestation.android_playintegrity.httpx.Client')
    def test_validate_production_success(self, mock_client, config):
        """Test production validation with successful response."""
        # Configure for production mode
        config.stub_mode = False
        validator = PlayIntegrityValidator(config)
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tokenPayloadExternal": {
                "deviceIntegrity": {
                    "deviceRecognitionVariant": ["MEETS_DEVICE_INTEGRITY"]
                },
                "appIntegrity": {
                    "appRecognitionVariant": ["PLAY_RECOGNIZED"]
                },
                "requestDetails": {
                    "nonce": "test_nonce",
                    "requestHash": "test_hash"
                }
            }
        }
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Mock access token
        with patch.object(validator, '_get_google_access_token') as mock_token:
            mock_token.return_value = "test_access_token"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.VALID
            assert "play_integrity_response" in result.metadata
    
    @patch('src.app.services.attestation.android_playintegrity.httpx.Client')
    def test_validate_production_device_integrity_failed(self, mock_client, config):
        """Test production validation with device integrity failure."""
        # Configure for production mode
        config.stub_mode = False
        validator = PlayIntegrityValidator(config)
        
        # Mock API response with device integrity failure
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tokenPayloadExternal": {
                "deviceIntegrity": {
                    "deviceRecognitionVariant": ["UNKNOWN_DEVICE"]
                },
                "appIntegrity": {
                    "appRecognitionVariant": ["PLAY_RECOGNIZED"]
                }
            }
        }
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Mock access token
        with patch.object(validator, '_get_google_access_token') as mock_token:
            mock_token.return_value = "test_access_token"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "device integrity check failed" in result.error_message.lower()
    
    @patch('src.app.services.attestation.android_playintegrity.httpx.Client')
    def test_validate_production_app_integrity_failed(self, mock_client, config):
        """Test production validation with app integrity failure."""
        # Configure for production mode
        config.stub_mode = False
        validator = PlayIntegrityValidator(config)
        
        # Mock API response with app integrity failure
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tokenPayloadExternal": {
                "deviceIntegrity": {
                    "deviceRecognitionVariant": ["MEETS_DEVICE_INTEGRITY"]
                },
                "appIntegrity": {
                    "appRecognitionVariant": ["UNRECOGNIZED_VERSION"]
                }
            }
        }
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Mock access token
        with patch.object(validator, '_get_google_access_token') as mock_token:
            mock_token.return_value = "test_access_token"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.INVALID
            assert "app integrity check failed" in result.error_message.lower()
    
    @patch('src.app.services.attestation.android_playintegrity.httpx.Client')
    def test_validate_production_api_error(self, mock_client, config):
        """Test production validation with API error."""
        # Configure for production mode
        config.stub_mode = False
        validator = PlayIntegrityValidator(config)
        
        # Mock API response with error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Mock access token
        with patch.object(validator, '_get_google_access_token') as mock_token:
            mock_token.return_value = "test_access_token"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.ERROR
            assert "failed to decode" in result.error_message.lower()
    
    def test_validate_production_missing_config(self, config):
        """Test production validation with missing configuration."""
        # Configure for production mode but remove required config
        config.stub_mode = False
        config.google_cloud_project_id = None
        validator = PlayIntegrityValidator(config)
        
        result = validator.validate("production_token")
        
        assert result.status == AttestationResultStatus.ERROR
        assert "configuration incomplete" in result.error_message.lower()
    
    @patch('src.app.services.attestation.android_playintegrity.httpx.Client')
    def test_validate_production_access_token_failed(self, mock_client, config):
        """Test production validation with failed access token."""
        # Configure for production mode
        config.stub_mode = False
        validator = PlayIntegrityValidator(config)
        
        # Mock failed access token
        with patch.object(validator, '_get_google_access_token') as mock_token:
            mock_token.return_value = None
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.ERROR
            assert "failed to obtain google access token" in result.error_message.lower()
    
    @patch('src.app.services.attestation.android_playintegrity.httpx.Client')
    def test_validate_production_request_error(self, mock_client, config):
        """Test production validation with request error."""
        # Configure for production mode
        config.stub_mode = False
        validator = PlayIntegrityValidator(config)
        
        # Mock request error
        mock_client_instance = Mock()
        mock_client_instance.post.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Mock access token
        with patch.object(validator, '_get_google_access_token') as mock_token:
            mock_token.return_value = "test_access_token"
            
            result = validator.validate("production_token")
            
            assert result.status == AttestationResultStatus.ERROR
            assert "request failed" in result.error_message.lower()
    
    def test_check_device_integrity_valid(self, validator):
        """Test device integrity check with valid verdict."""
        device_integrity = {
            "deviceRecognitionVariant": ["MEETS_DEVICE_INTEGRITY"]
        }
        
        result = validator._check_device_integrity(device_integrity)
        assert result is True
    
    def test_check_device_integrity_invalid(self, validator):
        """Test device integrity check with invalid verdict."""
        device_integrity = {
            "deviceRecognitionVariant": ["UNKNOWN_DEVICE"]
        }
        
        result = validator._check_device_integrity(device_integrity)
        assert result is False
    
    def test_check_device_integrity_stub_mode(self, config):
        """Test device integrity check in stub mode (more lenient)."""
        config.stub_mode = True
        validator = PlayIntegrityValidator(config)
        
        device_integrity = {
            "deviceRecognitionVariant": ["UNKNOWN_DEVICE"]
        }
        
        result = validator._check_device_integrity(device_integrity)
        assert result is True
    
    def test_check_app_integrity_valid(self, validator):
        """Test app integrity check with valid verdict."""
        app_integrity = {
            "appRecognitionVariant": ["PLAY_RECOGNIZED"]
        }
        
        result = validator._check_app_integrity(app_integrity)
        assert result is True
    
    def test_check_app_integrity_invalid(self, validator):
        """Test app integrity check with invalid verdict."""
        app_integrity = {
            "appRecognitionVariant": ["UNRECOGNIZED_VERSION"]
        }
        
        result = validator._check_app_integrity(app_integrity)
        assert result is False
    
    def test_check_app_integrity_stub_mode(self, config):
        """Test app integrity check in stub mode (more lenient)."""
        config.stub_mode = True
        validator = PlayIntegrityValidator(config)
        
        app_integrity = {
            "appRecognitionVariant": ["UNRECOGNIZED_VERSION"]
        }
        
        result = validator._check_app_integrity(app_integrity)
        assert result is True
    
    def test_validate_decoded_token_missing_payload(self, validator):
        """Test decoded token validation with missing payload."""
        decoded_token = {}  # Missing tokenPayloadExternal
        
        result = validator._validate_decoded_token(decoded_token)
        
        assert result is not None
        assert result.status == AttestationResultStatus.INVALID
        assert "missing payload" in result.error_message.lower()
    
    def test_validate_request_details_with_nonce(self, validator):
        """Test request details validation with nonce."""
        request_details = {
            "nonce": "test_nonce",
            "requestHash": "test_hash"
        }
        
        result = validator._validate_request_details(request_details)
        assert result is None  # Should pass validation
    
    def test_get_google_access_token_mock(self, validator):
        """Test Google access token retrieval (mock implementation)."""
        token = validator._get_google_access_token()
        
        # Should return a mock token in test environment
        assert token is not None
        assert token == "mock_google_access_token"
    
    def test_is_configured_stub_mode(self, validator):
        """Test configuration check in stub mode."""
        assert validator.is_configured() is True
    
    def test_is_configured_production_mode(self, config):
        """Test configuration check in production mode."""
        config.stub_mode = False
        validator = PlayIntegrityValidator(config)
        
        assert validator.is_configured() is True
    
    def test_is_configured_missing_config(self, config):
        """Test configuration check with missing config."""
        config.stub_mode = False
        config.google_cloud_project_id = None
        validator = PlayIntegrityValidator(config)
        
        assert validator.is_configured() is False
    
    def test_get_configuration_status(self, validator):
        """Test configuration status reporting."""
        status = validator.get_configuration_status()
        
        assert status["validator_type"] == "playintegrity"
        assert status["platform"] == "android"
        assert status["stub_mode"] is True
        assert status["configured"] is True
        assert status["has_project_id"] is True
        assert status["has_credentials"] is True
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
        assert result.validator_type == "playintegrity"
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
        assert result.validator_type == "playintegrity"
        assert result.metadata["test"] == "value"
    
    def test_create_valid_result(self, validator):
        """Test valid result creation."""
        device_id = "test_device"
        metadata = {"test": "value"}
        
        result = validator._create_valid_result(device_id, metadata)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.device_id == device_id
        assert result.platform == "android"
        assert result.validator_type == "playintegrity"
        assert result.metadata["test"] == "value"
        assert result.is_valid is True
