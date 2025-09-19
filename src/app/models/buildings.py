"""
SQLAlchemy model for Buildings
"""

import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class Building(Base):
    """
    SQLAlchemy model for Buildings table
    
    Represents a building/property that undergoes fire safety compliance testing.
    Matches existing database schema exactly.
    """
    __tablename__ = 'buildings'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Core building information
    name = Column(String, nullable=False, doc="Building name/identifier")
    address = Column(Text, nullable=False, doc="Full address of the building")
    building_type = Column(String, nullable=False, doc="Type/category of building")
    
    # Ownership and status
    owner_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=True,
        doc="Optional owner/manager of the building"
    )
    compliance_status = Column(
        String, 
        nullable=True, 
        default='pending',
        server_default='pending',
        doc="Current compliance status"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the building record was created"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the building record was last updated"
    )
    
    # Relationships
    test_sessions = relationship(
        "TestSession", 
        back_populates="building",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Building(id={self.id}, name='{self.name}', type='{self.building_type}')>"