"""Add baseline tables for stair pressurization compliance

Revision ID: 003_add_baseline_tables
Revises: 002_add_evidence_flag_columns
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '003_add_baseline_tables'
down_revision = '002_add_evidence_flag_columns'
branch_labels = None
depends_on = None


def upgrade():
    """Add baseline tables for stair pressurization compliance"""
    
    # Create building_configurations table
    op.create_table('building_configurations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        
        # Foreign key to buildings
        sa.Column('building_id', UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        
        # Stair pressurization design parameters
        sa.Column('floor_pressure_setpoints', JSONB, nullable=True,
                 comment="Floor-by-floor pressure setpoints: {\"floor_1\": 45, \"floor_2\": 50, ...}"),
        sa.Column('door_force_limit_newtons', sa.Integer, nullable=True, default=110,
                 comment="Maximum door opening force in Newtons"),
        sa.Column('air_velocity_target_ms', sa.Float, nullable=True, default=1.0,
                 comment="Target air velocity through doorways in m/s"),
        sa.Column('fan_specifications', JSONB, nullable=True,
                 comment="Fan equipment specifications and settings"),
        sa.Column('damper_specifications', JSONB, nullable=True,
                 comment="Damper equipment specifications and settings"),
        sa.Column('relief_air_strategy', sa.String(50), nullable=True,
                 comment="Strategy for relief air management"),
        sa.Column('ce_logic_diagram_path', sa.Text, nullable=True,
                 comment="Path to cause-and-effect logic diagram"),
        sa.Column('manual_override_locations', JSONB, nullable=True,
                 comment="Locations of manual override controls"),
        sa.Column('interfacing_systems', JSONB, nullable=True,
                 comment="Other systems that interface with stair pressurization"),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create baseline_pressure_differentials table
    op.create_table('baseline_pressure_differentials',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        
        # Foreign key to buildings
        sa.Column('building_id', UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        
        # Measurement context
        sa.Column('floor_id', sa.String(50), nullable=False,
                 comment="Floor identifier (e.g., 'floor_1', 'ground', 'level_2')"),
        sa.Column('door_configuration', sa.String(50), nullable=False,
                 comment="Door configuration (e.g., 'all_doors_open', 'all_doors_closed')"),
        sa.Column('pressure_pa', sa.Float, nullable=False,
                 comment="Measured pressure differential in Pascals"),
        sa.Column('measured_date', sa.Date, nullable=False,
                 comment="Date when baseline measurement was taken"),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create baseline_air_velocities table
    op.create_table('baseline_air_velocities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        
        # Foreign key to buildings
        sa.Column('building_id', UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        
        # Measurement context
        sa.Column('doorway_id', sa.String(100), nullable=False,
                 comment="Doorway identifier (e.g., 'stair_door_1', 'main_entrance')"),
        sa.Column('velocity_ms', sa.Float, nullable=False,
                 comment="Measured air velocity in meters per second"),
        sa.Column('measured_date', sa.Date, nullable=False,
                 comment="Date when baseline measurement was taken"),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create baseline_door_forces table
    op.create_table('baseline_door_forces',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        
        # Foreign key to buildings
        sa.Column('building_id', UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        
        # Measurement context
        sa.Column('door_id', sa.String(100), nullable=False,
                 comment="Door identifier (e.g., 'stair_door_1', 'fire_door_2')"),
        sa.Column('force_newtons', sa.Float, nullable=False,
                 comment="Measured door opening force in Newtons"),
        sa.Column('measured_date', sa.Date, nullable=False,
                 comment="Date when baseline measurement was taken"),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Add check constraints for AS 1851-2012 compliance
    op.create_check_constraint(
        'chk_building_config_door_force',
        'building_configurations',
        "door_force_limit_newtons IS NULL OR (door_force_limit_newtons >= 50 AND door_force_limit_newtons <= 110)"
    )
    
    op.create_check_constraint(
        'chk_building_config_air_velocity',
        'building_configurations',
        "air_velocity_target_ms IS NULL OR air_velocity_target_ms >= 1.0"
    )
    
    op.create_check_constraint(
        'chk_baseline_pressure_range',
        'baseline_pressure_differentials',
        "pressure_pa >= 20 AND pressure_pa <= 80"
    )
    
    op.create_check_constraint(
        'chk_baseline_velocity_min',
        'baseline_air_velocities',
        "velocity_ms >= 1.0"
    )
    
    op.create_check_constraint(
        'chk_baseline_door_force_max',
        'baseline_door_forces',
        "force_newtons <= 110"
    )
    
    # Create unique constraints for baseline measurements
    op.create_unique_constraint(
        'uq_baseline_pressure_building_floor_door',
        'baseline_pressure_differentials',
        ['building_id', 'floor_id', 'door_configuration']
    )
    
    op.create_unique_constraint(
        'uq_baseline_velocity_building_doorway',
        'baseline_air_velocities',
        ['building_id', 'doorway_id']
    )
    
    op.create_unique_constraint(
        'uq_baseline_door_force_building_door',
        'baseline_door_forces',
        ['building_id', 'door_id']
    )
    
    # Create indexes for performance
    op.create_index('idx_building_config_building', 'building_configurations', ['building_id'])
    op.create_index('idx_baseline_pressure_building', 'baseline_pressure_differentials', ['building_id'])
    op.create_index('idx_baseline_velocity_building', 'baseline_air_velocities', ['building_id'])
    op.create_index('idx_baseline_door_force_building', 'baseline_door_forces', ['building_id'])
    
    # Composite indexes for completeness queries
    op.create_index('idx_baseline_pressure_floor_door', 'baseline_pressure_differentials', ['building_id', 'floor_id', 'door_configuration'])
    op.create_index('idx_baseline_velocity_doorway', 'baseline_air_velocities', ['building_id', 'doorway_id'])
    op.create_index('idx_baseline_door_force_door', 'baseline_door_forces', ['building_id', 'door_id'])
    
    # Create updated_at triggers for all new tables
    op.execute("""
        CREATE TRIGGER update_building_configurations_updated_at 
        BEFORE UPDATE ON building_configurations 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    
    op.execute("""
        CREATE TRIGGER update_baseline_pressure_differentials_updated_at 
        BEFORE UPDATE ON baseline_pressure_differentials 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    
    op.execute("""
        CREATE TRIGGER update_baseline_air_velocities_updated_at 
        BEFORE UPDATE ON baseline_air_velocities 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    
    op.execute("""
        CREATE TRIGGER update_baseline_door_forces_updated_at 
        BEFORE UPDATE ON baseline_door_forces 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade():
    """Remove baseline tables and related objects"""
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_building_configurations_updated_at ON building_configurations")
    op.execute("DROP TRIGGER IF EXISTS update_baseline_pressure_differentials_updated_at ON baseline_pressure_differentials")
    op.execute("DROP TRIGGER IF EXISTS update_baseline_air_velocities_updated_at ON baseline_air_velocities")
    op.execute("DROP TRIGGER IF EXISTS update_baseline_door_forces_updated_at ON baseline_door_forces")
    
    # Drop indexes
    indexes_to_drop = [
        'idx_building_config_building',
        'idx_baseline_pressure_building',
        'idx_baseline_velocity_building',
        'idx_baseline_door_force_building',
        'idx_baseline_pressure_floor_door',
        'idx_baseline_velocity_doorway',
        'idx_baseline_door_force_door'
    ]
    
    for index_name in indexes_to_drop:
        op.drop_index(index_name)
    
    # Drop unique constraints
    op.drop_constraint('uq_baseline_pressure_building_floor_door', 'baseline_pressure_differentials', type_='unique')
    op.drop_constraint('uq_baseline_velocity_building_doorway', 'baseline_air_velocities', type_='unique')
    op.drop_constraint('uq_baseline_door_force_building_door', 'baseline_door_forces', type_='unique')
    
    # Drop check constraints
    op.drop_constraint('chk_building_config_door_force', 'building_configurations', type_='check')
    op.drop_constraint('chk_building_config_air_velocity', 'building_configurations', type_='check')
    op.drop_constraint('chk_baseline_pressure_range', 'baseline_pressure_differentials', type_='check')
    op.drop_constraint('chk_baseline_velocity_min', 'baseline_air_velocities', type_='check')
    op.drop_constraint('chk_baseline_door_force_max', 'baseline_door_forces', type_='check')
    
    # Drop tables
    op.drop_table('baseline_door_forces')
    op.drop_table('baseline_air_velocities')
    op.drop_table('baseline_pressure_differentials')
    op.drop_table('building_configurations')
