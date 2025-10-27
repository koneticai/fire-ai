"""
Test suite for config.py security validators (Task 1.1)
Tests JWT secret strength validation and production stub mode blocking
"""

import pytest
import os
from pydantic import ValidationError


def test_jwt_secret_minimum_length():
    """JWT secret must be at least 32 characters"""
    from src.app.config import Settings
    
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            jwt_secret_key="short",
            internal_jwt_secret_key="x" * 32,
            database_url="postgresql://test"
        )
    
    error = str(exc_info.value)
    assert "at least 32 characters" in error
    assert "jwt_secret_key" in error


def test_internal_jwt_secret_minimum_length():
    """Internal JWT secret must be at least 32 characters"""
    from src.app.config import Settings
    
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            jwt_secret_key="x" * 32,
            internal_jwt_secret_key="short",
            database_url="postgresql://test"
        )
    
    error = str(exc_info.value)
    assert "at least 32 characters" in error
    assert "internal_jwt_secret_key" in error


def test_jwt_secret_weak_pattern():
    """JWT secret cannot contain common weak patterns"""
    from src.app.config import Settings
    
    weak_patterns = ["test" * 10, "secret" * 6, "password" * 5, "changeme" * 4]
    
    for weak_secret in weak_patterns:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                jwt_secret_key=weak_secret,  # Long enough but weak
                internal_jwt_secret_key="a" * 32,
                database_url="postgresql://test"
            )
        
        error = str(exc_info.value)
        assert "weak pattern" in error


def test_valid_jwt_secret():
    """Valid 32+ character secrets pass validation"""
    from src.app.config import Settings
    
    settings = Settings(
        jwt_secret_key="a" * 32,
        internal_jwt_secret_key="b" * 32,
        database_url="postgresql://test"
    )
    
    assert len(settings.jwt_secret_key) == 32
    assert len(settings.internal_jwt_secret_key) == 32


def test_valid_jwt_secret_with_special_chars():
    """Secrets with special characters and mixed case are valid"""
    from src.app.config import Settings
    
    settings = Settings(
        jwt_secret_key="Abc123!@#XyzDEF456$%^GHI789&*()_",  # 32 chars
        internal_jwt_secret_key="9f86d081884c7d659a2feaa0c55ad015",  # 32 chars
        database_url="postgresql://test"
    )
    
    assert settings.jwt_secret_key == "Abc123!@#XyzDEF456$%^GHI789&*()_"


def test_stub_mode_blocked_in_production(monkeypatch):
    """Stub mode must be blocked in production environment"""
    from src.app.config import Settings
    
    monkeypatch.setenv("ENVIRONMENT", "production")
    
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            jwt_secret_key="x" * 32,
            internal_jwt_secret_key="y" * 32,
            database_url="postgresql://test",
            attestation_stub_mode=True
        )
    
    error = str(exc_info.value)
    assert "FORBIDDEN in production" in error
    assert "attestation_stub_mode" in error


def test_stub_mode_allowed_in_development(monkeypatch):
    """Stub mode is allowed in development"""
    from src.app.config import Settings
    
    monkeypatch.setenv("ENVIRONMENT", "development")
    
    settings = Settings(
        jwt_secret_key="x" * 32,
        internal_jwt_secret_key="y" * 32,
        database_url="postgresql://test",
        attestation_stub_mode=True
    )
    
    assert settings.attestation_stub_mode is True


def test_stub_mode_allowed_when_false_in_production(monkeypatch):
    """Stub mode=False is allowed in production"""
    from src.app.config import Settings
    
    monkeypatch.setenv("ENVIRONMENT", "production")
    
    settings = Settings(
        jwt_secret_key="x" * 32,
        internal_jwt_secret_key="y" * 32,
        database_url="postgresql://test",
        attestation_stub_mode=False
    )
    
    assert settings.attestation_stub_mode is False


def test_stub_mode_default_value():
    """Test default value of attestation_stub_mode"""
    from src.app.config import Settings
    
    settings = Settings(
        jwt_secret_key="x" * 32,
        internal_jwt_secret_key="y" * 32,
        database_url="postgresql://test"
    )
    
    # Default is True (per current config)
    assert settings.attestation_stub_mode is True


def test_environment_defaults_to_development():
    """When ENVIRONMENT not set, defaults to development (allows stub mode)"""
    from src.app.config import Settings
    import os
    
    # Ensure ENVIRONMENT is not set
    if 'ENVIRONMENT' in os.environ:
        del os.environ['ENVIRONMENT']
    
    settings = Settings(
        jwt_secret_key="x" * 32,
        internal_jwt_secret_key="y" * 32,
        database_url="postgresql://test",
        attestation_stub_mode=True
    )
    
    assert settings.attestation_stub_mode is True
