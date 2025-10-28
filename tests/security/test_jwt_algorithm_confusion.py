"""
Test JWT algorithm confusion attack prevention (Task 1.2).

Validates that only HS256 tokens signed with the configured secret are accepted and
that altered algorithm headers or invalid signatures are rejected.
"""

import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession


TEST_SECRET = "a" * 32
INTERNAL_SECRET = "b" * 32

os.environ.setdefault("DATABASE_URL", "postgresql://test")
os.environ["JWT_SECRET_KEY"] = TEST_SECRET
os.environ["INTERNAL_JWT_SECRET_KEY"] = INTERNAL_SECRET

from src.app.dependencies import get_current_active_user, verify_token


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _standard_payload(hours: int = 1) -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    return {
        "sub": "testuser",
        "user_id": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "exp": int(expires_at.timestamp()),
    }


@pytest.fixture(autouse=True)
def configure_settings(monkeypatch):
    from src.app import dependencies
    from src.app.config import Settings

    test_settings = Settings(
        jwt_secret_key=TEST_SECRET,
        internal_jwt_secret_key=INTERNAL_SECRET,
        database_url="postgresql://test"
    )
    monkeypatch.setattr(dependencies, "settings", test_settings)
    return test_settings


@pytest.fixture
def async_db():
    db_session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db_session.execute.return_value = result
    return db_session


def test_reject_none_algorithm():
    """Tokens with alg=none must be rejected."""
    header = {"alg": "none", "typ": "JWT"}
    payload = _standard_payload()

    token = ".".join([
        _base64url_encode(json.dumps(header, separators=(",", ":")).encode()),
        _base64url_encode(json.dumps(payload, separators=(",", ":")).encode()),
        ""
    ])

    with pytest.raises(HTTPException) as exc_info:
        verify_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


def test_reject_rs256_algorithm():
    """Tokens declaring RS256 must be rejected when only HS256 is allowed."""
    payload = _standard_payload()
    valid_token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    _, payload_segment, signature_segment = valid_token.split(".")

    malicious_header = {"alg": "RS256", "typ": "JWT"}
    altered_token = ".".join([
        _base64url_encode(json.dumps(malicious_header, separators=(",", ":")).encode()),
        payload_segment,
        signature_segment,
    ])

    with pytest.raises(HTTPException) as exc_info:
        verify_token(altered_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_accept_valid_hs256_token(async_db):
    """Valid HS256 tokens should be accepted and return token payload."""
    payload = _standard_payload()
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    token_data = await get_current_active_user(credentials, async_db)

    assert token_data.username == "testuser"
    assert str(token_data.user_id) == payload["user_id"]
    assert str(token_data.jti) == payload["jti"]


@pytest.mark.asyncio
async def test_verify_signature_enforced(async_db):
    """Tokens signed with the wrong secret must be rejected."""
    payload = _standard_payload()
    invalid_token = jwt.encode(payload, "wrong-secret-key" * 2, algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=invalid_token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(credentials, async_db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


def test_expired_token_rejected():
    """Expired tokens must be rejected."""
    payload = _standard_payload(hours=-1)
    expired_token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        verify_token(expired_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token expired"
