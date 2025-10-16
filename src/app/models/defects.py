"""
SQLAlchemy model for Defects
"""

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class Defect(Base):
    """
    SQLAlchemy model for Defects table
    
    Represents defects discovered during fire safety testing inspections.
    Each defect has an independent lifecycle from discovery to closure.
    """
    __tablename__ = 'defects'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Core relationships
    test_session_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('test_sessions.id', ondelete='CASCADE'), 
        nullable=False,
        doc="Test session (inspection) where defect was discovered"
    )
    building_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('buildings.id', ondelete='CASCADE'), 
        nullable=False,
        doc="Building where defect was found"
    )
    asset_id = Column(
        UUID(as_uuid=True), 
        nullable=True,
        doc="Optional - specific equipment that has the defect"
    )
    
    # Classification (AS1851 aligned)
    severity = Column(
        String(20), 
        nullable=False,
        doc="Defect severity: critical, high, medium, low"
    )
    category = Column(
        String(50), 
        nullable=True,
        doc="Defect category: e.g., extinguisher_pressure, hose_reel_leak"
    )
    description = Column(
        Text, 
        nullable=False,
        doc="Detailed description of the defect"
    )
    as1851_rule_code = Column(
        String(20), 
        nullable=True,
        doc="AS1851 rule code: e.g., FE-01, HR-03"
    )
    
    # Status workflow
    status = Column(
        String(20), 
        nullable=False, 
        default='open',
        doc="Defect status: open, acknowledged, repair_scheduled, repaired, verified, closed"
    )
    
    # Timestamps
    discovered_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        doc="When the defect was discovered"
    )
    acknowledged_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When the defect was acknowledged"
    )
    repaired_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When the defect was repaired"
    )
    verified_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When the repair was verified"
    )
    closed_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When the defect was closed"
    )
    
    # Evidence linkage
    evidence_ids = Column(
        ARRAY(UUID(as_uuid=True)), 
        nullable=True, 
        default=list,
        doc="Array of evidence.id showing the defect"
    )
    repair_evidence_ids = Column(
        ARRAY(UUID(as_uuid=True)), 
        nullable=True, 
        default=list,
        doc="Photos of repair completion"
    )
    
    # Audit fields
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        doc="When the defect record was created"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the defect record was last updated"
    )
    created_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True,
        doc="User who created this defect record"
    )
    acknowledged_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True,
        doc="User who acknowledged this defect"
    )
    
    # Relationships
    test_session = relationship("TestSession", back_populates="defects")
    building = relationship("Building", back_populates="defects")
    created_by_user = relationship("User", foreign_keys=[created_by], back_populates="created_defects")
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by], back_populates="acknowledged_defects")
    
    def __repr__(self):
        return f"<Defect(id={self.id}, severity='{self.severity}', status='{self.status}', building={self.building_id})>"
