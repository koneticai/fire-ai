"""
SQLAlchemy models for Interface Tests

These models capture baseline definitions, execution sessions, and timeline events
for AS1851 interface integration testing (manual override, alarm coordination, etc.).
"""

import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Integer,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class InterfaceTestDefinition(Base):
    """
    SQLAlchemy model for interface_test_definitions table.

    Stores baseline expectations for each interface scenario per building/location.
    """

    __tablename__ = "interface_test_definitions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    building_id = Column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        doc="Building this interface definition belongs to",
    )
    interface_type = Column(
        String(50),
        nullable=False,
        doc="Interface scenario type (manual_override, alarm_coordination, etc.)",
    )
    location_id = Column(
        String(100),
        nullable=False,
        doc="Unique identifier for the interface location",
    )
    location_name = Column(
        String(255),
        nullable=True,
        doc="Human readable name for the location",
    )
    test_action = Column(
        Text,
        nullable=True,
        doc="Action technicians should perform during the test",
    )
    expected_result = Column(
        Text,
        nullable=True,
        doc="Expected control system response",
    )
    expected_response_time_s = Column(
        Integer,
        nullable=True,
        doc="Expected response time in seconds according to baseline",
    )
    guidance = Column(
        JSONB,
        nullable=True,
        default=dict,
        server_default="{}",
        doc="Structured guidance (checklists, prerequisites, etc.)",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="Whether this definition is currently active",
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who created the definition",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the definition was created",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="When the definition was last updated",
    )

    building = relationship("Building", back_populates="interface_test_definitions")
    sessions = relationship(
        "InterfaceTestSession",
        back_populates="definition",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<InterfaceTestDefinition(id={self.id}, "
            f"type='{self.interface_type}', location='{self.location_id}')>"
        )


class InterfaceTestSession(Base):
    """
    SQLAlchemy model for interface_test_sessions table.

    Represents execution instances for interface testing, capturing observed
    response times and validation outcomes.
    """

    __tablename__ = "interface_test_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    test_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_sessions.id", ondelete="SET NULL"),
        nullable=True,
        doc="Optional link to umbrella fire safety test session",
    )
    definition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interface_test_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        doc="Reference to baseline definition used",
    )
    building_id = Column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        doc="Building where the interface test took place",
    )
    interface_type = Column(
        String(50),
        nullable=False,
        doc="Interface scenario type recorded during execution",
    )
    location_id = Column(
        String(100),
        nullable=False,
        doc="Location identifier recorded at execution time",
    )
    status = Column(
        String(50),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
        doc="Execution lifecycle status (scheduled, in_progress, completed, validated)",
    )
    compliance_outcome = Column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
        doc="Compliance outcome (pending, pass, fail)",
    )
    expected_response_time_s = Column(
        Integer,
        nullable=True,
        doc="Expected response time in seconds (copied from definition)",
    )
    observed_response_time_s = Column(
        Float,
        nullable=True,
        doc="Measured response time in seconds",
    )
    response_time_delta_s = Column(
        Float,
        nullable=True,
        doc="Difference between observed and expected response times",
    )
    observed_outcome = Column(
        JSONB,
        nullable=True,
        doc="Structured observations captured during execution",
    )
    failure_reasons = Column(
        JSONB,
        nullable=True,
        default=list,
        server_default="[]",
        doc="List of failure reasons when compliance_outcome == 'fail'",
    )
    validation_summary = Column(
        Text,
        nullable=True,
        doc="Summary generated by validator service",
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp execution started",
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp execution completed",
    )
    validated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp validation completed",
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who created the execution record",
    )
    validated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who validated the outcome",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp record was created",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp record was last updated",
    )

    definition = relationship("InterfaceTestDefinition", back_populates="sessions")
    building = relationship("Building", back_populates="interface_test_sessions")
    test_session = relationship("TestSession", back_populates="interface_tests")
    events = relationship(
        "InterfaceTestEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<InterfaceTestSession(id={self.id}, type='{self.interface_type}', "
            f"status='{self.status}', outcome='{self.compliance_outcome}')>"
        )


class InterfaceTestEvent(Base):
    """
    SQLAlchemy model for interface_test_events table.

    Records timeline events (start, observation, response_detected, validation, etc.)
    associated with an interface test execution.
    """

    __tablename__ = "interface_test_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    interface_test_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interface_test_sessions.id", ondelete="CASCADE"),
        nullable=False,
        doc="Associated interface test session",
    )
    event_type = Column(
        String(50),
        nullable=False,
        doc="Event type recorded during execution timeline",
    )
    event_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp event occurred",
    )
    notes = Column(
        Text,
        nullable=True,
        doc="Optional free text description for the event",
    )
    event_metadata = Column(
        JSONB,
        nullable=True,
        default=dict,
        server_default="{}",
        doc="Structured metadata for the event",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp event was recorded",
    )

    session = relationship("InterfaceTestSession", back_populates="events")

    def __repr__(self):
        return (
            f"<InterfaceTestEvent(id={self.id}, session={self.interface_test_session_id}, "
            f"type='{self.event_type}')>"
        )
