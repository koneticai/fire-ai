"""Add interface test tables

Revision ID: 007_add_interface_test_tables
Revises: 006_add_ce_test_tables
Create Date: 2025-01-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "007_add_interface_test_tables"
down_revision = "006_add_ce_test_tables"
branch_labels = None
depends_on = None


INTERFACE_TYPE_CONSTRAINT = (
    "interface_type IN ('manual_override', 'alarm_coordination', "
    "'shutdown_sequence', 'sprinkler_activation')"
)

SESSION_STATUS_CONSTRAINT = (
    "status IN ('scheduled', 'in_progress', 'completed', 'validated')"
)

COMPLIANCE_OUTCOME_CONSTRAINT = (
    "compliance_outcome IN ('pending', 'pass', 'fail')"
)


def upgrade():
    """Create interface test definition, session, and event tables."""
    # Interface test definitions store baseline expectations for each location
    op.create_table(
        "interface_test_definitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "building_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buildings.id", ondelete="CASCADE"),
            nullable=False,
            doc="Building this interface definition belongs to",
        ),
        sa.Column(
            "interface_type",
            sa.String(length=50),
            nullable=False,
            doc="Type of interface scenario (manual override, alarm coordination, etc.)",
        ),
        sa.Column(
            "location_id",
            sa.String(length=100),
            nullable=False,
            doc="Unique identifier for the control location",
        ),
        sa.Column(
            "location_name",
            sa.String(length=255),
            nullable=True,
            doc="Human readable location name",
        ),
        sa.Column(
            "test_action",
            sa.Text(),
            nullable=True,
            doc="Action to perform during the interface test",
        ),
        sa.Column(
            "expected_result",
            sa.Text(),
            nullable=True,
            doc="Expected system response for the interface test",
        ),
        sa.Column(
            "expected_response_time_s",
            sa.Integer(),
            nullable=True,
            doc="Expected response time in seconds",
        ),
        sa.Column(
            "guidance",
            postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            doc="Optional structured guidance and checklists",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            doc="Whether this definition is active for scheduling",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            doc="User who created the baseline definition",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            doc="Timestamp definition was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
            doc="Timestamp definition was last updated",
        ),
        sa.UniqueConstraint(
            "building_id",
            "interface_type",
            "location_id",
            name="uq_interface_definition_key",
        ),
    )

    op.create_check_constraint(
        "ck_interface_type",
        "interface_test_definitions",
        INTERFACE_TYPE_CONSTRAINT,
    )

    op.create_index(
        "ix_interface_test_definitions_building",
        "interface_test_definitions",
        ["building_id"],
    )
    op.create_index(
        "ix_interface_test_definitions_type",
        "interface_test_definitions",
        ["interface_type"],
    )

    # Interface test sessions represent execution records tied to definitions
    op.create_table(
        "interface_test_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "test_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("test_sessions.id", ondelete="SET NULL"),
            nullable=True,
            doc="Optional link to the broader fire test session",
        ),
        sa.Column(
            "definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interface_test_definitions.id", ondelete="RESTRICT"),
            nullable=False,
            doc="Baseline definition used for this interface test",
        ),
        sa.Column(
            "building_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buildings.id", ondelete="CASCADE"),
            nullable=False,
            doc="Building that the interface test was executed in",
        ),
        sa.Column(
            "interface_type",
            sa.String(length=50),
            nullable=False,
            doc="Type of interface scenario executed",
        ),
        sa.Column(
            "location_id",
            sa.String(length=100),
            nullable=False,
            doc="Location identifier captured at execution time",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'scheduled'"),
            doc="Lifecycle status of the interface test",
        ),
        sa.Column(
            "compliance_outcome",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'pending'"),
            doc="Compliance outcome (pending, pass, fail)",
        ),
        sa.Column(
            "expected_response_time_s",
            sa.Integer(),
            nullable=True,
            doc="Baseline expected response time in seconds",
        ),
        sa.Column(
            "observed_response_time_s",
            sa.Float(),
            nullable=True,
            doc="Measured response time during test execution",
        ),
        sa.Column(
            "response_time_delta_s",
            sa.Float(),
            nullable=True,
            doc="Difference between observed and expected response time",
        ),
        sa.Column(
            "observed_outcome",
            postgresql.JSONB,
            nullable=True,
            doc="Structured observations captured during execution",
        ),
        sa.Column(
            "failure_reasons",
            postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            doc="List of failure reasons when compliance_outcome == 'fail'",
        ),
        sa.Column(
            "validation_summary",
            sa.Text(),
            nullable=True,
            doc="Summary generated by the validator service",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            doc="When the interface test execution started",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            doc="When the execution finished",
        ),
        sa.Column(
            "validated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            doc="When the validator confirmed the outcome",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            doc="User who scheduled or created the interface test",
        ),
        sa.Column(
            "validated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            doc="User who validated the interface test outcome",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            doc="Timestamp record was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
            doc="Timestamp record was last updated",
        ),
    )

    op.create_check_constraint(
        "ck_interface_test_status",
        "interface_test_sessions",
        SESSION_STATUS_CONSTRAINT,
    )
    op.create_check_constraint(
        "ck_interface_test_outcome",
        "interface_test_sessions",
        COMPLIANCE_OUTCOME_CONSTRAINT,
    )
    op.create_check_constraint(
        "ck_interface_test_type",
        "interface_test_sessions",
        INTERFACE_TYPE_CONSTRAINT,
    )

    op.create_index(
        "ix_interface_test_sessions_building",
        "interface_test_sessions",
        ["building_id"],
    )
    op.create_index(
        "ix_interface_test_sessions_definition",
        "interface_test_sessions",
        ["definition_id"],
    )
    op.create_index(
        "ix_interface_test_sessions_status",
        "interface_test_sessions",
        ["status"],
    )
    op.create_index(
        "ix_interface_test_sessions_outcome",
        "interface_test_sessions",
        ["compliance_outcome"],
    )

    # Interface test events capture structured execution timeline
    op.create_table(
        "interface_test_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "interface_test_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interface_test_sessions.id", ondelete="CASCADE"),
            nullable=False,
            doc="Associated interface test session",
        ),
        sa.Column(
            "event_type",
            sa.String(length=50),
            nullable=False,
            doc="Event type (start, observation, response_detected, validation, etc.)",
        ),
        sa.Column(
            "event_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            doc="Timestamp when event occurred",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            doc="Optional descriptive notes for the event",
        ),
        sa.Column(
            "event_metadata",
            postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            doc="Structured metadata for the event",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            doc="Timestamp event record was created",
        ),
    )

    op.create_index(
        "ix_interface_test_events_session",
        "interface_test_events",
        ["interface_test_session_id"],
    )
    op.create_index(
        "ix_interface_test_events_type",
        "interface_test_events",
        ["event_type"],
    )


def downgrade():
    """Drop interface test tables."""
    op.drop_index(
        "ix_interface_test_events_type", table_name="interface_test_events"
    )
    op.drop_index(
        "ix_interface_test_events_session", table_name="interface_test_events"
    )
    op.drop_table("interface_test_events")

    op.drop_index(
        "ix_interface_test_sessions_outcome", table_name="interface_test_sessions"
    )
    op.drop_index(
        "ix_interface_test_sessions_status", table_name="interface_test_sessions"
    )
    op.drop_index(
        "ix_interface_test_sessions_definition",
        table_name="interface_test_sessions",
    )
    op.drop_index(
        "ix_interface_test_sessions_building",
        table_name="interface_test_sessions",
    )
    op.drop_constraint(
        "ck_interface_test_type",
        "interface_test_sessions",
        type_="check",
    )
    op.drop_constraint(
        "ck_interface_test_outcome",
        "interface_test_sessions",
        type_="check",
    )
    op.drop_constraint(
        "ck_interface_test_status",
        "interface_test_sessions",
        type_="check",
    )
    op.drop_table("interface_test_sessions")

    op.drop_index(
        "ix_interface_test_definitions_type",
        table_name="interface_test_definitions",
    )
    op.drop_index(
        "ix_interface_test_definitions_building",
        table_name="interface_test_definitions",
    )
    op.drop_constraint(
        "ck_interface_type",
        "interface_test_definitions",
        type_="check",
    )
    op.drop_constraint(
        "uq_interface_definition_key",
        "interface_test_definitions",
        type_="unique",
    )
    op.drop_table("interface_test_definitions")
