"""
SQLAlchemy model for AS1851 Rules table

This model maps to the as1851_rules table in the database.
The existing Pydantic models in rules.py remain for API serialization.
"""

import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from ..database.core import Base


class AS1851RuleDB(Base):
    """
    SQLAlchemy ORM model for as1851_rules table.

    Stores AS1851-2012 compliance rules with versioning support.
    Rule schemas define validation rules for fault classification.
    """
    __tablename__ = 'as1851_rules'

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )

    # Rule identification
    rule_code = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Unique rule code identifier (e.g., AS1851-2012-SP-01)"
    )
    version = Column(
        String(50),
        nullable=False,
        doc="Semantic version (e.g., 1.0.0)"
    )

    # Rule details
    rule_name = Column(
        String(255),
        nullable=False,
        doc="Human-readable rule name"
    )
    description = Column(
        Text,
        nullable=True,
        doc="Detailed rule description"
    )
    category = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Rule category (e.g., SP, FD, SC)"
    )
    test_frequency = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Required test frequency"
    )

    # Rule schema (JSONB for PostgreSQL GIN indexing)
    rule_schema = Column(
        JSONB,
        nullable=False,
        doc="JSON schema defining validation rules"
    )

    # Status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default='true',
        doc="Whether this rule version is active"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="When the rule was created"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the rule was last updated"
    )

    # Composite unique constraint
    __table_args__ = (
        Index('idx_as1851_rules_code_version', 'rule_code', 'version', unique=True),
        Index('idx_as1851_rules_schema', 'rule_schema', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<AS1851RuleDB(id={self.id}, code='{self.rule_code}', version='{self.version}')>"
