"""Create update_updated_at_column trigger function

Revision ID: 000_create_trigger_function
Revises: phase2_final_indexes
Create Date: 2024-12-19

This migration creates the reusable trigger function that automatically
updates the updated_at column whenever a row is modified.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '000_create_trigger_function'
down_revision = 'phase2_final_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Create the update_updated_at_column() trigger function"""

    # Create the trigger function if it doesn't exist
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)


def downgrade():
    """Remove the update_updated_at_column() trigger function"""

    # Drop the function (CASCADE will drop any dependent triggers)
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;")
