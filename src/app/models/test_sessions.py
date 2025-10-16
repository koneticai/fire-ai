"""
SQLAlchemy model for Test Sessions
"""

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class TestSession(Base):
    """
    SQLAlchemy model for Test Sessions table
    
    Represents a fire safety testing session for a specific building.
    Includes CRDT support via vector_clock and flexible session_data storage.
    Matches existing database schema exactly.
    """
    __tablename__ = 'test_sessions'
    
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
        doc="Building being tested in this session"
    )
    
    # Session information
    session_name = Column(
        String, 
        nullable=False,
        doc="Descriptive name for the testing session"
    )
    status = Column(
        String, 
        nullable=True, 
        default='active',
        server_default='active',
        doc="Current status of the testing session"
    )
    
    # CRDT and flexible data storage
    vector_clock = Column(
        JSONB, 
        nullable=True, 
        default={},
        server_default='{}',
        doc="CRDT vector clock for conflict-free distributed updates"
    )
    session_data = Column(
        JSONB, 
        nullable=True, 
        default={},
        server_default='{}',
        doc="Flexible data storage for session-specific information and test results"
    )
    
    # User tracking
    created_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=True,
        doc="User who created this test session"
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
    building = relationship("Building", back_populates="test_sessions")
    evidence = relationship(
        "Evidence", 
        back_populates="test_session",
        cascade="all, delete-orphan"
    )
    defects = relationship(
        "Defect", 
        back_populates="test_session",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<TestSession(id={self.id}, name='{self.session_name}', status='{self.status}')>"