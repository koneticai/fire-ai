"""
Tests for Token Revocation List (RTL) enforcement.

This module tests the complete RTL implementation including:
- Token creation with jti claims
- RTL checking in authentication dependencies
- Token revocation endpoints
- End-to-end revocation enforcement
"""

import pytest
import time
import uuid
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from jose import jwt

from src.app.dependencies import (
    create_access_token,
    get_current_active_user,
    is_token_revoked,
    verify_token,
)
from src.app.schemas.token import TokenData
from src.app.schemas.auth import TokenPayload

# JWT constants for testing - these should match what dependencies.py uses internally
JWT_SECRET_KEY = "test-secret-key"
JWT_ALGORITHM = "HS256"


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
        """Test that revoked tokens are properly rejected via is_token_revoked."""
        # Create a valid token
        user_data = {
            "sub": "testuser",
            "user_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        token = create_access_token(user_data)

        # Extract jti from token
        decoded = jwt.get_unverified_claims(token)
        token_jti = decoded["jti"]

        # Mock async database session
        mock_db = AsyncMock()

        # Test 1: Token not revoked (query returns None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await is_token_revoked(mock_db, uuid.UUID(token_jti))
        assert result is False  # Not revoked

        # Test 2: Token revoked (query returns a row)
        mock_result_revoked = MagicMock()
        mock_result_revoked.scalar_one_or_none.return_value = MagicMock()  # Non-None = revoked
        mock_db.execute = AsyncMock(return_value=mock_result_revoked)

        result = await is_token_revoked(mock_db, uuid.UUID(token_jti))
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

        # Mock async database session
        mock_db = AsyncMock()

        # Test 1: Valid token, not revoked
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not revoked
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_current_active_user(credentials, mock_db)
        assert isinstance(result, TokenPayload)
        assert result.username == "testuser"
        assert str(result.user_id) == "550e8400-e29b-41d4-a716-446655440000"

        # Test 2: Valid token, but revoked (should raise HTTPException)
        mock_result_revoked = MagicMock()
        mock_result_revoked.scalar_one_or_none.return_value = MagicMock()  # Revoked
        mock_db.execute = AsyncMock(return_value=mock_result_revoked)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(credentials, mock_db)

        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail.lower()

    def _mock_settings(self, secret="test-secret"):
        """Create a mock settings object for verify_token tests."""
        mock = MagicMock()
        mock.jwt_secret_key = secret
        mock.algorithm = "HS256"
        return mock

    def test_token_validation_requires_all_claims(self):
        """Test that token validation requires all critical claims."""
        from fastapi import HTTPException

        secret = "test-secret"

        # Test token missing 'sub' claim
        incomplete_token_data = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600  # 1 hour from now (timezone-safe)
            # Missing 'sub'
        }

        incomplete_token = jwt.encode(incomplete_token_data, secret, algorithm="HS256")

        # Should raise HTTPException due to missing 'sub'
        with patch('src.app.dependencies.settings', self._mock_settings(secret)):
            with pytest.raises(HTTPException) as exc_info:
                verify_token(incomplete_token)

            assert exc_info.value.status_code == 401
            assert "missing required claims" in exc_info.value.detail.lower()

    def test_invalid_uuid_user_id_rejected(self):
        """Test that tokens with invalid UUID user_id are rejected."""
        from fastapi import HTTPException

        secret = "test-secret"

        # Token with invalid user_id format
        invalid_token_data = {
            "sub": "testuser",
            "user_id": "not-a-valid-uuid",  # Invalid UUID
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600  # 1 hour from now (timezone-safe)
        }

        invalid_token = jwt.encode(invalid_token_data, secret, algorithm="HS256")

        # Should raise HTTPException due to invalid UUID
        with patch('src.app.dependencies.settings', self._mock_settings(secret)):
            with pytest.raises(HTTPException) as exc_info:
                verify_token(invalid_token)

            assert exc_info.value.status_code == 401
            assert "malformed user_id" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rtl_database_error_handling(self):
        """Test RTL check handles database errors gracefully."""
        # Mock database session that raises on execute
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("Database connection failed"))

        # is_token_revoked should propagate the exception
        # (caller, get_current_active_user, catches it and returns 401)
        with pytest.raises(Exception, match="Database connection failed"):
            await is_token_revoked(mock_db, uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))

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

        # Create token with invalid user_id format
        invalid_token_data = {
            "sub": "testuser",
            "user_id": "not-a-valid-uuid",  # Invalid UUID
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600  # 1 hour from now (timezone-safe)
        }

        invalid_token = jwt.encode(invalid_token_data, "test-secret", algorithm="HS256")

        # Mock credentials
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = invalid_token

        # Mock async database session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not revoked
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Should raise HTTPException with 401 (not 500) due to invalid UUID
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(credentials, mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_active_user_with_valid_token(self):
        """Test that get_current_active_user succeeds with valid non-revoked token."""
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

        # Mock async database session - token not revoked
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not revoked
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_current_active_user(credentials, mock_db)
        assert isinstance(result, TokenPayload)
        assert result.username == "testuser"
