"""Add defects table for FIRE-AI demo MVP

Revision ID: 001_add_defects_table
Revises: 000_create_trigger_function
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '001_add_defects_table'
down_revision = '000_create_trigger_function'
branch_labels = None
depends_on = None


def upgrade():
    """Add defects table with full schema"""
    
    # Create defects table
    op.create_table('defects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        
        # Core relationships
        sa.Column('test_session_id', UUID(as_uuid=True), sa.ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('building_id', UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_id', UUID(as_uuid=True), nullable=True),  # Optional - which equipment has the defect
        
        # Classification (AS1851 aligned)
        sa.Column('severity', sa.String(20), nullable=False, 
                 comment="Defect severity: critical, high, medium, low"),
        sa.Column('category', sa.String(50), nullable=True, 
                 comment="Defect category: e.g., extinguisher_pressure, hose_reel_leak"),
        sa.Column('description', sa.Text, nullable=False, 
                 comment="Detailed description of the defect"),
        sa.Column('as1851_rule_code', sa.String(20), nullable=True, 
                 comment="AS1851 rule code: e.g., FE-01, HR-03"),
        
        # Status workflow
        sa.Column('status', sa.String(20), nullable=False, default='open',
                 server_default='open',
                 comment="Defect status: open, acknowledged, repair_scheduled, repaired, verified, closed"),
        
        # Timestamps
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('repaired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Evidence linkage
        sa.Column('evidence_ids', sa.ARRAY(UUID(as_uuid=True)), nullable=True,
                 server_default=sa.text("'{}'::uuid[]"),
                 comment="Array of evidence.id showing the defect"),
        sa.Column('repair_evidence_ids', sa.ARRAY(UUID(as_uuid=True)), nullable=True,
                 server_default=sa.text("'{}'::uuid[]"),
                 comment="Photos of repair completion"),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('acknowledged_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Add check constraints for enums
    op.create_check_constraint(
        'chk_defects_severity',
        'defects',
        "severity IN ('critical', 'high', 'medium', 'low')"
    )
    
    op.create_check_constraint(
        'chk_defects_status',
        'defects', 
        "status IN ('open', 'acknowledged', 'repair_scheduled', 'repaired', 'verified', 'closed')"
    )
    
    # Create indexes for performance
    op.create_index('idx_defects_test_session', 'defects', ['test_session_id'])
    op.create_index('idx_defects_building', 'defects', ['building_id'])
    op.create_index('idx_defects_status', 'defects', ['status'])
    op.create_index('idx_defects_severity', 'defects', ['severity'])
    op.create_index('idx_defects_created_by', 'defects', ['created_by'])
    op.create_index('idx_defects_discovered_at', 'defects', ['discovered_at'])
    
    # Composite indexes for common queries
    op.create_index('idx_defects_building_status', 'defects', ['building_id', 'status'])
    op.create_index('idx_defects_session_status', 'defects', ['test_session_id', 'status'])
    
    # Create updated_at trigger for defects table
    op.execute("""
        CREATE TRIGGER update_defects_updated_at 
        BEFORE UPDATE ON defects 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade():
    """Remove defects table and related objects"""
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_defects_updated_at ON defects")
    
    # Drop indexes
    indexes_to_drop = [
        'idx_defects_test_session',
        'idx_defects_building', 
        'idx_defects_status',
        'idx_defects_severity',
        'idx_defects_created_by',
        'idx_defects_discovered_at',
        'idx_defects_building_status',
        'idx_defects_session_status'
    ]
    
    for index_name in indexes_to_drop:
        op.drop_index(index_name, 'defects')
    
    # Drop check constraints
    op.drop_constraint('chk_defects_severity', 'defects', type_='check')
    op.drop_constraint('chk_defects_status', 'defects', type_='check')
    
    # Drop table
    op.drop_table('defects')
