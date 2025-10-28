"""
SQLAlchemy model for AuditLog

Compliance audit trail per data_model.md specification.
Tracks all sensitive operations for AS 1851-2012 compliance.
"""

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class AuditLog(Base):
    """
    AuditLog model for compliance tracking.
    
    Records all sensitive operations including:
    - Evidence uploads (WORM-protected)
    - User actions
    - Data modifications
    
    References:
    - data_model.md: audit_log table schema
    - AS 1851-2012: Audit trail requirements
    """
    __tablename__ = 'audit_log'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
        doc="Unique audit log entry ID"
    )
    
    # User information
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        doc="User who performed the action (nullable for system actions)"
    )
    
    # Action details
    action = Column(
        String,
        nullable=False,
        index=True,
        doc="Action type (e.g., UPLOAD_EVIDENCE_WORM, CREATE_USER)"
    )
    
    resource_type = Column(
        String,
        nullable=False,
        index=True,
        doc="Resource type (e.g., evidence, user, building)"
    )
    
    resource_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        doc="ID of the resource affected"
    )
    
    # Change tracking
    old_values = Column(
        JSONB,
        nullable=True,
        doc="State before the action (JSONB for flexibility)"
    )
    
    new_values = Column(
        JSONB,
        nullable=True,
        doc="State after the action (JSONB for flexibility)"
    )
    
    # Request metadata
    ip_address = Column(
        INET,
        nullable=True,
        doc="Client IP address"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="Client user agent string"
    )
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="When the action occurred"
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_audit_log_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_log_user_action', 'user_id', 'action'),
        Index('idx_audit_log_created_at_desc', created_at.desc()),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user={self.user_id}, resource={self.resource_type}:{self.resource_id})>"
