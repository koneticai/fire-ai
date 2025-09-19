"""
SQLAlchemy model for Users
"""

import uuid
from sqlalchemy import Column, String, DateTime, Boolean, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class User(Base):
    """
    SQLAlchemy model for Users table
    
    Represents a user account with encrypted PII data.
    Matches existing database schema exactly.
    """
    __tablename__ = 'users'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # User credentials and identification
    username = Column(
        String, 
        nullable=False, 
        unique=True,
        doc="Unique username for authentication"
    )
    email = Column(
        String, 
        nullable=False, 
        unique=True,
        doc="User's email address"
    )
    
    # Encrypted PII data (using Fernet encryption)
    full_name_encrypted = Column(
        LargeBinary, 
        nullable=False,
        doc="User's full name encrypted with Fernet"
    )
    
    # Authentication
    password_hash = Column(
        String, 
        nullable=False,
        doc="Hashed password for authentication"
    )
    
    # Account status
    is_active = Column(
        Boolean, 
        nullable=True, 
        default=True,
        server_default='true',
        doc="Whether the user account is active"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the user account was created"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the user account was last updated"
    )
    
    # Relationships
    buildings = relationship("Building", foreign_keys="Building.owner_id")
    test_sessions = relationship("TestSession", foreign_keys="TestSession.created_by")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', active={self.is_active})>"