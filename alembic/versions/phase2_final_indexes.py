"""Add performance indexes for Phase 2

Revision ID: phase2_final
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    """Add performance indexes for Phase 2 completion"""
    
    # Performance indexes for pagination
    try:
        op.create_index('idx_test_sessions_created_at', 'test_sessions', ['created_at'])
    except:
        pass  # Index might already exist
        
    try:
        op.create_index('idx_test_sessions_status', 'test_sessions', ['status'])
    except:
        pass
        
    try:
        op.create_index('idx_test_sessions_building', 'test_sessions', ['building_id'])
    except:
        pass
    
    # Composite indexes for filtering
    try:
        op.create_index(
            'idx_audit_user_status', 
            'audits', 
            ['user_id', 'status', 'created_at']
        )
    except:
        pass
    
    # JSONB indexes for vector clocks (if vector_clock column exists)
    try:
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_clock_gin ON test_sessions 
            USING gin (vector_clock jsonb_path_ops)
        """)
    except:
        pass
    
    # Partial index for active items only
    try:
        op.create_index(
            'idx_active_buildings',
            'buildings',
            ['id'],
            postgresql_where=sa.text('is_active = true')
        )
    except:
        pass
    
    # Index for token revocation list performance
    try:
        op.create_index('idx_rtl_expires_at', 'token_revocation_list', ['expires_at'])
    except:
        pass

def downgrade():
    """Remove Phase 2 performance indexes"""
    indexes_to_drop = [
        'idx_test_sessions_created_at',
        'idx_test_sessions_status', 
        'idx_test_sessions_building',
        'idx_audit_user_status',
        'idx_vector_clock_gin',
        'idx_active_buildings',
        'idx_rtl_expires_at'
    ]
    
    for index_name in indexes_to_drop:
        try:
            op.drop_index(index_name)
        except:
            pass  # Index might not exist