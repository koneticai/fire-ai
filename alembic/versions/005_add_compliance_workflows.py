"""Add compliance workflow tables

Revision ID: 005_add_compliance_workflows
Revises: 004_add_attestation_tables
Create Date: 2025-01-10

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = '005_add_compliance_workflows'
down_revision = '004_add_attestation_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create compliance workflow tables"""

    op.create_table(
        'compliance_workflows',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('compliance_standard', sa.String(100), nullable=False, server_default='AS1851-2012'),
        sa.Column('workflow_definition', JSONB, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'compliance_workflow_instances',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', UUID(as_uuid=True), sa.ForeignKey('compliance_workflows.id'), nullable=False),
        sa.Column('building_id', UUID(as_uuid=True), sa.ForeignKey('buildings.id'), nullable=False),
        sa.Column('current_node_id', sa.String(255), nullable=True),
        sa.Column('instance_data', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_compliance_workflows_status', 'compliance_workflows', ['status'])
    op.create_index('ix_compliance_workflows_standard', 'compliance_workflows', ['compliance_standard'])
    op.create_index('ix_compliance_workflows_created_by', 'compliance_workflows', ['created_by'])
    op.create_index('ix_compliance_workflow_instances_workflow_id', 'compliance_workflow_instances', ['workflow_id'])
    op.create_index('ix_compliance_workflow_instances_building_id', 'compliance_workflow_instances', ['building_id'])
    op.create_index('ix_compliance_workflow_instances_status', 'compliance_workflow_instances', ['status'])


def downgrade():
    """Drop compliance workflow tables"""

    op.drop_index('ix_compliance_workflow_instances_status', table_name='compliance_workflow_instances')
    op.drop_index('ix_compliance_workflow_instances_building_id', table_name='compliance_workflow_instances')
    op.drop_index('ix_compliance_workflow_instances_workflow_id', table_name='compliance_workflow_instances')
    op.drop_index('ix_compliance_workflows_created_by', table_name='compliance_workflows')
    op.drop_index('ix_compliance_workflows_standard', table_name='compliance_workflows')
    op.drop_index('ix_compliance_workflows_status', table_name='compliance_workflows')

    op.drop_table('compliance_workflow_instances')
    op.drop_table('compliance_workflows')
