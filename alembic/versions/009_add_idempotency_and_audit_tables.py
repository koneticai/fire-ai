"""Add idempotency_keys and audit_log tables

Revision ID: 009_add_idempotency_and_audit_tables
Revises: 008_add_interface_events_event_at_index
Create Date: 2025-10-26

Critical: These tables are defined in data_model.md and schema.sql but were missing from migrations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

# revision identifiers, used by Alembic.
revision = '009_add_idempotency_and_audit_tables'
down_revision = '008_add_interface_events_event_at_index'
branch_labels = None
depends_on = None


def upgrade():
    """Add idempotency_keys and audit_log tables per data_model.md specification"""
    
    # Create idempotency_keys table
    op.create_table('idempotency_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True, 
                 comment='SHA-256 hash of the idempotency key'),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=False, 
                 comment='API endpoint that was called'),
        sa.Column('request_hash', sa.String(64), nullable=False, 
                 comment='SHA-256 hash of request body'),
        sa.Column('response_data', JSONB, nullable=True, 
                 comment='Cached response data'),
        sa.Column('status_code', sa.Integer, nullable=True, 
                 comment='HTTP status code'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, 
                 comment='TTL for automatic cleanup'),
        comment='Request deduplication using idempotency keys'
    )
    
    # Create audit_log table
    op.create_table('audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
                 comment='User who performed the action'),
        sa.Column('action', sa.String(100), nullable=False, 
                 comment='Action type: CLASSIFY_FAULT, CREATE_BUILDING, etc.'),
        sa.Column('resource_type', sa.String(100), nullable=False, 
                 comment='Resource type: as1851_rule, building, test_session, etc.'),
        sa.Column('resource_id', UUID(as_uuid=True), nullable=True, 
                 comment='ID of the specific resource'),
        sa.Column('old_values', JSONB, nullable=True, 
                 comment='Snapshot before change'),
        sa.Column('new_values', JSONB, nullable=True, 
                 comment='Snapshot after change'),
        sa.Column('ip_address', INET, nullable=True, 
                 comment='Client IP address'),
        sa.Column('user_agent', sa.Text, nullable=True, 
                 comment='Client user agent string'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
                 comment='Timestamp of the action'),
        comment='Complete compliance audit trail'
    )
    
    # Create indexes for idempotency_keys
    op.create_index('idx_idempotency_key_hash', 'idempotency_keys', ['key_hash'], unique=True)
    op.create_index('idx_idempotency_expires', 'idempotency_keys', ['expires_at'], 
                    comment='For cleanup of expired keys')
    op.create_index('idx_idempotency_user_id', 'idempotency_keys', ['user_id'])
    
    # Create indexes for audit_log
    op.create_index('idx_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('idx_audit_log_action', 'audit_log', ['action'])
    op.create_index('idx_audit_log_created_at', 'audit_log', ['created_at'], 
                    comment='For time-based queries')
    op.create_index('idx_audit_log_resource', 'audit_log', ['resource_type', 'resource_id'], 
                    comment='Composite index for resource lookups')


def downgrade():
    """Drop idempotency_keys and audit_log tables"""
    
    # Drop indexes first
    op.drop_index('idx_audit_log_resource', table_name='audit_log')
    op.drop_index('idx_audit_log_created_at', table_name='audit_log')
    op.drop_index('idx_audit_log_action', table_name='audit_log')
    op.drop_index('idx_audit_log_user_id', table_name='audit_log')
    
    op.drop_index('idx_idempotency_user_id', table_name='idempotency_keys')
    op.drop_index('idx_idempotency_expires', table_name='idempotency_keys')
    op.drop_index('idx_idempotency_key_hash', table_name='idempotency_keys')
    
    # Drop tables
    op.drop_table('audit_log')
    op.drop_table('idempotency_keys')
