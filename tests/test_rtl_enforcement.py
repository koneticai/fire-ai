"""
Tests for Token Revocation List (RTL) enforcement.

This module tests the complete RTL implementation including:
- Token creation with jti claims
- RTL checking in authentication dependencies
- Token revocation endpoints
- End-to-end revocation enforcement
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt

from src.app.dependencies import (
    create_access_token, 
    get_current_active_user, 
    check_token_revocation,
    JWT_SECRET_KEY,
    JWT_ALGORITHM
)
from src.app.models import TokenData


class TestRTLEnforcement:
    """Test cases for RTL enforcement and security."""
    
    def test_token_creation_includes_jti(self):
        """Test that created tokens include jti for revocation tracking."""
        user_data = {
            "sub": "testuser",
            "user_id": "550e8400-e29b-41d4-a716-446655440000"  # Valid UUID
        }
        
        token = create_access_token(user_data)
        
        # Decode token without verification to check structure
        decoded = jwt.get_unverified_claims(token)
        
        # Verify jti is present and valid
        assert "jti" in decoded
        assert isinstance(decoded["jti"], str)
        assert len(decoded["jti"]) > 0
        
        # Verify jti is a valid UUID format
        try:
            uuid.UUID(decoded["jti"])
        except ValueError:
            pytest.fail("jti should be a valid UUID")
    
    @pytest.mark.asyncio
    async def test_rtl_check_prevents_access(self):
        """Test that revoked tokens are properly rejected."""
        # Create a valid token
        user_data = {
            "sub": "testuser", 
            "user_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        token = create_access_token(user_data)
        
        # Extract jti from token
        decoded = jwt.get_unverified_claims(token)
        token_jti = decoded["jti"]
        
        # Mock database connection and RTL check
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test 1: Token not revoked (should succeed)
        mock_cursor.fetchone.return_value = [0]  # Not revoked
        
        with patch('src.app.dependencies.get_database_connection', return_value=mock_conn):
            result = check_token_revocation(token_jti, mock_conn)
            assert result is False  # Not revoked
        
        # Test 2: Token revoked (should be detected)
        mock_cursor.fetchone.return_value = [1]  # Revoked
        
        with patch('src.app.dependencies.get_database_connection', return_value=mock_conn):
            result = check_token_revocation(token_jti, mock_conn)
            assert result is True  # Revoked
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_rtl_integration(self):
        """Test that get_current_active_user properly checks RTL."""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create token with valid UUID user_id
        user_data = {
            "sub": "testuser",
            "user_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        token = create_access_token(user_data)
        
        # Mock credentials
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = token
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test 1: Valid token, not revoked
        mock_cursor.fetchone.return_value = [0]  # Not revoked
        
        with patch('src.app.dependencies.get_database_connection', return_value=mock_conn):
            with patch('src.app.dependencies.JWT_SECRET_KEY', 'test-secret-key'):
                result = await get_current_active_user(credentials)
                assert isinstance(result, TokenData)
                assert result.username == "testuser"
                assert str(result.user_id) == "550e8400-e29b-41d4-a716-446655440000"
        
        # Test 2: Valid token, but revoked (should raise HTTPException)
        mock_cursor.fetchone.return_value = [1]  # Revoked
        
        with patch('src.app.dependencies.get_database_connection', return_value=mock_conn):
            with patch('src.app.dependencies.JWT_SECRET_KEY', 'test-secret-key'):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_active_user(credentials)
                
                assert exc_info.value.status_code == 401
                assert "revoked" in exc_info.value.detail.lower()
    
    def test_token_validation_requires_all_claims(self):
        """Test that token validation requires all critical claims."""
        from fastapi import HTTPException
        from jose import jwt
        
        # Test token missing 'sub' claim
        incomplete_token_data = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "jti": str(uuid.uuid4()),
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
            # Missing 'sub'
        }
        
        incomplete_token = jwt.encode(incomplete_token_data, "test-secret", algorithm="HS256")
        
        # Mock credentials
        credentials = Mock()
        credentials.credentials = incomplete_token
        
        # Should raise HTTPException due to missing 'sub'
        with patch('src.app.dependencies.JWT_SECRET_KEY', 'test-secret'):
            with pytest.raises(HTTPException) as exc_info:
                # This would be called within get_current_active_user
                from src.app.dependencies import verify_token
                verify_token(incomplete_token)
            
            assert exc_info.value.status_code == 401
            assert "missing required claims" in exc_info.value.detail.lower()
    
    def test_invalid_uuid_user_id_rejected(self):
        """Test that tokens with invalid UUID user_id are rejected."""
        from fastapi import HTTPException
        from jose import jwt
        
        # Token with invalid user_id format
        invalid_token_data = {
            "sub": "testuser",
            "user_id": "not-a-valid-uuid",  # Invalid UUID
            "jti": str(uuid.uuid4()),
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        invalid_token = jwt.encode(invalid_token_data, "test-secret", algorithm="HS256")
        
        # Should raise HTTPException due to invalid UUID
        with patch('src.app.dependencies.JWT_SECRET_KEY', 'test-secret'):
            with pytest.raises(HTTPException) as exc_info:
                from src.app.dependencies import verify_token
                verify_token(invalid_token)
            
            assert exc_info.value.status_code == 401
            assert "malformed user_id" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_rtl_database_error_handling(self):
        """Test RTL check handles database errors gracefully."""
        # Mock database connection that raises an exception
        mock_conn = Mock()
        mock_conn.cursor.side_effect = Exception("Database connection failed")
        
        # Should return True (revoked) when database check fails (fail-safe)
        result = check_token_revocation("test-jti", mock_conn)
        assert result is True  # Fail-safe: treat as revoked when can't check
    
    def test_jti_uniqueness(self):
        """Test that each token gets a unique jti."""
        user_data = {
            "sub": "testuser",
            "user_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        
        # Create multiple tokens
        token1 = create_access_token(user_data)
        token2 = create_access_token(user_data)
        
        # Decode to get jtis
        decoded1 = jwt.get_unverified_claims(token1)
        decoded2 = jwt.get_unverified_claims(token2)
        
        # jtis should be different even for same user
        assert decoded1["jti"] != decoded2["jti"]
        
        # Both should be valid UUIDs
        uuid.UUID(decoded1["jti"])
        uuid.UUID(decoded2["jti"])
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_handles_invalid_uuid_correctly(self):
        """Test that get_current_active_user returns 401 (not 500) on malformed user_id."""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        from jose import jwt
        
        # Create token with invalid user_id format
        invalid_token_data = {
            "sub": "testuser",
            "user_id": "not-a-valid-uuid",  # Invalid UUID
            "jti": str(uuid.uuid4()),
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        invalid_token = jwt.encode(invalid_token_data, "test-secret", algorithm="HS256")
        
        # Mock credentials
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = invalid_token
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [0]  # Not revoked
        
        # Should raise HTTPException with 401 (not 500) due to invalid UUID
        with patch('src.app.dependencies.JWT_SECRET_KEY', 'test-secret'):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_active_user(credentials, mock_conn)
            
            assert exc_info.value.status_code == 401
            assert "token validation failed" in exc_info.value.detail.lower()
        
        # Verify database connection was closed
        mock_conn.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_closes_db_connection(self):
        """Test that get_current_active_user properly closes database connections."""
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create valid token
        user_data = {
            "sub": "testuser",
            "user_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        token = create_access_token(user_data)
        
        # Mock credentials
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = token
        
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [0]  # Not revoked
        
        # Should succeed and close connection
        with patch('src.app.dependencies.JWT_SECRET_KEY', 'test-secret'):
            result = await get_current_active_user(credentials, mock_conn)
            assert isinstance(result, TokenData)
        
        # Verify database connection was closed
        mock_conn.close.assert_called_once()