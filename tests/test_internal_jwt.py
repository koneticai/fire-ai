"""
Tests for Internal JWT functionality.

This module tests JWT token generation and validation for inter-service communication.
"""

import pytest
import os
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch

from src.app.internal_jwt import InternalJWTManager, get_internal_jwt_token


class TestInternalJWTManager:
    """Test cases for Internal JWT Manager."""
    
    def setup_method(self):
        """Set up test environment variables."""
        self.test_secret = "test_secret_key_for_internal_jwt"
        
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_jwt_manager_initialization(self):
        """Test JWT manager initialization with environment variable."""
        manager = InternalJWTManager()
        assert manager.secret_key == "test_secret_key_for_internal_jwt"
        assert manager.algorithm == "HS256"
        assert manager.expiration_minutes == 15
    
    def test_jwt_manager_missing_secret(self):
        """Test JWT manager initialization without secret key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                InternalJWTManager()
            assert "INTERNAL_JWT_SECRET_KEY environment variable is required" in str(exc_info.value)
    
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_token_generation(self):
        """Test JWT token generation."""
        manager = InternalJWTManager()
        token = manager.generate_token("fastapi", "user123")
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify structure
        decoded = jwt.decode(token, "test_secret_key_for_internal_jwt", algorithms=["HS256"], audience="go-service")
        assert decoded["iss"] == "fastapi"
        assert decoded["aud"] == "go-service"
        assert decoded["service"] == "fastapi"
        assert decoded["purpose"] == "internal_communication"
        assert decoded["user_id"] == "user123"
        assert "iat" in decoded
        assert "exp" in decoded
    
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_token_generation_without_user_id(self):
        """Test JWT token generation without user ID."""
        manager = InternalJWTManager()
        token = manager.generate_token("fastapi")
        
        decoded = jwt.decode(token, "test_secret_key_for_internal_jwt", algorithms=["HS256"], audience="go-service")
        assert decoded["iss"] == "fastapi"
        assert decoded["aud"] == "go-service"
        assert "user_id" not in decoded
    
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_token_validation_valid(self):
        """Test validation of valid JWT token."""
        manager = InternalJWTManager()
        token = manager.generate_token("fastapi", "user123")
        
        decoded = manager.validate_token(token)
        assert decoded["iss"] == "fastapi"
        assert decoded["user_id"] == "user123"
    
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_token_validation_invalid(self):
        """Test validation of invalid JWT token."""
        manager = InternalJWTManager()
        
        # Test with completely invalid token
        with pytest.raises(jwt.InvalidTokenError):
            manager.validate_token("invalid_token")
        
        # Test with token signed with different secret
        different_secret_token = jwt.encode(
            {"iss": "fastapi", "aud": "go-service"}, 
            "different_secret", 
            algorithm="HS256"
        )
        with pytest.raises(jwt.InvalidTokenError):
            manager.validate_token(different_secret_token)
    
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_token_expiration(self):
        """Test token expiration handling."""
        manager = InternalJWTManager()
        
        # Create an expired token
        expired_payload = {
            "iss": "fastapi",
            "aud": "go-service",
            "iat": int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
            "exp": int((datetime.utcnow() - timedelta(minutes=1)).timestamp()),
            "service": "fastapi",
            "purpose": "internal_communication"
        }
        expired_token = jwt.encode(expired_payload, self.test_secret, algorithm="HS256")
        
        with pytest.raises(jwt.ExpiredSignatureError):
            manager.validate_token(expired_token)
    
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_is_token_valid_method(self):
        """Test is_token_valid convenience method."""
        manager = InternalJWTManager()
        
        # Valid token
        valid_token = manager.generate_token("fastapi")
        assert manager.is_token_valid(valid_token) is True
        
        # Invalid token
        assert manager.is_token_valid("invalid_token") is False


class TestInternalJWTConvenienceFunction:
    """Test convenience function for JWT token generation."""
    
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_get_internal_jwt_token(self):
        """Test convenience function for getting JWT token."""
        token = get_internal_jwt_token("user456")
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token structure
        decoded = jwt.decode(token, "test_secret_key_for_internal_jwt", algorithms=["HS256"], audience="go-service")
        assert decoded["user_id"] == "user456"
        assert decoded["iss"] == "fastapi"
    
    @patch.dict(os.environ, {"INTERNAL_JWT_SECRET_KEY": "test_secret_key_for_internal_jwt"})
    def test_get_internal_jwt_token_without_user(self):
        """Test convenience function without user ID."""
        token = get_internal_jwt_token()
        
        decoded = jwt.decode(token, "test_secret_key_for_internal_jwt", algorithms=["HS256"], audience="go-service")
        assert "user_id" not in decoded
        assert decoded["iss"] == "fastapi"