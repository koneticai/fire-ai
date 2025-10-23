"""Add attestation tables for device validation logging and trust scoring

Revision ID: 004_add_attestation_tables
Revises: 003_add_baseline_tables
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '004_add_attestation_tables'
down_revision = '003_add_baseline_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add attestation logging and trust scoring tables"""
    
    # Create attestation_logs table
    op.create_table('attestation_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('device_id', sa.String(255), nullable=False, comment="Device identifier (hash or UUID)"),
        sa.Column('platform', sa.String(20), nullable=False, comment="Platform: 'ios' or 'android'"),
        sa.Column('validator_type', sa.String(50), nullable=False, comment="Validator type: 'devicecheck', 'appattest', 'playintegrity', 'safetynet'"),
        sa.Column('token_hash', sa.String(64), nullable=False, comment="SHA-256 hash of the attestation token"),
        sa.Column('result', sa.String(20), nullable=False, comment="Validation result: 'valid', 'invalid', 'error'"),
        sa.Column('error_message', sa.Text, nullable=True, comment="Error message if validation failed"),
        sa.Column('metadata', JSONB, nullable=True, default={}, comment="Additional validation metadata"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment="When the attestation was attempted")
    )
    
    # Create device_trust_scores table
    op.create_table('device_trust_scores',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('device_id', sa.String(255), unique=True, nullable=False, comment="Device identifier (hash or UUID)"),
        sa.Column('platform', sa.String(20), nullable=False, comment="Platform: 'ios' or 'android'"),
        sa.Column('trust_score', sa.Integer, nullable=False, default=100, comment="Trust score 0-100 (100 = fully trusted)"),
        sa.Column('total_validations', sa.Integer, nullable=False, default=0, comment="Total number of validation attempts"),
        sa.Column('failed_validations', sa.Integer, nullable=False, default=0, comment="Number of failed validation attempts"),
        sa.Column('last_validation_at', sa.DateTime(timezone=True), nullable=True, comment="Timestamp of last validation attempt"),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment="When this device was first seen"),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment="When this record was last updated")
    )
    
    # Create indexes for attestation_logs
    op.create_index('idx_attestation_logs_device', 'attestation_logs', ['device_id'])
    op.create_index('idx_attestation_logs_created', 'attestation_logs', ['created_at'])
    op.create_index('idx_attestation_logs_result', 'attestation_logs', ['result'])
    op.create_index('idx_attestation_logs_platform', 'attestation_logs', ['platform'])
    op.create_index('idx_attestation_logs_validator', 'attestation_logs', ['validator_type'])
    
    # Create indexes for device_trust_scores
    op.create_index('idx_device_trust_device', 'device_trust_scores', ['device_id'])
    op.create_index('idx_device_trust_score', 'device_trust_scores', ['trust_score'])
    op.create_index('idx_device_trust_platform', 'device_trust_scores', ['platform'])
    op.create_index('idx_device_trust_last_validation', 'device_trust_scores', ['last_validation_at'])
    
    # Add trigger to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_device_trust_scores_updated_at 
        BEFORE UPDATE ON device_trust_scores 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    """Remove attestation tables and related objects"""
    
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS update_device_trust_scores_updated_at ON device_trust_scores")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop indexes for device_trust_scores
    op.drop_index('idx_device_trust_last_validation', 'device_trust_scores')
    op.drop_index('idx_device_trust_platform', 'device_trust_scores')
    op.drop_index('idx_device_trust_score', 'device_trust_scores')
    op.drop_index('idx_device_trust_device', 'device_trust_scores')
    
    # Drop indexes for attestation_logs
    op.drop_index('idx_attestation_logs_validator', 'attestation_logs')
    op.drop_index('idx_attestation_logs_platform', 'attestation_logs')
    op.drop_index('idx_attestation_logs_result', 'attestation_logs')
    op.drop_index('idx_attestation_logs_created', 'attestation_logs')
    op.drop_index('idx_attestation_logs_device', 'attestation_logs')
    
    # Drop tables
    op.drop_table('device_trust_scores')
    op.drop_table('attestation_logs')
