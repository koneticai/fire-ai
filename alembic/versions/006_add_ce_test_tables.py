"""Add C&E test tables

Revision ID: 006_add_ce_test_tables
Revises: 005_add_compliance_workflows
Create Date: 2025-01-10

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = '006_add_ce_test_tables'
down_revision = '005_add_compliance_workflows'
branch_labels = None
depends_on = None


def upgrade():
    """Create C&E test tables"""

    # C&E Test Sessions table
    op.create_table(
        'ce_test_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('session_name', sa.String(255), nullable=False),
        sa.Column('building_id', UUID(as_uuid=True), sa.ForeignKey('buildings.id'), nullable=False),
        sa.Column('test_type', sa.String(100), nullable=False, server_default='containment_efficiency'),
        sa.Column('compliance_standard', sa.String(100), nullable=False, server_default='AS1851-2012'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('test_configuration', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('test_results', JSONB, nullable=True),
        sa.Column('deviation_analysis', JSONB, nullable=True),
        sa.Column('compliance_score', sa.Float(), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # C&E Test Measurements table
    op.create_table(
        'ce_test_measurements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('test_session_id', UUID(as_uuid=True), sa.ForeignKey('ce_test_sessions.id'), nullable=False),
        sa.Column('measurement_type', sa.String(100), nullable=False),  # pressure, velocity, temperature, etc.
        sa.Column('location_id', sa.String(255), nullable=False),  # zone, room, or specific location
        sa.Column('measurement_value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('measurement_metadata', JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # C&E Test Deviations table
    op.create_table(
        'ce_test_deviations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('test_session_id', UUID(as_uuid=True), sa.ForeignKey('ce_test_sessions.id'), nullable=False),
        sa.Column('deviation_type', sa.String(100), nullable=False),  # pressure_drop, velocity_exceeded, etc.
        sa.Column('severity', sa.String(50), nullable=False),  # minor, major, critical
        sa.Column('location_id', sa.String(255), nullable=False),
        sa.Column('expected_value', sa.Float(), nullable=True),
        sa.Column('actual_value', sa.Float(), nullable=False),
        sa.Column('tolerance_percentage', sa.Float(), nullable=True),
        sa.Column('deviation_percentage', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('recommended_action', sa.Text(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # C&E Test Reports table
    op.create_table(
        'ce_test_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('test_session_id', UUID(as_uuid=True), sa.ForeignKey('ce_test_sessions.id'), nullable=False),
        sa.Column('report_type', sa.String(100), nullable=False, server_default='compliance_report'),
        sa.Column('report_data', JSONB, nullable=False),
        sa.Column('generated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_final', sa.Boolean(), nullable=False, server_default='false'),
    )

    # Create indexes for performance
    op.create_index('ix_ce_test_sessions_building_id', 'ce_test_sessions', ['building_id'])
    op.create_index('ix_ce_test_sessions_status', 'ce_test_sessions', ['status'])
    op.create_index('ix_ce_test_sessions_test_type', 'ce_test_sessions', ['test_type'])
    op.create_index('ix_ce_test_sessions_created_by', 'ce_test_sessions', ['created_by'])
    
    # Composite indexes for common query patterns
    op.create_index('ix_ce_test_sessions_created_by_status', 'ce_test_sessions', ['created_by', 'status'])
    op.create_index('ix_ce_test_sessions_building_status', 'ce_test_sessions', ['building_id', 'status'])
    
    op.create_index('ix_ce_test_measurements_session_id', 'ce_test_measurements', ['test_session_id'])
    op.create_index('ix_ce_test_measurements_type', 'ce_test_measurements', ['measurement_type'])
    op.create_index('ix_ce_test_measurements_location', 'ce_test_measurements', ['location_id'])
    op.create_index('ix_ce_test_measurements_timestamp', 'ce_test_measurements', ['timestamp'])
    
    # Composite index for measurement queries with timestamp ordering
    op.create_index('ix_ce_test_measurements_session_timestamp', 'ce_test_measurements', ['test_session_id', 'timestamp'])
    
    op.create_index('ix_ce_test_deviations_session_id', 'ce_test_deviations', ['test_session_id'])
    op.create_index('ix_ce_test_deviations_type', 'ce_test_deviations', ['deviation_type'])
    op.create_index('ix_ce_test_deviations_severity', 'ce_test_deviations', ['severity'])
    op.create_index('ix_ce_test_deviations_resolved', 'ce_test_deviations', ['is_resolved'])
    
    # Composite index for deviation queries by severity
    op.create_index('ix_ce_test_deviations_session_severity', 'ce_test_deviations', ['test_session_id', 'severity'])
    
    op.create_index('ix_ce_test_reports_session_id', 'ce_test_reports', ['test_session_id'])
    op.create_index('ix_ce_test_reports_type', 'ce_test_reports', ['report_type'])
    op.create_index('ix_ce_test_reports_final', 'ce_test_reports', ['is_final'])


def downgrade():
    """Drop C&E test tables"""

    # Drop indexes
    op.drop_index('ix_ce_test_reports_final', table_name='ce_test_reports')
    op.drop_index('ix_ce_test_reports_type', table_name='ce_test_reports')
    op.drop_index('ix_ce_test_reports_session_id', table_name='ce_test_reports')
    
    op.drop_index('ix_ce_test_deviations_session_severity', table_name='ce_test_deviations')
    op.drop_index('ix_ce_test_deviations_resolved', table_name='ce_test_deviations')
    op.drop_index('ix_ce_test_deviations_severity', table_name='ce_test_deviations')
    op.drop_index('ix_ce_test_deviations_type', table_name='ce_test_deviations')
    op.drop_index('ix_ce_test_deviations_session_id', table_name='ce_test_deviations')
    
    op.drop_index('ix_ce_test_measurements_session_timestamp', table_name='ce_test_measurements')
    op.drop_index('ix_ce_test_measurements_timestamp', table_name='ce_test_measurements')
    op.drop_index('ix_ce_test_measurements_location', table_name='ce_test_measurements')
    op.drop_index('ix_ce_test_measurements_type', table_name='ce_test_measurements')
    op.drop_index('ix_ce_test_measurements_session_id', table_name='ce_test_measurements')
    
    op.drop_index('ix_ce_test_sessions_building_status', table_name='ce_test_sessions')
    op.drop_index('ix_ce_test_sessions_created_by_status', table_name='ce_test_sessions')
    op.drop_index('ix_ce_test_sessions_created_by', table_name='ce_test_sessions')
    op.drop_index('ix_ce_test_sessions_test_type', table_name='ce_test_sessions')
    op.drop_index('ix_ce_test_sessions_status', table_name='ce_test_sessions')
    op.drop_index('ix_ce_test_sessions_building_id', table_name='ce_test_sessions')

    # Drop tables
    op.drop_table('ce_test_reports')
    op.drop_table('ce_test_deviations')
    op.drop_table('ce_test_measurements')
    op.drop_table('ce_test_sessions')
