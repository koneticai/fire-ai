"""Add index on interface_test_events.event_at for performance

Revision ID: 008_add_interface_events_event_at_index
Revises: 007_add_interface_test_tables
Create Date: 2025-10-23

This migration adds an index on the event_at column of interface_test_events
to improve performance of chronological event queries.
"""

from alembic import op


revision = "008_add_interface_events_event_at_index"
down_revision = "007_add_interface_test_tables"
branch_labels = None
depends_on = None


def upgrade():
    """Add index on event_at column for chronological queries."""
    op.create_index(
        "ix_interface_test_events_event_at",
        "interface_test_events",
        ["event_at"],
    )


def downgrade():
    """Remove index on event_at column."""
    op.drop_index(
        "ix_interface_test_events_event_at",
        table_name="interface_test_events"
    )
