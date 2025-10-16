"""
SQLAlchemy model for Evidence
"""

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class Evidence(Base):
    """
    SQLAlchemy model for Evidence table
    
    Represents evidence files/data collected during fire safety testing.
    Matches existing database schema structure.
    """
    __tablename__ = 'evidence'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Relationships
    session_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('test_sessions.id'), 
        nullable=False,
        doc="Test session this evidence belongs to"
    )
    
    # Evidence information
    evidence_type = Column(
        String, 
        nullable=False,
        doc="Type/category of evidence"
    )
    file_path = Column(
        String, 
        nullable=True,
        doc="Path to stored file if applicable"
    )
    
    # Data and evidence metadata (renamed to avoid SQLAlchemy reserved name)
    evidence_metadata = Column(
        "metadata",  # Database column name
        JSONB, 
        nullable=True, 
        default={},
        doc="Flexible metadata storage for evidence"
    )
    checksum = Column(
        String, 
        nullable=True,
        doc="SHA-256 checksum for file integrity verification"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the evidence was created/uploaded"
    )
    
    # Flag columns for soft-delete functionality
    flagged_for_review = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default='false',
        doc="Flag indicating if evidence is flagged for review (soft-delete)"
    )
    flag_reason = Column(
        Text,
        nullable=True,
        doc="Reason for flagging the evidence for review"
    )
    flagged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when evidence was flagged for review"
    )
    flagged_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=True,
        doc="User who flagged the evidence for review"
    )
    
    # Relationships
    test_session = relationship("TestSession", back_populates="evidence")
    flagged_by_user = relationship("User", foreign_keys=[flagged_by])
    
    def __repr__(self):
        return f"<Evidence(id={self.id}, type='{self.evidence_type}', session={self.session_id})>"