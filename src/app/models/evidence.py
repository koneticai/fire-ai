"""
SQLAlchemy model for Evidence
"""

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
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
    
    # Relationships
    test_session = relationship("TestSession", back_populates="evidence")
    
    def __repr__(self):
        return f"<Evidence(id={self.id}, type='{self.evidence_type}', session={self.session_id})>"