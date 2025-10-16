"""Add evidence flag columns for soft-delete functionality

Revision ID: 002_add_evidence_flag_columns
Revises: 001_add_defects_table
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '002_add_evidence_flag_columns'
down_revision = '001_add_defects_table'
branch_labels = None
depends_on = None


def upgrade():
    """Add flag columns to evidence table for soft-delete functionality"""
    
    # Add flag columns to evidence table
    op.add_column('evidence', 
        sa.Column('flagged_for_review', sa.Boolean(), nullable=False, server_default='false',
                 comment="Flag indicating if evidence is flagged for review (soft-delete)")
    )
    
    op.add_column('evidence', 
        sa.Column('flag_reason', sa.Text(), nullable=True,
                 comment="Reason for flagging the evidence for review")
    )
    
    op.add_column('evidence', 
        sa.Column('flagged_at', sa.DateTime(timezone=True), nullable=True,
                 comment="Timestamp when evidence was flagged for review")
    )
    
    op.add_column('evidence', 
        sa.Column('flagged_by', UUID(as_uuid=True), 
                 sa.ForeignKey('users.id', ondelete='SET NULL'), 
                 nullable=True,
                 comment="User who flagged the evidence for review")
    )
    
    # Create index for performance on flagged_for_review queries
    op.create_index('idx_evidence_flagged_for_review', 'evidence', ['flagged_for_review'])
    op.create_index('idx_evidence_flagged_by', 'evidence', ['flagged_by'])
    op.create_index('idx_evidence_flagged_at', 'evidence', ['flagged_at'])


def downgrade():
    """Remove flag columns from evidence table"""
    
    # Drop indexes
    op.drop_index('idx_evidence_flagged_at', 'evidence')
    op.drop_index('idx_evidence_flagged_by', 'evidence')
    op.drop_index('idx_evidence_flagged_for_review', 'evidence')
    
    # Drop columns
    op.drop_column('evidence', 'flagged_by')
    op.drop_column('evidence', 'flagged_at')
    op.drop_column('evidence', 'flag_reason')
    op.drop_column('evidence', 'flagged_for_review')
