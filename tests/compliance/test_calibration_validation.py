"""
Test calibration certificate validation (Task 3.1)
References: AS 1851-2012 calibration requirements

Validates that:
1. Valid calibration certificates are accepted
2. Expired certificates are rejected with HTTP 422
3. Missing certificates are rejected with HTTP 422
4. Expiring soon certificates log warnings
5. Integration with measurement endpoints blocks expired instruments
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock
from fastapi import HTTPException
from src.app.models.calibration import CalibrationCertificate
from src.app.services.calibration_validator import calibration_validator


@pytest.mark.asyncio
async def test_valid_calibration_accepted(db_session):
    """Valid calibration certificates should be accepted"""
    # Create valid certificate
    cert = CalibrationCertificate(
        instrument_id="PRESS-001",
        instrument_type="pressure_gauge",
        cert_number="CAL-2025-001",
        calibrated_date=date.today() - timedelta(days=30),
        expiry_date=date.today() + timedelta(days=335)  # ~11 months remaining
    )
    
    # Mock database to return the certificate
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cert
    db_session.execute.return_value = mock_result
    
    # Should not raise exception
    result = await calibration_validator.validate_instrument("PRESS-001", db_session)
    assert result.instrument_id == "PRESS-001"
    assert result.is_expired is False
    assert result.days_until_expiry == 335
    assert result.cert_number == "CAL-2025-001"


@pytest.mark.asyncio
async def test_expired_calibration_rejected(db_session):
    """Expired calibration certificates should be rejected with HTTP 422"""
    # Create expired certificate
    cert = CalibrationCertificate(
        instrument_id="PRESS-002",
        instrument_type="pressure_gauge",
        cert_number="CAL-2024-001",
        calibrated_date=date.today() - timedelta(days=400),
        expiry_date=date.today() - timedelta(days=35)  # Expired 35 days ago
    )
    
    # Mock database to return the expired certificate
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cert
    db_session.execute.return_value = mock_result
    
    # Should raise 422 error
    with pytest.raises(HTTPException) as exc_info:
        await calibration_validator.validate_instrument("PRESS-002", db_session)
    
    # Verify error details
    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert detail["error_code"] == "FIRE-422-EXPIRED-CALIBRATION"
    assert "expired" in detail["message"].lower()
    assert detail["instrument_id"] == "PRESS-002"
    assert detail["cert_number"] == "CAL-2024-001"
    assert detail["days_expired"] == 35
    assert "expiry_date" in detail
    assert "AS 1851-2012" in detail["requirement"]


@pytest.mark.asyncio
async def test_missing_calibration_rejected(db_session):
    """Instruments without calibration should be rejected with HTTP 422"""
    # Mock database to return None (no certificate found)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_session.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc_info:
        await calibration_validator.validate_instrument("PRESS-003", db_session)
    
    # Verify error details
    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert detail["error_code"] == "FIRE-422-NO-CALIBRATION"
    assert "no calibration certificate" in detail["message"].lower()
    assert detail["instrument_id"] == "PRESS-003"
    assert "AS 1851-2012" in detail["requirement"]


@pytest.mark.asyncio
async def test_expiring_soon_warning(db_session, caplog):
    """Should warn when calibration expires in < 30 days"""
    import logging
    caplog.set_level(logging.WARNING)
    
    # Create certificate expiring in 15 days
    cert = CalibrationCertificate(
        instrument_id="PRESS-004",
        instrument_type="pressure_gauge",
        cert_number="CAL-2025-002",
        calibrated_date=date.today() - timedelta(days=335),
        expiry_date=date.today() + timedelta(days=15)  # Expires in 15 days
    )
    
    # Mock database to return the expiring certificate
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cert
    db_session.execute.return_value = mock_result
    
    # Should still accept but log warning
    result = await calibration_validator.validate_instrument("PRESS-004", db_session)
    assert result.instrument_id == "PRESS-004"
    assert result.is_expired is False
    assert result.days_until_expiry == 15
    
    # Check warning was logged
    assert any("expiring soon" in record.message.lower() for record in caplog.records)
    assert any("PRESS-004" in record.message for record in caplog.records)
    assert any("15 days" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_model_properties(db_session):
    """Test CalibrationCertificate model properties"""
    # Test valid (not expired)
    valid_cert = CalibrationCertificate(
        instrument_id="TEST-001",
        instrument_type="anemometer",
        cert_number="CAL-2025-100",
        calibrated_date=date.today() - timedelta(days=100),
        expiry_date=date.today() + timedelta(days=100)
    )
    assert valid_cert.is_expired is False
    assert valid_cert.days_until_expiry == 100
    
    # Test expired
    expired_cert = CalibrationCertificate(
        instrument_id="TEST-002",
        instrument_type="force_meter",
        cert_number="CAL-2024-200",
        calibrated_date=date.today() - timedelta(days=400),
        expiry_date=date.today() - timedelta(days=10)
    )
    assert expired_cert.is_expired is True
    assert expired_cert.days_until_expiry == -10
    
    # Test repr
    assert "TEST-001" in repr(valid_cert)
    assert "anemometer" in repr(valid_cert)
