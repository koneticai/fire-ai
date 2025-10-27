"""
Calibration certificate validation service.
Implements AS 1851-2012 calibration requirements.

All measurement instruments must have valid calibration certificates
before measurements can be recorded.
"""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.calibration import CalibrationCertificate
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class CalibrationValidator:
    """
    Validates instrument calibration before allowing measurements.
    
    Ensures compliance with AS 1851-2012 calibration requirements:
    - All instruments must have calibration certificates
    - Certificates must not be expired
    - Warning issued for certificates expiring soon (< 30 days)
    """
    
    @staticmethod
    async def validate_instrument(
        instrument_id: str,
        db: AsyncSession
    ) -> CalibrationCertificate:
        """
        Validate that instrument has valid calibration certificate.
        
        Args:
            instrument_id: Unique instrument identifier
            db: Database session
        
        Returns:
            CalibrationCertificate if valid
        
        Raises:
            HTTPException 422: If instrument not calibrated or certificate expired
        """
        # Get certificate
        result = await db.execute(
            select(CalibrationCertificate)
            .where(CalibrationCertificate.instrument_id == instrument_id)
        )
        cert = result.scalar_one_or_none()
        
        # Check certificate exists
        if not cert:
            logger.error(f"No calibration certificate for instrument: {instrument_id}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "FIRE-422-NO-CALIBRATION",
                    "message": f"Instrument {instrument_id} has no calibration certificate",
                    "instrument_id": instrument_id,
                    "requirement": "AS 1851-2012 requires all instruments have valid calibration"
                }
            )
        
        # Check not expired
        if cert.is_expired:
            logger.error(
                f"Expired calibration: {instrument_id} "
                f"(expired {cert.expiry_date})"
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "FIRE-422-EXPIRED-CALIBRATION",
                    "message": f"Calibration certificate expired on {cert.expiry_date}",
                    "instrument_id": instrument_id,
                    "cert_number": cert.cert_number,
                    "expiry_date": cert.expiry_date.isoformat(),
                    "days_expired": abs(cert.days_until_expiry),
                    "requirement": "AS 1851-2012 requires valid calibration certificates"
                }
            )
        
        # Warn if expiring soon (< 30 days)
        if 0 < cert.days_until_expiry < 30:
            logger.warning(
                f"Calibration expiring soon: {instrument_id} "
                f"({cert.days_until_expiry} days remaining, expires {cert.expiry_date})"
            )
        
        logger.debug(f"Calibration valid for {instrument_id}: {cert.cert_number}")
        return cert


# Singleton instance
calibration_validator = CalibrationValidator()
