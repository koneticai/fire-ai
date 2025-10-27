"""
SQLAlchemy models for C&E (Containment & Efficiency) Tests
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class CETestSession(Base):
    """
    SQLAlchemy model for C&E Test Sessions table
    
    Represents a containment and efficiency testing session for a specific building.
    Includes test configuration, results, and compliance scoring.
    """
    __tablename__ = 'ce_test_sessions'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Foreign relationships
    building_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('buildings.id'), 
        nullable=False,
        doc="Building being tested in this C&E session"
    )
    created_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=False,
        doc="User who created this test session"
    )
    
    # Session information
    session_name = Column(
        String(255), 
        nullable=False,
        doc="Descriptive name for the C&E testing session"
    )
    test_type = Column(
        String(100), 
        nullable=False, 
        default='containment_efficiency',
        server_default='containment_efficiency',
        doc="Type of C&E test being performed"
    )
    compliance_standard = Column(
        String(100), 
        nullable=False, 
        default='AS1851-2012',
        server_default='AS1851-2012',
        doc="Compliance standard being tested against"
    )
    status = Column(
        String(50), 
        nullable=False, 
        default='active',
        server_default='active',
        doc="Current status of the test session"
    )
    
    # Test data
    test_configuration = Column(
        JSONB, 
        nullable=False, 
        default={},
        server_default='{}',
        doc="Configuration parameters for the test"
    )
    test_results = Column(
        JSONB, 
        nullable=True,
        doc="Results and measurements from the test"
    )
    deviation_analysis = Column(
        JSONB, 
        nullable=True,
        doc="Analysis of deviations from expected values"
    )
    compliance_score = Column(
        Float, 
        nullable=True,
        doc="Overall compliance score (0-100)"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the test session was created"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the test session was last updated"
    )
    
    # Relationships
    building = relationship("Building", back_populates="ce_test_sessions", lazy='select')
    created_by_user = relationship("User", lazy='select', foreign_keys=[created_by])
    measurements = relationship(
        "CETestMeasurement", 
        back_populates="test_session",
        cascade="all, delete-orphan",
        lazy='select'
    )
    deviations = relationship(
        "CETestDeviation", 
        back_populates="test_session",
        cascade="all, delete-orphan",
        lazy='select'
    )
    reports = relationship(
        "CETestReport", 
        back_populates="test_session",
        cascade="all, delete-orphan",
        lazy='select'
    )
    
    def __repr__(self):
        return f"<CETestSession(id={self.id}, name='{self.session_name}', type='{self.test_type}')>"


class CETestMeasurement(Base):
    """
    SQLAlchemy model for C&E Test Measurements table
    
    Represents individual measurements taken during a C&E test session.
    """
    __tablename__ = 'ce_test_measurements'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Foreign relationships
    test_session_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('ce_test_sessions.id'), 
        nullable=False,
        doc="C&E test session this measurement belongs to"
    )
    
    # Measurement data
    measurement_type = Column(
        String(100), 
        nullable=False,
        doc="Type of measurement (pressure, velocity, temperature, etc.)"
    )
    location_id = Column(
        String(255), 
        nullable=False,
        doc="Zone, room, or specific location where measurement was taken"
    )
    measurement_value = Column(
        Float, 
        nullable=False,
        doc="The measured value"
    )
    unit = Column(
        String(20), 
        nullable=False,
        doc="Unit of measurement (Pa, m/s, °C, etc.)"
    )
    timestamp = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the measurement was taken"
    )
    measurement_metadata = Column(
        JSONB, 
        nullable=True, 
        default={},
        server_default='{}',
        doc="Additional metadata about the measurement"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the measurement record was created"
    )
    
    # Relationships
    test_session = relationship("CETestSession", back_populates="measurements", lazy='select')
    
    def __repr__(self):
        return f"<CETestMeasurement(id={self.id}, type='{self.measurement_type}', value={self.measurement_value})>"


class CETestDeviation(Base):
    """
    SQLAlchemy model for C&E Test Deviations table
    
    Represents deviations from expected values found during C&E testing.
    """
    __tablename__ = 'ce_test_deviations'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Foreign relationships
    test_session_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('ce_test_sessions.id'), 
        nullable=False,
        doc="C&E test session this deviation belongs to"
    )
    resolved_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=True,
        doc="User who resolved this deviation"
    )
    
    # Deviation data
    deviation_type = Column(
        String(100), 
        nullable=False,
        doc="Type of deviation (pressure_drop, velocity_exceeded, etc.)"
    )
    severity = Column(
        String(50), 
        nullable=False,
        doc="Severity level (minor, major, critical)"
    )
    location_id = Column(
        String(255), 
        nullable=False,
        doc="Location where the deviation was detected"
    )
    expected_value = Column(
        Float, 
        nullable=True,
        doc="Expected value according to standards"
    )
    actual_value = Column(
        Float, 
        nullable=False,
        doc="Actual measured value"
    )
    tolerance_percentage = Column(
        Float, 
        nullable=True,
        doc="Allowed tolerance percentage"
    )
    deviation_percentage = Column(
        Float, 
        nullable=False,
        doc="Percentage deviation from expected value"
    )
    description = Column(
        Text, 
        nullable=True,
        doc="Description of the deviation"
    )
    recommended_action = Column(
        Text, 
        nullable=True,
        doc="Recommended action to address the deviation"
    )
    
    # Resolution tracking
    is_resolved = Column(
        Boolean, 
        nullable=False, 
        default=False,
        server_default='false',
        doc="Whether this deviation has been resolved"
    )
    resolved_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When the deviation was resolved"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the deviation was recorded"
    )
    
    # Relationships
    test_session = relationship("CETestSession", back_populates="deviations", lazy='select')
    resolved_by_user = relationship("User", lazy='select', foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f"<CETestDeviation(id={self.id}, type='{self.deviation_type}', severity='{self.severity}')>"


class CETestReport(Base):
    """
    SQLAlchemy model for C&E Test Reports table
    
    Represents generated reports from C&E test sessions.
    """
    __tablename__ = 'ce_test_reports'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Foreign relationships
    test_session_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('ce_test_sessions.id'), 
        nullable=False,
        doc="C&E test session this report belongs to"
    )
    generated_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=False,
        doc="User who generated this report"
    )
    
    # Report data
    report_type = Column(
        String(100), 
        nullable=False, 
        default='compliance_report',
        server_default='compliance_report',
        doc="Type of report generated"
    )
    report_data = Column(
        JSONB, 
        nullable=False,
        doc="The report content and data"
    )
    is_final = Column(
        Boolean, 
        nullable=False, 
        default=False,
        server_default='false',
        doc="Whether this is the final report for the session"
    )
    
    # Finalization fields (AS 1851-2012 compliance)
    finalized = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default='false',
        doc="Whether this report has been finalized with engineer sign-off"
    )
    finalized_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the report was finalized"
    )
    finalized_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=True,
        doc="Engineer who finalized this report"
    )
    engineer_signature_s3_uri = Column(
        Text,
        nullable=True,
        doc="S3 URI of WORM-protected finalized report with signature"
    )
    engineer_license_number = Column(
        String(100),
        nullable=True,
        doc="License number of the finalizing engineer"
    )
    compliance_statement = Column(
        Text,
        nullable=True,
        doc="Compliance statement provided during finalization"
    )
    
    # Timestamps
    generated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the report was generated"
    )
    
    # Relationships
    test_session = relationship("CETestSession", back_populates="reports", lazy='select')
    
    def __repr__(self):
        return f"<CETestReport(id={self.id}, type='{self.report_type}', final={self.is_final})>"
