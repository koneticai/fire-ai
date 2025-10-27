"""
Calibration certificate model per AS 1851-2012 requirements.
All measurement instruments must have valid calibration certificates.
"""

from sqlalchemy import Column, String, Date, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import date
from ..database.core import Base
import uuid


class CalibrationCertificate(Base):
    """
    Calibration certificate for measurement instruments.
    
    AS 1851-2012 requires all instruments have valid calibration.
    Instruments with expired certificates are blocked from use.
    """
    __tablename__ = "calibration_certificates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id = Column(String(100), unique=True, nullable=False, index=True)
    instrument_type = Column(String(50), nullable=False)
    cert_number = Column(String(100), nullable=False)
    calibrated_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    cert_file_path = Column(Text, nullable=True)
    calibration_lab = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationship
    creator = relationship("User", foreign_keys=[created_by])
    
    @property
    def is_expired(self) -> bool:
        """Check if certificate is expired"""
        return date.today() > self.expiry_date
    
    @property
    def days_until_expiry(self) -> int:
        """Calculate days until expiry (negative if expired)"""
        return (self.expiry_date - date.today()).days
    
    def __repr__(self):
        return f"<CalibrationCertificate(instrument_id={self.instrument_id}, type={self.instrument_type}, expires={self.expiry_date})>"
