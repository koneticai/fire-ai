"""Add report finalization fields

Revision ID: 010_add_report_finalization_fields
Revises: 009_add_idempotency_and_audit_tables
Create Date: 2025-10-27

Add fields for AS 1851-2012 compliant report finalization with WORM storage.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '010_add_report_finalization_fields'
down_revision = '009_add_idempotency_and_audit_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add finalization fields to ce_test_reports table."""
    
    # Add finalization status
    op.add_column('ce_test_reports',
        sa.Column('finalized', sa.Boolean(), server_default='false', nullable=False)
    )
    
    # Add finalization timestamp
    op.add_column('ce_test_reports',
        sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add finalizing user reference
    op.add_column('ce_test_reports',
        sa.Column('finalized_by', UUID(as_uuid=True), nullable=True)
    )
    
    # Add WORM storage URI
    op.add_column('ce_test_reports',
        sa.Column('engineer_signature_s3_uri', sa.Text(), nullable=True)
    )
    
    # Add engineer license number
    op.add_column('ce_test_reports',
        sa.Column('engineer_license_number', sa.String(100), nullable=True)
    )
    
    # Add compliance statement
    op.add_column('ce_test_reports',
        sa.Column('compliance_statement', sa.Text(), nullable=True)
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_ce_test_reports_finalized_by',
        'ce_test_reports',
        'users',
        ['finalized_by'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for finalized reports
    op.create_index('ix_ce_test_reports_finalized', 'ce_test_reports', ['finalized'])
    
    # Create composite index for common queries
    op.create_index('ix_ce_test_reports_finalized_by_user', 'ce_test_reports', ['finalized_by', 'finalized'])


def downgrade():
    """Remove finalization fields from ce_test_reports table."""
    
    # Drop indexes
    op.drop_index('ix_ce_test_reports_finalized_by_user', 'ce_test_reports')
    op.drop_index('ix_ce_test_reports_finalized', 'ce_test_reports')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_ce_test_reports_finalized_by', 'ce_test_reports', type_='foreignkey')
    
    # Drop columns in reverse order
    op.drop_column('ce_test_reports', 'compliance_statement')
    op.drop_column('ce_test_reports', 'engineer_license_number')
    op.drop_column('ce_test_reports', 'engineer_signature_s3_uri')
    op.drop_column('ce_test_reports', 'finalized_by')
    op.drop_column('ce_test_reports', 'finalized_at')
    op.drop_column('ce_test_reports', 'finalized')
