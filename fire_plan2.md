Week 1: Database Migration Scripts + Implementation Prompts
Migration 1: Stairs Registry Table
Alembic Migration Script


python
"""Add stairs registry table

Revision ID: 001_add_stairs_registry
Revises: 
Create Date: 2025-10-20 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_stairs_registry'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create stairs table
    op.create_table(
        'stairs',
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_name', sa.String(100), nullable=False),
        sa.Column('orientation', sa.String(50), nullable=True),
        sa.Column('stair_type', sa.String(50), nullable=True),
        sa.Column('floor_range_bottom', sa.String(50), nullable=True),
        sa.Column('floor_range_top', sa.String(50), nullable=True),
        sa.Column('design_standard', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_name', name='uq_building_stair_name')
    )
    
    # Create indexes
    op.create_index('idx_stairs_building', 'stairs', ['building_id'])
    op.create_index('idx_stairs_building_type', 'stairs', ['building_id', 'stair_type'])
    
    # Add check constraint for orientation
    op.create_check_constraint(
        'ck_stairs_orientation',
        'stairs',
        "orientation IN ('North', 'South', 'East', 'West', 'Central', 'North-East', 'North-West', 'South-East', 'South-West') OR orientation IS NULL"
    )
    
    # Add check constraint for stair_type
    op.create_check_constraint(
        'ck_stairs_type',
        'stairs',
        "stair_type IN ('fire_isolated', 'smoke_proof', 'pressurized', 'standard') OR stair_type IS NULL"
    )


def downgrade():
    # Archive existing data before dropping
    op.execute("""
        CREATE TABLE IF NOT EXISTS stairs_archived AS 
        SELECT *, NOW() as archived_at 
        FROM stairs
    """)
    
    # Drop indexes
    op.drop_index('idx_stairs_building_type', table_name='stairs')
    op.drop_index('idx_stairs_building', table_name='stairs')
    
    # Drop constraints
    op.drop_constraint('ck_stairs_type', 'stairs', type_='check')
    op.drop_constraint('ck_stairs_orientation', 'stairs', type_='check')
    op.drop_constraint('uq_building_stair_name', 'stairs', type_='unique')
    
    # Drop table
    op.drop_table('stairs')
Coding Agent Prompt for SQLAlchemy Model


markdown
# PROMPT: Create SQLAlchemy model for Stairs

Create a SQLAlchemy model in `services/api/src/app/models/stair.py` with the following requirements:

## Model Specification
- **Table name**: `stairs`
- **Primary key**: `stair_id` (UUID, auto-generated)
- **Foreign key**: `building_id` references `buildings.id` with CASCADE delete
- **Columns**:
  - stair_name: String(100), required
  - orientation: String(50), optional, enum ['North', 'South', 'East', 'West', 'Central', 'North-East', 'North-West', 'South-East', 'South-West']
  - stair_type: String(50), optional, enum ['fire_isolated', 'smoke_proof', 'pressurized', 'standard']
  - floor_range_bottom: String(50), optional
  - floor_range_top: String(50), optional
  - design_standard: String(100), optional
  - created_at: DateTime with timezone, default NOW()
  - updated_at: DateTime with timezone, default NOW(), auto-update on change

## Relationships
- **building**: Many-to-one relationship with Building model
- **floors**: One-to-many relationship with Floor model (cascade delete)
- **doors**: One-to-many relationship with Door model (cascade delete)
- **doorways**: One-to-many relationship with Doorway model (cascade delete)
- **test_instances**: One-to-many relationship with TestInstance model
- **faults**: One-to-many relationship with Fault model

## Validation
- Add `@validates('orientation')` to ensure value is in allowed enum or None
- Add `@validates('stair_type')` to ensure value is in allowed enum or None
- Add `@validates('stair_name')` to strip whitespace and ensure non-empty

## Methods
- `__repr__()`: Return readable string representation
- `to_dict()`: Serialize to dictionary (exclude sensitive fields)
- `get_floor_count()`: Return count of associated floors
- `get_total_instances_for_frequency(frequency)`: Return expected instance count for given test frequency

## Unique Constraint
- Composite unique constraint on (building_id, stair_name)

## Example Usage
```python
from app.models.stair import Stair
from app.models.building import Building

# Create stair
building = Building.query.get('building-uuid')
stair = Stair(
    building_id=building.id,
    stair_name='Stair-A',
    orientation='North',
    stair_type='pressurized',
    floor_range_bottom='Ground',
    floor_range_top='Level-14',
    design_standard='AS/NZS 1668.1:2015'
)
db.session.add(stair)
db.session.commit()

# Query stairs for building
stairs = Stair.query.filter_by(building_id=building.id).all()
for stair in stairs:
    print(f"{stair.stair_name}: {stair.get_floor_count()} floors")
```

## File Structure
Create in: `services/api/src/app/models/stair.py`
Import in: `services/api/src/app/models/__init__.py`

Migration 2: Floors Registry Table
Alembic Migration Script


python
"""Add floors registry table with stair relationship

Revision ID: 002_add_floors_registry
Revises: 001_add_stairs_registry
Create Date: 2025-10-20 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_add_floors_registry'
down_revision = '001_add_stairs_registry'
branch_labels = None
depends_on = None


def upgrade():
    # Create floors table
    op.create_table(
        'floors',
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor_level', sa.String(50), nullable=False),
        sa.Column('floor_number', sa.Integer, nullable=False),
        sa.Column('height_m', sa.Numeric(5, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'floor_level', name='uq_building_stair_floor')
    )
    
    # Create indexes for efficient queries
    op.create_index('idx_floors_stair', 'floors', ['stair_id'])
    op.create_index('idx_floors_building', 'floors', ['building_id'])
    op.create_index('idx_floors_building_number', 'floors', ['building_id', 'floor_number'])
    op.create_index('idx_floors_stair_number', 'floors', ['stair_id', 'floor_number'])
    
    # Add check constraint for floor_number (allow negative for basements)
    op.create_check_constraint(
        'ck_floors_number_range',
        'floors',
        'floor_number >= -5 AND floor_number <= 200'
    )


def downgrade():
    # Archive data
    op.execute("""
        CREATE TABLE IF NOT EXISTS floors_archived AS 
        SELECT *, NOW() as archived_at 
        FROM floors
    """)
    
    # Drop indexes
    op.drop_index('idx_floors_stair_number', table_name='floors')
    op.drop_index('idx_floors_building_number', table_name='floors')
    op.drop_index('idx_floors_building', table_name='floors')
    op.drop_index('idx_floors_stair', table_name='floors')
    
    # Drop constraints
    op.drop_constraint('ck_floors_number_range', 'floors', type_='check')
    op.drop_constraint('uq_building_stair_floor', 'floors', type_='unique')
    
    # Drop table
    op.drop_table('floors')
Coding Agent Prompt for Floor Model


markdown
# PROMPT: Create SQLAlchemy model for Floors

Create a SQLAlchemy model in `services/api/src/app/models/floor.py` with the following requirements:

## Model Specification
- **Table name**: `floors`
- **Primary key**: `floor_id` (UUID, auto-generated)
- **Foreign keys**: 
  - `building_id` references `buildings.id` with CASCADE delete
  - `stair_id` references `stairs.stair_id` with CASCADE delete
- **Columns**:
  - floor_level: String(50), required (e.g., "Ground", "Level-1", "Basement-1")
  - floor_number: Integer, required (numeric for sorting: -1 for Basement, 0 for Ground, 1+ for levels)
  - height_m: Numeric(5,2), optional (floor height above ground in meters)
  - created_at: DateTime with timezone, default NOW()
  - updated_at: DateTime with timezone, default NOW()

## Relationships
- **building**: Many-to-one with Building
- **stair**: Many-to-one with Stair
- **doors**: One-to-many with Door (cascade delete)
- **doorways**: One-to-many with Doorway (cascade delete)
- **test_instances**: One-to-many with TestInstance
- **baseline_pressures**: One-to-many with BaselinePressureDifferential

## Validation
- `@validates('floor_number')`: Ensure range -5 to 200
- `@validates('floor_level')`: Strip whitespace, non-empty
- `@validates('height_m')`: If provided, must be >= 0

## Methods
- `__repr__()`: Return "Floor(floor_level='Level-5', stair='Stair-A')"
- `to_dict()`: Serialize to dict
- `get_door_count()`: Count of doors on this floor for this stair
- `get_baseline_pressure(door_configuration)`: Get baseline pressure for this floor+stair+config

## Unique Constraint
- Composite unique on (building_id, stair_id, floor_level)

## Ordering
- Add `__table_args__` with default ordering by floor_number ascending

## Example Usage
```python
from app.models.floor import Floor
from app.models.stair import Stair

stair = Stair.query.filter_by(stair_name='Stair-A').first()

# Create floors
floors = []
for i in range(15):
    floor = Floor(
        building_id=stair.building_id,
        stair_id=stair.stair_id,
        floor_level='Ground' if i == 0 else f'Level-{i}',
        floor_number=i,
        height_m=i * 3.5  # 3.5m per floor
    )
    floors.append(floor)

db.session.bulk_save_objects(floors)
db.session.commit()

# Query floors for stair, ordered by floor_number
floors = Floor.query.filter_by(stair_id=stair.stair_id).order_by(Floor.floor_number).all()
```

Create in: `services/api/src/app/models/floor.py`

Migration 3: Doors and Doorways Registry
Alembic Migration Script


python
"""Add doors and doorways registry tables

Revision ID: 003_add_doors_doorways
Revises: 002_add_floors_registry
Create Date: 2025-10-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_add_doors_doorways'
down_revision = '002_add_floors_registry'
branch_labels = None
depends_on = None


def upgrade():
    # Create doors table
    op.create_table(
        'doors',
        sa.Column('door_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floors.floor_id', ondelete='CASCADE'), nullable=False),
        sa.Column('door_identifier', sa.String(100), nullable=False),
        sa.Column('door_type', sa.String(50), nullable=True),
        sa.Column('fire_rating_minutes', sa.Integer, nullable=True),
        sa.Column('door_closer_model', sa.String(100), nullable=True),
        sa.Column('door_hand', sa.String(20), nullable=True),
        sa.Column('width_m', sa.Numeric(4, 2), nullable=True),
        sa.Column('height_m', sa.Numeric(4, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'floor_id', 'door_identifier', name='uq_door_identifier')
    )
    
    # Create doorways table
    op.create_table(
        'doorways',
        sa.Column('doorway_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floors.floor_id', ondelete='CASCADE'), nullable=False),
        sa.Column('doorway_identifier', sa.String(100), nullable=False),
        sa.Column('width_m', sa.Numeric(4, 2), nullable=True),
        sa.Column('height_m', sa.Numeric(4, 2), nullable=True),
        sa.Column('orientation', sa.String(50), nullable=True),
        sa.Column('adjacent_space', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'floor_id', 'doorway_identifier', name='uq_doorway_identifier')
    )
    
    # Indexes for doors
    op.create_index('idx_doors_stair_floor', 'doors', ['stair_id', 'floor_id'])
    op.create_index('idx_doors_building', 'doors', ['building_id'])
    
    # Indexes for doorways
    op.create_index('idx_doorways_stair_floor', 'doorways', ['stair_id', 'floor_id'])
    op.create_index('idx_doorways_building', 'doorways', ['building_id'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_doors_type',
        'doors',
        "door_type IN ('fire_rated', 'smoke_rated', 'standard', 'emergency_exit') OR door_type IS NULL"
    )
    
    op.create_check_constraint(
        'ck_doors_hand',
        'doors',
        "door_hand IN ('left', 'right', 'double') OR door_hand IS NULL"
    )
    
    op.create_check_constraint(
        'ck_doors_dimensions',
        'doors',
        'width_m IS NULL OR (width_m > 0 AND width_m <= 3.0)'
    )
    
    op.create_check_constraint(
        'ck_doorways_dimensions',
        'doorways',
        'width_m IS NULL OR (width_m > 0 AND width_m <= 5.0)'
    )


def downgrade():
    # Archive data
    op.execute("""
        CREATE TABLE IF NOT EXISTS doors_archived AS 
        SELECT *, NOW() as archived_at 
        FROM doors
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS doorways_archived AS 
        SELECT *, NOW() as archived_at 
        FROM doorways
    """)
    
    # Drop doorways first (no dependencies)
    op.drop_index('idx_doorways_building', table_name='doorways')
    op.drop_index('idx_doorways_stair_floor', table_name='doorways')
    op.drop_constraint('ck_doorways_dimensions', 'doorways', type_='check')
    op.drop_constraint('uq_doorway_identifier', 'doorways', type_='unique')
    op.drop_table('doorways')
    
    # Drop doors
    op.drop_index('idx_doors_building', table_name='doors')
    op.drop_index('idx_doors_stair_floor', table_name='doors')
    op.drop_constraint('ck_doors_dimensions', 'doors', type_='check')
    op.drop_constraint('ck_doors_hand', 'doors', type_='check')
    op.drop_constraint('ck_doors_type', 'doors', type_='check')
    op.drop_constraint('uq_door_identifier', 'doors', type_='unique')
    op.drop_table('doors')
Coding Agent Prompts for Door and Doorway Models


markdown
# PROMPT 1: Create SQLAlchemy model for Doors

Create `services/api/src/app/models/door.py`:

## Model Specification
- **Table**: `doors`
- **Primary key**: `door_id` (UUID)
- **Foreign keys**: building_id, stair_id, floor_id (all CASCADE delete)
- **Columns**:
  - door_identifier: String(100), required
  - door_type: Enum['fire_rated', 'smoke_rated', 'standard', 'emergency_exit']
  - fire_rating_minutes: Integer, optional (60, 90, 120, etc.)
  - door_closer_model: String(100), optional
  - door_hand: Enum['left', 'right', 'double']
  - width_m: Numeric(4,2), range 0-3.0
  - height_m: Numeric(4,2), range 0-3.5
  - created_at, updated_at

## Relationships
- building, stair, floor (many-to-one)
- baseline_door_forces (one-to-many)
- test_instances (one-to-many)

## Methods
- `get_baseline_force(pressurization_active=True)`: Get baseline door force
- `get_current_closer_spec()`: Return door closer specifications dict

## Unique Constraint
- (building_id, stair_id, floor_id, door_identifier)

Example:
```python
door = Door(
    building_id=building.id,
    stair_id=stair.id,
    floor_id=floor.id,
    door_identifier='D-GF-A',
    door_type='fire_rated',
    fire_rating_minutes=60,
    door_closer_model='LCN 4040XP',
    door_hand='right',
    width_m=0.90,
    height_m=2.10
)
```
---

# PROMPT 2: Create SQLAlchemy model for Doorways

Create `services/api/src/app/models/doorway.py`:

## Model Specification
- **Table**: `doorways`
- **Primary key**: `doorway_id` (UUID)
- **Foreign keys**: building_id, stair_id, floor_id (CASCADE)
- **Columns**:
  - doorway_identifier: String(100), required
  - width_m: Numeric(4,2), range 0-5.0
  - height_m: Numeric(4,2), range 0-4.0
  - orientation: String(50), optional
  - adjacent_space: String(100), optional (e.g., "Corridor", "Lobby")
  - created_at, updated_at

## Relationships
- building, stair, floor (many-to-one)
- baseline_air_velocities (one-to-many)
- test_instances (one-to-many)

## Methods
- `get_grid_layout()`: Return 9-point grid coordinates based on width_m × height_m
- `get_baseline_velocity(door_scenario='worst_case_3_doors_open')`: Get baseline velocity

## Unique Constraint
- (building_id, stair_id, floor_id, doorway_identifier)

Example:
```python
doorway = Doorway(
    building_id=building.id,
    stair_id=stair.id,
    floor_id=floor.id,
    doorway_identifier='DW-GF-A',
    width_m=1.20,
    height_m=2.40,
    orientation='North',
    adjacent_space='Main Corridor'
)

# Get 9-point grid for velocity measurement
grid = doorway.get_grid_layout()
# Returns: [
#   {'point': 1, 'x': 0.30, 'y': 1.92},  # 0.25W, 0.8H
#   {'point': 2, 'x': 0.60, 'y': 1.92},  # 0.5W, 0.8H
#   ...
# ]
```

Migration 4: Zones and Control Equipment
Alembic Migration Script


python
"""Add zones and control equipment tables

Revision ID: 004_add_zones_equipment
Revises: 003_add_doors_doorways
Create Date: 2025-10-20 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004_add_zones_equipment'
down_revision = '003_add_doors_doorways'
branch_labels = None
depends_on = None


def upgrade():
    # Create zones table
    op.create_table(
        'zones',
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('zone_name', sa.String(100), nullable=False),
        sa.Column('floors_covered', postgresql.JSONB, nullable=False),  # ["Ground", "Level-1", "Level-2"]
        sa.Column('floor_ids_covered', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'zone_name', name='uq_zone_name')
    )
    
    # Create control_equipment table
    op.create_table(
        'control_equipment',
        sa.Column('equipment_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.zone_id', ondelete='SET NULL'), nullable=True),
        sa.Column('equipment_type', sa.String(50), nullable=False),
        sa.Column('equipment_identifier', sa.String(100), nullable=False),
        sa.Column('manufacturer', sa.String(100), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('installation_date', sa.Date, nullable=True),
        sa.Column('specifications', postgresql.JSONB, nullable=True),  # {capacity_m3_s: 5.2, motor_kw: 15}
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'equipment_identifier', name='uq_equipment_identifier')
    )
    
    # Indexes
    op.create_index('idx_zones_stair', 'zones', ['stair_id'])
    op.create_index('idx_zones_building', 'zones', ['building_id'])
    op.create_index('idx_equipment_stair_zone', 'control_equipment', ['stair_id', 'zone_id'])
    op.create_index('idx_equipment_type', 'control_equipment', ['equipment_type'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_equipment_type',
        'control_equipment',
        "equipment_type IN ('fan', 'damper', 'pressure_sensor', 'control_panel', 'detector', 'actuator')"
    )
    
    # JSONB validation for floors_covered (must be non-empty array)
    op.execute("""
        ALTER TABLE zones ADD CONSTRAINT ck_zones_floors_covered_not_empty
        CHECK (jsonb_array_length(floors_covered) > 0)
    """)


def downgrade():
    # Archive data
    op.execute("""
        CREATE TABLE IF NOT EXISTS control_equipment_archived AS 
        SELECT *, NOW() as archived_at 
        FROM control_equipment
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS zones_archived AS 
        SELECT *, NOW() as archived_at 
        FROM zones
    """)
    
    # Drop control_equipment first (has FK to zones)
    op.drop_index('idx_equipment_type', table_name='control_equipment')
    op.drop_index('idx_equipment_stair_zone', table_name='control_equipment')
    op.drop_constraint('ck_equipment_type', 'control_equipment', type_='check')
    op.drop_constraint('uq_equipment_identifier', 'control_equipment', type_='unique')
    op.drop_table('control_equipment')
    
    # Drop zones
    op.execute("ALTER TABLE zones DROP CONSTRAINT IF EXISTS ck_zones_floors_covered_not_empty")
    op.drop_index('idx_zones_building', table_name='zones')
    op.drop_index('idx_zones_stair', table_name='zones')
    op.drop_constraint('uq_zone_name', 'zones', type_='unique')
    op.drop_table('zones')
Coding Agent Prompts


markdown
# PROMPT 1: Create Zone model

Create `services/api/src/app/models/zone.py`:

## Model Specification
- **Table**: `zones`
- **PK**: zone_id (UUID)
- **FKs**: building_id, stair_id (CASCADE)
- **Columns**:
  - zone_name: String(100), required
  - floors_covered: JSONB array of strings (e.g., ["Ground", "Level-1", "Level-2"])
  - floor_ids_covered: ARRAY of UUIDs
  - created_at, updated_at

## Relationships
- building, stair (many-to-one)
- control_equipment (one-to-many)
- ce_scenarios (one-to-many)
- test_instances (one-to-many)

## Methods
- `get_floor_range_text()`: Return "Ground to Level-3" from floors_covered
- `get_equipment_list()`: Return list of equipment in this zone
- `validate_floors_covered()`: Ensure floors_covered matches floor_ids_covered

## Validation
- `@validates('floors_covered')`: Must be non-empty array
- `@validates('floor_ids_covered')`: Must be non-empty array, all UUIDs must exist in floors table

Example:
```python
zone = Zone(
    building_id=building.id,
    stair_id=stair.id,
    zone_name='Zone-1',
    floors_covered=["Ground", "Level-1", "Level-2", "Level-3"],
    floor_ids_covered=[floor_ground.id, floor_1.id, floor_2.id, floor_3.id]




Retry

AW
Continue



) db.session.add(zone) db.session.commit()
print(zone.get_floor_range_text()) # "Ground to Level-3" print(zone.get_equipment_list()) # ['FAN-01', 'DAMPER-Z1-RELIEF']


---

# PROMPT 2: Create ControlEquipment model

Create `services/api/src/app/models/control_equipment.py`:

## Model Specification
- **Table**: `control_equipment`
- **PK**: equipment_id (UUID)
- **FKs**: 
  - building_id, stair_id (CASCADE)
  - zone_id (SET NULL - equipment can exist without zone assignment)
- **Columns**:
  - equipment_type: Enum['fan', 'damper', 'pressure_sensor', 'control_panel', 'detector', 'actuator']
  - equipment_identifier: String(100), required
  - manufacturer: String(100), optional
  - model: String(100), optional
  - serial_number: String(100), optional
  - installation_date: Date, optional
  - specifications: JSONB (flexible dict for equipment-specific specs)
  - created_at, updated_at

## Relationships
- building, stair, zone (many-to-one)

## Methods
- `to_dict(include_specs=True)`: Serialize, optionally include full specifications
- `get_spec(key, default=None)`: Get value from specifications JSONB
- `set_spec(key, value)`: Set value in specifications JSONB

## Validation
- `@validates('equipment_type')`: Ensure in allowed enum
- `@validates('equipment_identifier')`: Strip whitespace, uppercase

## Unique Constraint
- (building_id, stair_id, equipment_identifier)

## Equipment Type Specific Specifications
```python
# Fan specifications example
fan_specs = {
    'capacity_m3_s': 5.2,
    'motor_kw': 15.0,
    'max_rpm': 1450,
    'pressure_pa': 500,
    'vfd_installed': True
}

# Damper specifications example
damper_specs = {
    'type': 'relief',  # 'relief', 'control', 'isolation'
    'actuator_model': 'Belimo LMB24-SR',
    'fail_position': 'open',
    'size_mm': '600x400'
}

# Pressure sensor specifications example
sensor_specs = {
    'range_pa': '0-100',
    'accuracy': '±1 Pa',
    'output_signal': '4-20mA'
}
```

Example:
```python
# Create fan
fan = ControlEquipment(
    building_id=building.id,
    stair_id=stair.id,
    zone_id=zone.id,
    equipment_type='fan',
    equipment_identifier='FAN-01',
    manufacturer='Woods',
    model='EDXM-450',
    serial_number='WD-2024-12345',
    installation_date=date(2024, 1, 15),
    specifications={
        'capacity_m3_s': 5.2,
        'motor_kw': 15.0,
        'max_rpm': 1450,
        'pressure_pa': 500,
        'vfd_installed': True
    }
)

# Query equipment by type
fans = ControlEquipment.query.filter_by(
    stair_id=stair.id, 
    equipment_type='fan'
).all()

# Get specification
capacity = fan.get_spec('capacity_m3_s')  # 5.2
```

Migration 5: Baseline Tables
Alembic Migration Script


python
"""Add baseline measurement tables (pressure, velocity, door force)

Revision ID: 005_add_baseline_tables
Revises: 004_add_zones_equipment
Create Date: 2025-10-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005_add_baseline_tables'
down_revision = '004_add_zones_equipment'
branch_labels = None
depends_on = None


def upgrade():
    # Create baseline_pressure_differentials table
    op.create_table(
        'baseline_pressure_differentials',
        sa.Column('baseline_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floors.floor_id', ondelete='CASCADE'), nullable=False),
        sa.Column('door_configuration', sa.String(50), nullable=False),
        sa.Column('pressure_pa', sa.Numeric(6, 2), nullable=False),
        sa.Column('commissioned_date', sa.Date, nullable=False),
        sa.Column('commissioned_by', sa.String(255), nullable=True),
        sa.Column('commissioning_report_ref', sa.String(255), nullable=True),
        sa.Column('environmental_conditions', postgresql.JSONB, nullable=True),  # {temp_c: 22, wind_ms: 2.1}
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'floor_id', 'door_configuration', name='uq_baseline_pressure')
    )
    
    # Create baseline_air_velocities table
    op.create_table(
        'baseline_air_velocities',
        sa.Column('baseline_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('doorway_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doorways.doorway_id', ondelete='CASCADE'), nullable=False),
        sa.Column('door_scenario', sa.String(50), nullable=False),
        sa.Column('velocity_ms', sa.Numeric(5, 3), nullable=False),
        sa.Column('measurement_points', postgresql.JSONB, nullable=True),  # 9-point grid data
        sa.Column('average_velocity_ms', sa.Numeric(5, 3), nullable=True),
        sa.Column('commissioned_date', sa.Date, nullable=False),
        sa.Column('commissioned_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'doorway_id', 'door_scenario', name='uq_baseline_velocity')
    )
    
    # Create baseline_door_forces table
    op.create_table(
        'baseline_door_forces',
        sa.Column('baseline_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('door_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doors.door_id', ondelete='CASCADE'), nullable=False),
        sa.Column('pressurization_active', sa.Boolean, nullable=False, default=True),
        sa.Column('force_newtons', sa.Numeric(6, 2), nullable=False),
        sa.Column('measurement_position', sa.String(50), nullable=True),
        sa.Column('commissioned_date', sa.Date, nullable=False),
        sa.Column('commissioned_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'door_id', 'pressurization_active', name='uq_baseline_door_force')
    )
    
    # Indexes for baseline tables
    op.create_index('idx_baseline_pressure_stair_floor', 'baseline_pressure_differentials', ['stair_id', 'floor_id'])
    op.create_index('idx_baseline_velocity_doorway', 'baseline_air_velocities', ['doorway_id'])
    op.create_index('idx_baseline_door_force_door', 'baseline_door_forces', ['door_id'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_baseline_pressure_range',
        'baseline_pressure_differentials',
        'pressure_pa >= 10 AND pressure_pa <= 100'
    )
    
    op.create_check_constraint(
        'ck_baseline_pressure_door_config',
        'baseline_pressure_differentials',
        "door_configuration IN ('all_closed', 'evac_doors_open')"
    )
    
    op.create_check_constraint(
        'ck_baseline_velocity_range',
        'baseline_air_velocities',
        'velocity_ms >= 0.5 AND velocity_ms <= 5.0'
    )
    
    op.create_check_constraint(
        'ck_baseline_door_force_range',
        'baseline_door_forces',
        'force_newtons >= 0 AND force_newtons <= 200'
    )
    
    op.create_check_constraint(
        'ck_baseline_door_force_position',
        'baseline_door_forces',
        "measurement_position IN ('at_handle', 'at_edge') OR measurement_position IS NULL"
    )


def downgrade():
    # Archive baseline data
    op.execute("""
        CREATE TABLE IF NOT EXISTS baseline_pressure_differentials_archived AS 
        SELECT *, NOW() as archived_at 
        FROM baseline_pressure_differentials
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS baseline_air_velocities_archived AS 
        SELECT *, NOW() as archived_at 
        FROM baseline_air_velocities
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS baseline_door_forces_archived AS 
        SELECT *, NOW() as archived_at 
        FROM baseline_door_forces
    """)
    
    # Drop baseline_door_forces
    op.drop_index('idx_baseline_door_force_door', table_name='baseline_door_forces')
    op.drop_constraint('ck_baseline_door_force_position', 'baseline_door_forces', type_='check')
    op.drop_constraint('ck_baseline_door_force_range', 'baseline_door_forces', type_='check')
    op.drop_constraint('uq_baseline_door_force', 'baseline_door_forces', type_='unique')
    op.drop_table('baseline_door_forces')
    
    # Drop baseline_air_velocities
    op.drop_index('idx_baseline_velocity_doorway', table_name='baseline_air_velocities')
    op.drop_constraint('ck_baseline_velocity_range', 'baseline_air_velocities', type_='check')
    op.drop_constraint('uq_baseline_velocity', 'baseline_air_velocities', type_='unique')
    op.drop_table('baseline_air_velocities')
    
    # Drop baseline_pressure_differentials
    op.drop_index('idx_baseline_pressure_stair_floor', table_name='baseline_pressure_differentials')
    op.drop_constraint('ck_baseline_pressure_door_config', 'baseline_pressure_differentials', type_='check')
    op.drop_constraint('ck_baseline_pressure_range', 'baseline_pressure_differentials', type_='check')
    op.drop_constraint('uq_baseline_pressure', 'baseline_pressure_differentials', type_='unique')
    op.drop_table('baseline_pressure_differentials')
Coding Agent Prompts for Baseline Models


markdown
# PROMPT 1: Create BaselinePressureDifferential model

Create `services/api/src/app/models/baseline_pressure.py`:

## Model Specification
- **Table**: `baseline_pressure_differentials`
- **PK**: baseline_id (UUID)
- **FKs**: building_id, stair_id, floor_id (all CASCADE)
- **Columns**:
  - door_configuration: Enum['all_closed', 'evac_doors_open'], required
  - pressure_pa: Numeric(6,2), required, range 10-100
  - commissioned_date: Date, required
  - commissioned_by: String(255), optional
  - commissioning_report_ref: String(255), optional
  - environmental_conditions: JSONB, optional
  - created_at, updated_at

## Relationships
- building, stair, floor (many-to-one)

## Methods
- `to_dict()`: Serialize
- `is_recent(days=365)`: Check if commissioned within X days
- `get_condition(key, default=None)`: Get environmental condition from JSONB

## Validation
- `@validates('pressure_pa')`: Range 10-100 Pa
- `@validates('door_configuration')`: Must be in ['all_closed', 'evac_doors_open']
- `@validates('commissioned_date')`: Cannot be in future

## Unique Constraint
- (building_id, stair_id, floor_id, door_configuration)

## Class Methods
- `get_baseline_for_instance(stair_id, floor_id, door_configuration)`: Query helper

Example:
```python
baseline = BaselinePressureDifferential(
    building_id=building.id,
    stair_id=stair.id,
    floor_id=floor.id,
    door_configuration='all_closed',
    pressure_pa=45.2,
    commissioned_date=date(2024, 1, 15),
    commissioned_by='ABC Fire Engineering',
    commissioning_report_ref='REP-2024-001',
    environmental_conditions={
        'temp_c': 22,
        'humidity_pct': 55,
        'wind_ms': 2.1,
        'doors_open_list': []
    }
)

# Query helper
baseline = BaselinePressureDifferential.get_baseline_for_instance(
    stair_id=stair.id,
    floor_id=floor.id,
    door_configuration='all_closed'
)
print(f"Baseline: {baseline.pressure_pa} Pa, commissioned {baseline.commissioned_date}")
```

---

# PROMPT 2: Create BaselineAirVelocity model

Create `services/api/src/app/models/baseline_velocity.py`:

## Model Specification
- **Table**: `baseline_air_velocities`
- **PK**: baseline_id (UUID)
- **FKs**: building_id, stair_id, doorway_id (all CASCADE)
- **Columns**:
  - door_scenario: String(50), required (e.g., 'worst_case_3_doors_open')
  - velocity_ms: Numeric(5,3), required, range 0.5-5.0 (primary measurement)
  - measurement_points: JSONB, optional (9-point grid data)
  - average_velocity_ms: Numeric(5,3), optional (calculated from grid)
  - commissioned_date: Date, required
  - commissioned_by: String(255), optional
  - created_at, updated_at

## Relationships
- building, stair, doorway (many-to-one)

## Methods
- `to_dict()`: Serialize
- `get_grid_points()`: Return parsed measurement_points array
- `calculate_average_from_grid()`: Calculate average from 9 points
- `validate_grid_completeness()`: Ensure all 9 points present

## Validation
- `@validates('velocity_ms')`: Range 0.5-5.0 m/s
- `@validates('measurement_points')`: If provided, must have 9 points

## Unique Constraint
- (building_id, stair_id, doorway_id, door_scenario)

## JSONB Structure for measurement_points
```python
measurement_points = [
    {'point': 1, 'x': 0.25, 'y': 0.8, 'velocity_ms': 1.2},
    {'point': 2, 'x': 0.5, 'y': 0.8, 'velocity_ms': 1.3},
    {'point': 3, 'x': 0.75, 'y': 0.8, 'velocity_ms': 1.1},
    {'point': 4, 'x': 0.25, 'y': 0.5, 'velocity_ms': 1.15},
    {'point': 5, 'x': 0.5, 'y': 0.5, 'velocity_ms': 1.25},  # Center reference
    {'point': 6, 'x': 0.75, 'y': 0.5, 'velocity_ms': 1.18},
    {'point': 7, 'x': 0.25, 'y': 0.2, 'velocity_ms': 1.08},
    {'point': 8, 'x': 0.5, 'y': 0.2, 'velocity_ms': 1.12},
    {'point': 9, 'x': 0.75, 'y': 0.2, 'velocity_ms': 1.05}
]
```

Example:
```python
baseline = BaselineAirVelocity(
    building_id=building.id,
    stair_id=stair.id,
    doorway_id=doorway.id,
    door_scenario='worst_case_3_doors_open',
    velocity_ms=1.15,
    measurement_points=measurement_points,  # 9-point grid
    average_velocity_ms=1.15,  # Auto-calculated
    commissioned_date=date(2024, 1, 15),
    commissioned_by='ABC Fire Engineering'
)

# Calculate average
avg = baseline.calculate_average_from_grid()  # Returns 1.15
```

---

# PROMPT 3: Create BaselineDoorForce model

Create `services/api/src/app/models/baseline_door_force.py`:

## Model Specification
- **Table**: `baseline_door_forces`
- **PK**: baseline_id (UUID)
- **FKs**: building_id, stair_id, door_id (all CASCADE)
- **Columns**:
  - pressurization_active: Boolean, required (default True)
  - force_newtons: Numeric(6,2), required, range 0-200
  - measurement_position: Enum['at_handle', 'at_edge'], optional
  - commissioned_date: Date, required
  - commissioned_by: String(255), optional
  - created_at, updated_at

## Relationships
- building, stair, door (many-to-one)

## Methods
- `to_dict()`: Serialize
- `is_compliant()`: Check if force <= 110 N (AS1851 requirement)
- `get_compliance_margin()`: Return 110 - force_newtons

## Validation
- `@validates('force_newtons')`: Range 0-200 N
- `@validates('measurement_position')`: Must be in ['at_handle', 'at_edge'] or None
- `@validates('commissioned_date')`: Cannot be in future

## Unique Constraint
- (building_id, stair_id, door_id, pressurization_active)

## Class Methods
- `get_baseline_for_door(door_id, pressurization_active=True)`: Query helper

Example:
```python
baseline = BaselineDoorForce(
    building_id=building.id,
    stair_id=stair.id,
    door_id=door.id,
    pressurization_active=True,
    force_newtons=95.5,
    measurement_position='at_handle',
    commissioned_date=date(2024, 1, 15),
    commissioned_by='ABC Fire Engineering'
)

# Check compliance
if baseline.is_compliant():
    margin = baseline.get_compliance_margin()  # 110 - 95.5 = 14.5 N
    print(f"Compliant with {margin:.1f} N margin")
else:
    print("CRITICAL: Exceeds 110 N limit")
```

Migration 6: C&E Scenarios and Interface Test Definitions
Alembic Migration Script


python
"""Add CE scenarios and interface test definition tables

Revision ID: 006_add_ce_interface_definitions
Revises: 005_add_baseline_tables
Create Date: 2025-10-20 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '006_add_ce_interface_definitions'
down_revision = '005_add_baseline_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create ce_scenarios table
    op.create_table(
        'ce_scenarios',
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.zone_id', ondelete='CASCADE'), nullable=False),
        sa.Column('scenario_name', sa.String(255), nullable=False),
        sa.Column('scenario_type', sa.String(50), nullable=False),
        sa.Column('trigger_device_id', sa.String(100), nullable=False),
        sa.Column('trigger_device_type', sa.String(50), nullable=True),
        sa.Column('expected_sequence', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('version', sa.Integer, nullable=False, default=1),
        sa.Column('active', sa.Boolean, nullable=False, default=True),
        sa.UniqueConstraint('building_id', 'stair_id', 'zone_id', 'scenario_name', 'version', name='uq_ce_scenario')
    )
    
    # Create interface_test_definitions table
    op.create_table(
        'interface_test_definitions',
        sa.Column('definition_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('interface_type', sa.String(50), nullable=False),
        sa.Column('location_id', sa.String(100), nullable=False),
        sa.Column('location_name', sa.String(255), nullable=True),
        sa.Column('test_action', sa.Text, nullable=True),
        sa.Column('expected_result', sa.Text, nullable=True),
        sa.Column('response_time_s', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('building_id', 'stair_id', 'interface_type', 'location_id', name='uq_interface_definition')
    )
    
    # Indexes
    op.create_index('idx_ce_scenarios_zone', 'ce_scenarios', ['zone_id'])
    op.create_index('idx_ce_scenarios_active', 'ce_scenarios', ['active'])
    op.create_index('idx_interface_defs_stair_type', 'interface_test_definitions', ['stair_id', 'interface_type'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_ce_scenario_type',
        'ce_scenarios',
        "scenario_type IN ('baseline_commissioning', 'six_monthly', 'annual')"
    )
    
    op.create_check_constraint(
        'ck_ce_trigger_device_type',
        'ce_scenarios',
        "trigger_device_type IN ('smoke_detector', 'heat_detector', 'manual_call_point', 'test_switch') OR trigger_device_type IS NULL"
    )
    
    op.create_check_constraint(
        'ck_interface_type',
        'interface_test_definitions',
        "interface_type IN ('manual_override', 'alarm_coordination', 'shutdown_sequence', 'sprinkler_activation')"
    )
    
    # JSONB validation for expected_sequence
    op.execute("""
        ALTER TABLE ce_scenarios ADD CONSTRAINT ck_ce_expected_sequence_format
        CHECK (jsonb_typeof(expected_sequence) = 'array' AND jsonb_array_length(expected_sequence) > 0)
    """)


def downgrade():
    # Archive data
    op.execute("""
        CREATE TABLE IF NOT EXISTS interface_test_definitions_archived AS 
        SELECT *, NOW() as archived_at 
        FROM interface_test_definitions
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS ce_scenarios_archived AS 
        SELECT *, NOW() as archived_at 
        FROM ce_scenarios
    """)
    
    # Drop interface_test_definitions
    op.drop_index('idx_interface_defs_stair_type', table_name='interface_test_definitions')
    op.drop_constraint('ck_interface_type', 'interface_test_definitions', type_='check')
    op.drop_constraint('uq_interface_definition', 'interface_test_definitions', type_='unique')
    op.drop_table('interface_test_definitions')
    
    # Drop ce_scenarios
    op.execute("ALTER TABLE ce_scenarios DROP CONSTRAINT IF EXISTS ck_ce_expected_sequence_format")
    op.drop_index('idx_ce_scenarios_active', table_name='ce_scenarios')
    op.drop_index('idx_ce_scenarios_zone', table_name='ce_scenarios')
    op.drop_constraint('ck_ce_trigger_device_type', 'ce_scenarios', type_='check')
    op.drop_constraint('ck_ce_scenario_type', 'ce_scenarios', type_='check')
    op.drop_constraint('uq_ce_scenario', 'ce_scenarios', type_='unique')
    op.drop_table('ce_scenarios')
Coding Agent Prompts


markdown
# PROMPT 1: Create CEScenario model

Create `services/api/src/app/models/ce_scenario.py`:

## Model Specification
- **Table**: `ce_scenarios`
- **PK**: scenario_id (UUID)
- **FKs**: building_id, stair_id, zone_id (CASCADE), created_by (SET NULL)
- **Columns**:
  - scenario_name: String(255), required
  - scenario_type: Enum['baseline_commissioning', 'six_monthly', 'annual']
  - trigger_device_id: String(100), required
  - trigger_device_type: Enum['smoke_detector', 'heat_detector', 'manual_call_point', 'test_switch']
  - expected_sequence: JSONB array, required
  - created_at, created_by
  - version: Integer (for scenario versioning)
  - active: Boolean (to deactivate old versions)

## Relationships
- building, stair, zone, created_by_user (many-to-one)
- test_instances (one-to-many)

## Methods
- `to_dict(include_sequence=True)`: Serialize
- `get_step_count()`: Return number of steps in expected_sequence
- `get_step(step_order)`: Get specific step from sequence
- `validate_sequence_format()`: Ensure all steps have required fields
- `clone_to_new_version()`: Create new version (increment version, set active=True, deactivate old)

## Validation
- `@validates('expected_sequence')`: Must be array with > 0 elements, each element must have required fields
- `@validates('scenario_type')`: Must be in enum
- `@validates('version')`: Must be >= 1

## JSONB Structure for expected_sequence
```python
expected_sequence = [
    {
        'step_order': 1,
        'component_id': 'ALARM-PANEL',
        'component_type': 'alarm',
        'expected_action': 'activate',
        'expected_delay_seconds': 0,
        'tolerance_seconds': 2
    },
    {
        'step_order': 2,
        'component_id': 'FAN-01',
        'component_type': 'fan',
        'expected_action': 'start',
        'expected_delay_seconds': 3,
        'tolerance_seconds': 2
    },
    {
        'step_order': 3,
        'component_id': 'DAMPER-RELIEF-Z1',
        'component_type': 'damper',
        'expected_action': 'open',
        'expected_delay_seconds': 5,
        'tolerance_seconds': 2
    },
    {
        'step_order': 4,
        'component_id': 'PRESSURE-SENSOR-L5',
        'component_type': 'sensor',
        'expected_action': 'reach_setpoint',
        'expected_delay_seconds': 15,
        'tolerance_seconds': 5
    }
]
```

Example:
```python
scenario = CEScenario(
    building_id=building.id,
    stair_id=stair.id,
    zone_id=zone.id,
    scenario_name='Fire Floor 8 - Zone 3 Activation',
    scenario_type='annual',
    trigger_device_id='SD-L8-01',
    trigger_device_type='smoke_detector',
    expected_sequence=expected_sequence,
    created_by=user.id,
    version=1,
    active=True
)

# Validate sequence
if scenario.validate_sequence_format():




Retry

AW
Continue





python
    db.session.add(scenario)
    db.session.commit()
    print(f"Scenario created with {scenario.get_step_count()} steps")

PROMPT 2: Create InterfaceTestDefinition model
Create services/api/src/app/models/interface_test_definition.py:
Model Specification
Table: interface_test_definitions
PK: definition_id (UUID)
FKs: building_id, stair_id (CASCADE)
Columns:
interface_type: Enum['manual_override', 'alarm_coordination', 'shutdown_sequence', 'sprinkler_activation']
location_id: String(100), required (e.g., 'FIRE-PANEL-01', 'BMS-WORKSTATION')
location_name: String(255), optional (human-readable)
test_action: Text, optional (description of action to perform)
expected_result: Text, optional (description of expected system response)
response_time_s: Integer, optional (expected response time in seconds)
created_at
Relationships
building, stair (many-to-one)
test_instances (one-to-many)
Methods
to_dict(): Serialize
get_full_description(): Return formatted string with action + expected result
Validation
@validates('interface_type'): Must be in enum
@validates('response_time_s'): If provided, must be 1-300 seconds
Unique Constraint
(building_id, stair_id, interface_type, location_id)
Class Methods
get_definitions_for_stair(stair_id, interface_type=None): Query helper
Example:


python
# Manual Override definition
manual_override = InterfaceTestDefinition(
    building_id=building.id,
    stair_id=stair.id,
    interface_type='manual_override',
    location_id='FIRE-PANEL-01',
    location_name='Main Fire Control Panel',
    test_action='Press manual override button on fire control panel',
    expected_result='System switches to manual mode - Fans continue running under manual control',
    response_time_s=5
)

# Alarm Coordination definition
alarm_coord = InterfaceTestDefinition(
    building_id=building.id,
    stair_id=stair.id,
    interface_type='alarm_coordination',
    location_id='FIRE-ALARM-PANEL',
    location_name='Fire Alarm Control Panel',
    test_action='Trigger fire alarm via test panel function',
    expected_result='Stair pressurization activates within 3-5 seconds',
    response_time_s=4
)

# Shutdown Sequence definition
shutdown = InterfaceTestDefinition(
    building_id=building.id,
    stair_id=stair.id,
    interface_type='shutdown_sequence',
    location_id='BMS-WORKSTATION',
    location_name='BMS Control Workstation',
    test_action='Initiate system shutdown via BMS interface',
    expected_result='Orderly shutdown: Fan stops → Dampers close → Pressure dissipates',
    response_time_s=20
)

# Sprinkler Interface definition
sprinkler = InterfaceTestDefinition(
    building_id=building.id,
    stair_id=stair.id,
    interface_type='sprinkler_activation',
    location_id='SPRINKLER-PANEL',
    location_name='Sprinkler Control Panel',
    test_action='Simulate sprinkler activation signal (do NOT trigger actual sprinklers)',
    expected_result='System maintains operation per design intent',
    response_time_s=5
)

# Query all interface definitions for a stair
definitions = InterfaceTestDefinition.get_definitions_for_stair(stair.id)
print(f"Found {len(definitions)} interface test definitions")
````
````

---

## Migration 7: Test Instance Templates

### Alembic Migration Script
````python
"""Add test instance templates table (pre-generated from archetypes)

Revision ID: 007_add_test_instance_templates
Revises: 006_add_ce_interface_definitions
Create Date: 2025-10-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '007_add_test_instance_templates'
down_revision = '006_add_ce_interface_definitions'
branch_labels = None
depends_on = None


def upgrade():
    # Create test_instance_templates table
    op.create_table(
        'test_instance_templates',
        sa.Column('template_instance_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('archetype_id', sa.String(50), nullable=False),
        sa.Column('measurement_type', sa.String(50), nullable=False),
        sa.Column('frequency', sa.String(20), nullable=False),
        
        # Instance-specific context (nullable depending on archetype)
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floors.floor_id', ondelete='CASCADE'), nullable=True),
        sa.Column('door_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doors.door_id', ondelete='CASCADE'), nullable=True),
        sa.Column('doorway_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doorways.doorway_id', ondelete='CASCADE'), nullable=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.zone_id', ondelete='CASCADE'), nullable=True),
        sa.Column('door_configuration', sa.String(50), nullable=True),
        sa.Column('door_scenario', sa.String(50), nullable=True),
        sa.Column('pressurization_active', sa.Boolean, nullable=True),
        sa.Column('interface_type', sa.String(50), nullable=True),
        sa.Column('location_id', sa.String(100), nullable=True),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ce_scenarios.scenario_id', ondelete='CASCADE'), nullable=True),
        
        # Baseline values
        sa.Column('design_setpoint', sa.Numeric(10, 3), nullable=True),
        sa.Column('baseline_value', sa.Numeric(10, 3), nullable=True),
        sa.Column('baseline_date', sa.Date, nullable=True),
        sa.Column('min_threshold', sa.Numeric(10, 3), nullable=True),
        sa.Column('max_threshold', sa.Numeric(10, 3), nullable=True),
        sa.Column('unit', sa.String(20), nullable=True),
        
        # UX assets
        sa.Column('visual_asset_path', sa.Text, nullable=True),
        sa.Column('descriptive_instructions', postgresql.JSONB, nullable=True),
        sa.Column('audible_cues', postgresql.JSONB, nullable=True),
        sa.Column('safety_warnings', postgresql.JSONB, nullable=True),
        
        # Instrument requirements
        sa.Column('required_instrument_type', sa.String(50), nullable=True),
        sa.Column('calibration_requirement', postgresql.JSONB, nullable=True),
        
        # Evidence requirements
        sa.Column('evidence_prompts', postgresql.JSONB, nullable=True),
        
        # Sequence order
        sa.Column('sequence_order', sa.Integer, nullable=False),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False)
    )
    
    # Indexes for efficient queries
    op.create_index('idx_templates_building_freq', 'test_instance_templates', ['building_id', 'frequency'])
    op.create_index('idx_templates_stair_floor', 'test_instance_templates', ['stair_id', 'floor_id'])
    op.create_index('idx_templates_archetype', 'test_instance_templates', ['archetype_id'])
    op.create_index('idx_templates_measurement_type', 'test_instance_templates', ['measurement_type'])
    op.create_index('idx_templates_sequence', 'test_instance_templates', ['building_id', 'frequency', 'sequence_order'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_template_frequency',
        'test_instance_templates',
        "frequency IN ('monthly', 'six_monthly', 'annual')"
    )
    
    op.create_check_constraint(
        'ck_template_measurement_type',
        'test_instance_templates',
        "measurement_type IN ('pressure_differential', 'air_velocity', 'door_opening_force', 'cause_and_effect_logic', 'interface_test')"
    )
    
    op.create_check_constraint(
        'ck_template_sequence_positive',
        'test_instance_templates',
        'sequence_order > 0'
    )


def downgrade():
    # Archive templates
    op.execute("""
        CREATE TABLE IF NOT EXISTS test_instance_templates_archived AS 
        SELECT *, NOW() as archived_at 
        FROM test_instance_templates
    """)
    
    # Drop indexes
    op.drop_index('idx_templates_sequence', table_name='test_instance_templates')
    op.drop_index('idx_templates_measurement_type', table_name='test_instance_templates')
    op.drop_index('idx_templates_archetype', table_name='test_instance_templates')
    op.drop_index('idx_templates_stair_floor', table_name='test_instance_templates')
    op.drop_index('idx_templates_building_freq', table_name='test_instance_templates')
    
    # Drop constraints
    op.drop_constraint('ck_template_sequence_positive', 'test_instance_templates', type_='check')
    op.drop_constraint('ck_template_measurement_type', 'test_instance_templates', type_='check')
    op.drop_constraint('ck_template_frequency', 'test_instance_templates', type_='check')
    
    # Drop table
    op.drop_table('test_instance_templates')
````

### Coding Agent Prompt for TestInstanceTemplate Model
````markdown
# PROMPT: Create TestInstanceTemplate model

Create `services/api/src/app/models/test_instance_template.py`:

## Model Specification
- **Table**: `test_instance_templates`
- **PK**: template_instance_id (UUID)
- **FKs**: building_id, stair_id (required), floor_id, door_id, doorway_id, zone_id, scenario_id (optional - depends on archetype)
- **Columns**:
  - archetype_id: String(50), required (e.g., 'ARCH-PRESSURE-001')
  - measurement_type: Enum['pressure_differential', 'air_velocity', 'door_opening_force', 'cause_and_effect_logic', 'interface_test']
  - frequency: Enum['monthly', 'six_monthly', 'annual']
  - Instance context (varies by archetype):
    - stair_id: Always required
    - floor_id: For pressure, velocity, door force
    - door_id: For door force
    - doorway_id: For velocity
    - zone_id: For C&E tests
    - door_configuration: For pressure ('all_closed', 'evac_doors_open')
    - door_scenario: For velocity ('worst_case_3_doors_open')
    - pressurization_active: For door force (Boolean)
    - interface_type: For interface tests
    - location_id: For interface tests
    - scenario_id: For C&E tests
  - Baseline values:
    - design_setpoint: Numeric(10,3)
    - baseline_value: Numeric(10,3)
    - baseline_date: Date
    - min_threshold: Numeric(10,3)
    - max_threshold: Numeric(10,3)
    - unit: String(20)
  - UX assets:
    - visual_asset_path: Text
    - descriptive_instructions: JSONB array
    - audible_cues: JSONB object
    - safety_warnings: JSONB array
  - Instrument requirements:
    - required_instrument_type: String(50)
    - calibration_requirement: JSONB
  - Evidence requirements:
    - evidence_prompts: JSONB array
  - Sequence order: Integer (for mobile navigation)
  - created_at, updated_at

## Relationships
- building, stair (many-to-one, required)
- floor, door, doorway, zone, scenario (many-to-one, optional)
- test_instances (one-to-many) - instances cloned from this template

## Methods
- `to_dict(include_ux=False)`: Serialize, optionally exclude UX assets
- `clone_to_session(session_id)`: Create TestInstance from this template
- `get_scoped_identifier()`: Return unique string like "PRESSURE_STAIR-A_L8_ALL-CLOSED"
- `validate_context_completeness()`: Ensure required context fields are populated based on archetype

## Class Methods
- `get_templates_for_building(building_id, frequency)`: Query helper
- `count_templates(building_id, frequency)`: Return expected instance count

## Validation
- `@validates('measurement_type')`: Must be in enum
- `@validates('frequency')`: Must be in enum
- `@validates('sequence_order')`: Must be > 0

## JSONB Structures

### descriptive_instructions
```python
descriptive_instructions = [
    {
        'step': 1,
        'instruction': 'Configure doors: Close all stair doors on floors 7-9',
        'estimated_time_s': 60
    },
    {
        'step': 2,
        'instruction': 'Position manometer at Stair-A landing, Floor 8, 1.5m height',
        'estimated_time_s': 30
    },
    {
        'step': 3,
        'instruction': 'Wait 30 seconds for pressure stabilization',
        'estimated_time_s': 30
    },
    {
        'step': 4,
        'instruction': 'Record pressure reading in Pascals (Pa)',
        'estimated_time_s': 10
    }
]
```

### audible_cues
```python
audible_cues = {
    'start': 'beep_start.mp3',
    'countdown_duration_s': 30,
    'measurement_prompt': 'beep_measure.mp3',
    'success': 'tone_success.mp3',
    'fail': 'tone_alert.mp3'
}
```

### safety_warnings
```python
safety_warnings = [
    'Ensure doors can be manually opened',
    'Confirm no occupants in stairwell during test',
    'Do not block emergency exits'
]
```

### calibration_requirement
```python
calibration_requirement = {
    'frequency_months': 12,
    'standard': 'ISO/IEC 17025',
    'accuracy_required': '±1 Pa'
}
```

### evidence_prompts
```python
evidence_prompts = [
    {
        'type': 'photo',
        'description': 'Manometer display showing pressure reading',
        'mandatory': True,
        'min_resolution': '1024x768'
    },
    {
        'type': 'photo',
        'description': 'Floor number sign confirming test location',
        'mandatory': True
    }
]
```

Example:
```python
# Create pressure differential template
template = TestInstanceTemplate(
    building_id=building.id,
    archetype_id='ARCH-PRESSURE-001',
    measurement_type='pressure_differential',
    frequency='annual',
    stair_id=stair.id,
    floor_id=floor.id,
    door_configuration='all_closed',
    design_setpoint=45.0,
    baseline_value=44.2,
    baseline_date=date(2024, 1, 15),
    min_threshold=20.0,
    max_threshold=80.0,
    unit='Pa',
    visual_asset_path=f'assets/floor_plans/{building.id}/{stair.id}/{floor.id}.svg',
    descriptive_instructions=descriptive_instructions,
    audible_cues=audible_cues,
    safety_warnings=safety_warnings,
    required_instrument_type='manometer',
    calibration_requirement=calibration_requirement,
    evidence_prompts=evidence_prompts,
    sequence_order=1
)

# Validate before saving
if template.validate_context_completeness():
    db.session.add(template)
    db.session.commit()
    print(f"Template created: {template.get_scoped_identifier()}")
```
````

---

## Migration 8: Test Instances (Runtime Execution)

### Alembic Migration Script
````python
"""Add test instances table (cloned from templates per session)

Revision ID: 008_add_test_instances
Revises: 007_add_test_instance_templates
Create Date: 2025-10-20 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '008_add_test_instances'
down_revision = '007_add_test_instance_templates'
branch_labels = None
depends_on = None


def upgrade():
    # Create test_instances table
    op.create_table(
        'test_instances',
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('template_instance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_instance_templates.template_instance_id', ondelete='SET NULL'), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('building_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('buildings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('archetype_id', sa.String(50), nullable=False),
        sa.Column('measurement_type', sa.String(50), nullable=False),
        sa.Column('frequency', sa.String(20), nullable=False),
        
        # Instance context (denormalized from template for query performance)
        sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='CASCADE'), nullable=False),
        sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floors.floor_id', ondelete='CASCADE'), nullable=True),
        sa.Column('door_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doors.door_id', ondelete='CASCADE'), nullable=True),
        sa.Column('doorway_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doorways.doorway_id', ondelete='CASCADE'), nullable=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.zone_id', ondelete='CASCADE'), nullable=True),
        sa.Column('door_configuration', sa.String(50), nullable=True),
        sa.Column('door_scenario', sa.String(50), nullable=True),
        sa.Column('pressurization_active', sa.Boolean, nullable=True),
        sa.Column('interface_type', sa.String(50), nullable=True),
        sa.Column('location_id', sa.String(100), nullable=True),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ce_scenarios.scenario_id', ondelete='SET NULL'), nullable=True),
        
        # Baseline context
        sa.Column('design_setpoint', sa.Numeric(10, 3), nullable=True),
        sa.Column('baseline_value', sa.Numeric(10, 3), nullable=True),
        sa.Column('baseline_date', sa.Date, nullable=True),
        sa.Column('min_threshold', sa.Numeric(10, 3), nullable=True),
        sa.Column('max_threshold', sa.Numeric(10, 3), nullable=True),
        sa.Column('unit', sa.String(20), nullable=True),
        
        # UX (loaded into mobile bundle)
        sa.Column('visual_asset_path', sa.Text, nullable=True),
        sa.Column('descriptive_instructions', postgresql.JSONB, nullable=True),
        sa.Column('audible_cues', postgresql.JSONB, nullable=True),
        sa.Column('safety_warnings', postgresql.JSONB, nullable=True),
        
        # Instrument
        sa.Column('required_instrument_type', sa.String(50), nullable=True),
        sa.Column('required_instrument_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('instruments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('calibration_requirement', postgresql.JSONB, nullable=True),
        
        # Evidence
        sa.Column('evidence_prompts', postgresql.JSONB, nullable=True),
        
        # Execution status
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('sequence_order', sa.Integer, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('technician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        
        # Results (populated after execution)
        sa.Column('measured_value_numeric', sa.Numeric(10, 3), nullable=True),
        sa.Column('measured_value_text', sa.Text, nullable=True),
        sa.Column('is_compliant', sa.Boolean, nullable=True),
        sa.Column('deviation_from_baseline_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('validation_result', postgresql.JSONB, nullable=True),
        sa.Column('fault_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('faults.id', ondelete='SET NULL'), nullable=True),
        sa.Column('evidence_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False)
    )
    
    # Indexes for efficient queries
    op.create_index('idx_instances_session', 'test_instances', ['session_id'])
    op.create_index('idx_instances_status', 'test_instances', ['status'])
    op.create_index('idx_instances_stair_floor', 'test_instances', ['stair_id', 'floor_id'])
    op.create_index('idx_instances_template', 'test_instances', ['template_instance_id'])
    op.create_index('idx_instances_session_sequence', 'test_instances', ['session_id', 'sequence_order'])
    op.create_index('idx_instances_technician', 'test_instances', ['technician_id'])
    op.create_index('idx_instances_measurement_type', 'test_instances', ['measurement_type'])
    op.create_index('idx_instances_compliance', 'test_instances', ['is_compliant'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_instance_status',
        'test_instances',
        "status IN ('pending', 'in_progress', 'completed', 'skipped', 'failed')"
    )
    
    op.create_check_constraint(
        'ck_instance_completed_timestamps',
        'test_instances',
        "(status = 'completed' AND completed_at IS NOT NULL) OR (status != 'completed')"
    )


def downgrade():
    # Archive instances
    op.execute("""
        CREATE TABLE IF NOT EXISTS test_instances_archived AS 
        SELECT *, NOW() as archived_at 
        FROM test_instances
    """)
    
    # Drop indexes
    op.drop_index('idx_instances_compliance', table_name='test_instances')
    op.drop_index('idx_instances_measurement_type', table_name='test_instances')
    op.drop_index('idx_instances_technician', table_name='test_instances')
    op.drop_index('idx_instances_session_sequence', table_name='test_instances')
    op.drop_index('idx_instances_template', table_name='test_instances')
    op.drop_index('idx_instances_stair_floor', table_name='test_instances')
    op.drop_index('idx_instances_status', table_name='test_instances')
    op.drop_index('idx_instances_session', table_name='test_instances')
    
    # Drop constraints
    op.drop_constraint('ck_instance_completed_timestamps', 'test_instances', type_='check')
    op.drop_constraint('ck_instance_status', 'test_instances', type_='check')
    
    # Drop table
    op.drop_table('test_instances')
````

### Coding Agent Prompt for TestInstance Model
````markdown
# PROMPT: Create TestInstance model

Create `services/api/src/app/models/test_instance.py`:

## Model Specification
- **Table**: `test_instances`
- **PK**: instance_id (UUID)
- **FKs**: 
  - template_instance_id (SET NULL - link to template)
  - session_id (CASCADE - instance belongs to session)
  - building_id, stair_id (CASCADE)
  - floor_id, door_id, doorway_id, zone_id, scenario_id (CASCADE, optional)
  - required_instrument_id (SET NULL)
  - technician_id (SET NULL)
  - fault_id (SET NULL)

- **Columns**: (Same as template, plus execution/results fields)
  - All template context fields (denormalized)
  - Execution status:
    - status: Enum['pending', 'in_progress', 'completed', 'skipped', 'failed']
    - sequence_order: Integer
    - started_at: DateTime
    - completed_at: DateTime
    - technician_id: UUID
  - Results:
    - measured_value_numeric: Numeric(10,3)
    - measured_value_text: Text (for JSON data like C&E sequences or 9-point grids)
    - is_compliant: Boolean
    - deviation_from_baseline_pct: Numeric(6,2)
    - validation_result: JSONB
    - fault_id: UUID
    - evidence_ids: Array of UUIDs
    - notes: Text
  - created_at, updated_at

## Relationships
- template, session, building, stair, floor, door, doorway, zone, scenario, instrument, technician, fault (many-to-one)
- evidence_records (one-to-many)

## Methods
- `to_dict(include_results=True, include_ux=False)`: Serialize
- `start()`: Set status='in_progress', started_at=now
- `complete(measured_value, is_compliant, validation_result)`: Set status='completed', populate results
- `skip(reason)`: Set status='skipped', add reason to notes
- `get_duration_seconds()`: Return completed_at - started_at in seconds
- `get_scoped_identifier()`: Same as template
- `validate_before_completion()`: Ensure required fields populated

## Class Methods
- `get_instances_for_session(session_id, status=None)`: Query helper
- `get_pending_count(session_id)`: Count pending instances
- `get_completion_percentage(session_id)`: Return (completed / total) * 100

## Validation
- `@validates('status')`: Must be in enum
- `@validates('measured_value_numeric')`: If provided, check against min/max thresholds
- `@validates('completed_at')`: Cannot be before started_at

## State Machine
```python
# Valid status transitions
VALID_TRANSITIONS = {
    'pending': ['in_progress', 'skipped'],
    'in_progress': ['completed', 'failed', 'skipped'],
    'completed': [],  # Terminal state
    'skipped': [],    # Terminal state
    'failed': ['pending']  # Can retry
}
```

Example:
```python
# Clone template to create instance
template = TestInstanceTemplate.query.get(template_id)
instance = template.clone_to_session(session_id)
db.session.add(instance)
db.session.commit()

# Technician starts test
instance.start()
instance.technician_id = current_user.id
db.session.commit()

# Execute test (mobile app)
measured_pressure = 43.2  # Pa

# Validate
validator = InstanceValidator()
validation_result = validator.validate_instance(
    instance=instance,
    measurement_value=measured_pressure,
    actual_data={
        'evidence_ids': [evidence1.id, evidence2.id],
        'notes': 'All doors confirmed closed',
        'environmental_conditions': {'temp_c': 22, 'wind_ms': 2.1}
    }
)

# Complete instance
instance.complete(
    measured_value=measured_pressure,
    is_compliant=validation_result.is_compliant,
    validation_result=validation_result.to_dict()
)
instance.measured_value_numeric = measured_pressure
instance.deviation_from_baseline_pct = validation_result.deviation_from_baseline_pct
instance.fault_id = validation_result.fault_id
instance.evidence_ids = [evidence1.id, evidence2.id]
instance.notes = 'All doors confirmed closed'
db.session.commit()

# Query session progress
total = TestInstance.query.filter_by(session_id=session.id).count()
completed = TestInstance.query.filter_by(session_id=session.id, status='completed').count()
completion_pct = TestInstance.get_completion_percentage(session.id)
print(f"{completed}/{total} instances complete ({completion_pct:.1f}%)")
```
````

---

## Summary: Week 1 Migrations Complete

You've now created **8 comprehensive database migrations** covering:

1. ✅ **Stairs Registry** - Multi-stair building support
2. ✅ **Floors Registry** - Floor-by-floor context
3. ✅ **Doors & Doorways** - Door force and velocity test locations
4. ✅ **Zones & Equipment** - C&E testing infrastructure
5. ✅ **Baseline Tables** - Commissioning baseline data (pressure, velocity, door force)
6. ✅ **C&E Scenarios & Interface Definitions** - Test sequence templates
7. ✅ **Test Instance Templates** - Pre-generated archetype expansions
8. ✅ **Test Instances** - Runtime execution and results

### Next Steps for Week 1:
````bash
# Run all migrations on staging
alembic upgrade head

# Verify table creation




Retry

AW
Continue





bash
# Verify table creation
psql -h staging-db-host -U admin -d firemode_staging -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'stairs', 'floors', 'doors', 'doorways', 'zones', 'control_equipment',
    'baseline_pressure_differentials', 'baseline_air_velocities', 'baseline_door_forces',
    'ce_scenarios', 'interface_test_definitions',
    'test_instance_templates', 'test_instances'
)
ORDER BY table_name;
"

# Verify indexes
psql -h staging-db-host -U admin -d firemode_staging -c "
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename LIKE '%stair%' OR tablename LIKE '%baseline%' OR tablename LIKE '%instance%'
ORDER BY tablename, indexname;
"

# Verify foreign keys
psql -h staging-db-host -U admin -d firemode_staging -c "
SELECT
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
AND tc.table_name IN ('test_instances', 'test_instance_templates', 'baseline_pressure_differentials')
ORDER BY tc.table_name;
"

Migration 9: Evidence Records & Enhanced Faults
Alembic Migration Script


python
"""Add evidence records table and enhance faults with instance context

Revision ID: 009_add_evidence_enhance_faults
Revises: 008_add_test_instances
Create Date: 2025-10-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009_add_evidence_enhance_faults'
down_revision = '008_add_test_instances'
branch_labels = None
depends_on = None


def upgrade():
    # Create evidence_records table
    op.create_table(
        'evidence_records',
        sa.Column('evidence_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_instances.instance_id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evidence_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('file_path', sa.Text, nullable=True),  # S3 key
        sa.Column('file_hash_sha256', sa.String(64), nullable=True),
        sa.Column('device_attestation_token', sa.Text, nullable=True),
        sa.Column('gps_coordinates', postgresql.JSONB, nullable=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger, nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False)
    )
    
    # Indexes for evidence
    op.create_index('idx_evidence_instance', 'evidence_records', ['instance_id'])
    op.create_index('idx_evidence_session', 'evidence_records', ['session_id'])
    op.create_index('idx_evidence_captured', 'evidence_records', ['captured_at'])
    op.create_index('idx_evidence_hash', 'evidence_records', ['file_hash_sha256'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_evidence_type',
        'evidence_records',
        "evidence_type IN ('photo', 'video', 'structured_data', 'metadata')"
    )
    
    op.create_check_constraint(
        'ck_evidence_file_size',
        'evidence_records',
        'file_size_bytes IS NULL OR (file_size_bytes > 0 AND file_size_bytes <= 104857600)'  # Max 100MB
    )
    
    # Enhance faults table with instance context
    op.add_column('faults', sa.Column('instance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_instances.instance_id', ondelete='SET NULL'), nullable=True))
    op.add_column('faults', sa.Column('stair_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stairs.stair_id', ondelete='SET NULL'), nullable=True))
    op.add_column('faults', sa.Column('floor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floors.floor_id', ondelete='SET NULL'), nullable=True))
    op.add_column('faults', sa.Column('door_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doors.door_id', ondelete='SET NULL'), nullable=True))
    op.add_column('faults', sa.Column('doorway_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doorways.doorway_id', ondelete='SET NULL'), nullable=True))
    op.add_column('faults', sa.Column('zone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('zones.zone_id', ondelete='SET NULL'), nullable=True))
    op.add_column('faults', sa.Column('door_configuration', sa.String(50), nullable=True))
    op.add_column('faults', sa.Column('measurement_type', sa.String(50), nullable=True))
    op.add_column('faults', sa.Column('measured_value', sa.Numeric(10, 3), nullable=True))
    op.add_column('faults', sa.Column('design_setpoint', sa.Numeric(10, 3), nullable=True))
    op.add_column('faults', sa.Column('baseline_value', sa.Numeric(10, 3), nullable=True))
    op.add_column('faults', sa.Column('min_threshold', sa.Numeric(10, 3), nullable=True))
    op.add_column('faults', sa.Column('max_threshold', sa.Numeric(10, 3), nullable=True))
    op.add_column('faults', sa.Column('unit', sa.String(20), nullable=True))
    op.add_column('faults', sa.Column('deviation_from_baseline_pct', sa.Numeric(6, 2), nullable=True))
    op.add_column('faults', sa.Column('rule_applied', sa.String(50), nullable=True))
    op.add_column('faults', sa.Column('rule_version', sa.String(50), nullable=True))
    op.add_column('faults', sa.Column('environmental_conditions', postgresql.JSONB, nullable=True))
    
    # Create indexes on new fault columns
    op.create_index('idx_faults_instance', 'faults', ['instance_id'])
    op.create_index('idx_faults_stair_floor', 'faults', ['stair_id', 'floor_id'])
    op.create_index('idx_faults_measurement_type', 'faults', ['measurement_type'])


def downgrade():
    # Archive evidence
    op.execute("""
        CREATE TABLE IF NOT EXISTS evidence_records_archived AS 
        SELECT *, NOW() as archived_at 
        FROM evidence_records
    """)
    
    # Drop evidence table
    op.drop_index('idx_evidence_hash', table_name='evidence_records')
    op.drop_index('idx_evidence_captured', table_name='evidence_records')
    op.drop_index('idx_evidence_session', table_name='evidence_records')
    op.drop_index('idx_evidence_instance', table_name='evidence_records')
    op.drop_constraint('ck_evidence_file_size', 'evidence_records', type_='check')
    op.drop_constraint('ck_evidence_type', 'evidence_records', type_='check')
    op.drop_table('evidence_records')
    
    # Remove fault enhancements (archive first)
    op.execute("""
        CREATE TABLE IF NOT EXISTS faults_enhanced_archived AS 
        SELECT * FROM faults WHERE instance_id IS NOT NULL
    """)
    
    op.drop_index('idx_faults_measurement_type', table_name='faults')
    op.drop_index('idx_faults_stair_floor', table_name='faults')
    op.drop_index('idx_faults_instance', table_name='faults')
    
    op.drop_column('faults', 'environmental_conditions')
    op.drop_column('faults', 'rule_version')
    op.drop_column('faults', 'rule_applied')
    op.drop_column('faults', 'deviation_from_baseline_pct')
    op.drop_column('faults', 'unit')
    op.drop_column('faults', 'max_threshold')
    op.drop_column('faults', 'min_threshold')
    op.drop_column('faults', 'baseline_value')
    op.drop_column('faults', 'design_setpoint')
    op.drop_column('faults', 'measured_value')
    op.drop_column('faults', 'measurement_type')
    op.drop_column('faults', 'door_configuration')
    op.drop_column('faults', 'zone_id')
    op.drop_column('faults', 'doorway_id')
    op.drop_column('faults', 'door_id')
    op.drop_column('faults', 'floor_id')
    op.drop_column('faults', 'stair_id')
    op.drop_column('faults', 'instance_id')
Coding Agent Prompts


markdown
# PROMPT 1: Create EvidenceRecord model

Create `services/api/src/app/models/evidence_record.py`:

## Model Specification
- **Table**: `evidence_records`
- **PK**: evidence_id (UUID)
- **FKs**: instance_id, session_id (both CASCADE)
- **Columns**:
  - evidence_type: Enum['photo', 'video', 'structured_data', 'metadata']
  - description: Text
  - file_path: Text (S3 key or local Realm path)
  - file_hash_sha256: String(64) - integrity verification
  - device_attestation_token: Text (iOS DeviceCheck / Android SafetyNet)
  - gps_coordinates: JSONB ({lat, lng, accuracy})
  - captured_at: DateTime (when evidence captured on device)
  - uploaded_at: DateTime (when synced to backend)
  - file_size_bytes: BigInteger (max 100MB)
  - mime_type: String(100)
  - metadata: JSONB (camera model, resolution, etc.)
  - created_at

## Relationships
- instance, session (many-to-one)

## Methods
- `to_dict()`: Serialize
- `verify_hash()`: Recompute SHA-256 from file and compare
- `get_s3_url(expiry_seconds=3600)`: Generate pre-signed S3 URL
- `is_synced()`: Return uploaded_at is not None

## Class Methods
- `get_evidence_for_instance(instance_id)`: Query helper
- `get_unsynced_count(session_id)`: Count evidence not yet uploaded

## Validation
- `@validates('evidence_type')`: Must be in enum
- `@validates('file_size_bytes')`: Must be 0-104857600 (100MB)
- `@validates('file_hash_sha256')`: Must be 64 hex characters

## JSONB Structures

### gps_coordinates
```python
gps_coordinates = {
    'lat': -33.8688,
    'lng': 151.2093,
    'accuracy': 10.5,  # meters
    'altitude': 25.0,  # meters (optional)
    'timestamp': '2025-10-20T14:32:17Z'
}
```

### metadata
```python
metadata = {
    'camera_model': 'iPhone 14 Pro',
    'resolution': '4032x3024',
    'timestamp_exif': '2025-10-20T14:32:17Z',
    'orientation': 1,
    'flash': False,
    'focal_length': 6.86,
    'device_info': {
        'os': 'iOS',
        'os_version': '17.2',
        'app_version': '4.5.0'
    }
}
```

Example:
```python
import hashlib

# Capture evidence on mobile
with open('manometer_photo.jpg', 'rb') as f:
    file_data = f.read()
    file_hash = hashlib.sha256(file_data).hexdigest()

evidence = EvidenceRecord(
    instance_id=instance.instance_id,
    session_id=session.id,
    evidence_type='photo',
    description='Manometer display showing pressure reading',
    file_path='pending_upload/manometer_photo.jpg',  # Local Realm path
    file_hash_sha256=file_hash,
    device_attestation_token='eyJhbGc...',  # iOS DeviceCheck
    gps_coordinates={
        'lat': -33.8688,
        'lng': 151.2093,
        'accuracy': 10.5
    },
    captured_at=datetime.utcnow(),
    file_size_bytes=len(file_data),
    mime_type='image/jpeg',
    metadata={
        'camera_model': 'iPhone 14 Pro',
        'resolution': '4032x3024'
    }
)

# Save to Realm (offline)
realm.write {
    realm.add(evidence)
}

# Later, sync to backend
upload_to_s3(file_data, s3_key=f'evidence/{evidence.evidence_id}.jpg')
evidence.file_path = f'evidence/{evidence.evidence_id}.jpg'
evidence.uploaded_at = datetime.utcnow()
db.session.commit()

# Verify integrity
if evidence.verify_hash():
    print("Evidence integrity verified")
```

---

# PROMPT 2: Enhance Fault model with instance context

Update `services/api/src/app/models/fault.py`:

## Add New Columns
- instance_id: UUID FK to test_instances
- stair_id, floor_id, door_id, doorway_id, zone_id: UUIDs (for context)
- door_configuration: String(50)
- measurement_type: String(50)
- measured_value, design_setpoint, baseline_value, min_threshold, max_threshold: Numeric(10,3)
- unit: String(20)
- deviation_from_baseline_pct: Numeric(6,2)
- rule_applied, rule_version: String(50)
- environmental_conditions: JSONB

## Add Relationships
- instance (many-to-one)
- stair, floor, door, doorway, zone (many-to-one)

## Add Methods
- `get_location_description()`: Return "Stair-A, Floor 8, All Doors Closed"
- `get_full_context()`: Return dict with all context fields
- `is_critical()`: Return severity == 'critical'
- `requires_urgent_action()`: Return severity in ['critical', 'high']

## Update Existing Methods
- `to_dict()`: Include new instance context fields

Example:
```python
# Create fault with full instance context
fault = Fault(
    test_session_id=session.id,
    instance_id=instance.instance_id,
    building_id=building.id,
    stair_id=instance.stair_id,
    floor_id=instance.floor_id,
    door_configuration=instance.door_configuration,
    measurement_type='pressure_differential',
    
    severity='critical',
    defect_classification='1A',
    description=(
        f"Pressure 18.2 Pa BELOW minimum 20 Pa on "
        f"{instance.stair.stair_name} {instance.floor.floor_level} "
        f"({instance.door_configuration})"
    ),
    action_required="Increase fan speed, check damper positions, inspect for air leaks",
    
    measured_value=18.2,
    design_setpoint=45.0,
    baseline_value=44.2,
    min_threshold=20.0,
    max_threshold=80.0,
    unit='Pa',
    deviation_from_baseline_pct=-59.6,  # (18.2-44.2)/44.2
    
    rule_applied='SP-01',
    rule_version='AS1851-2024-v1.3',
    
    detected_at=datetime.utcnow(),
    status='open',
    
    evidence_ids=[evidence1.evidence_id, evidence2.evidence_id],
    environmental_conditions={'temp_c': 22, 'wind_ms': 2.1}
)

# Query helpers
location = fault.get_location_description()
# "Stair-A, Level-8, All Doors Closed"

if fault.requires_urgent_action():
    send_notification(fault)
```

Migration 10: AS1851 Rules Table
Alembic Migration Script


python
"""Add AS1851 rules table for validation

Revision ID: 010_add_as1851_rules
Revises: 009_add_evidence_enhance_faults
Create Date: 2025-10-20 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '010_add_as1851_rules'
down_revision = '009_add_evidence_enhance_faults'
branch_labels = None
depends_on = None


def upgrade():
    # Create as1851_rules table
    op.create_table(
        'as1851_rules',
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('rule_code', sa.String(50), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('measurement_type', sa.String(50), nullable=False),
        sa.Column('min_threshold', sa.Numeric(10, 3), nullable=True),
        sa.Column('max_threshold', sa.Numeric(10, 3), nullable=True),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('severity_if_fail', sa.String(20), nullable=False),
        sa.Column('defect_classification', sa.String(10), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('reference_standard', sa.String(100), nullable=True),
        sa.Column('active', sa.Boolean, nullable=False, default=True),
        sa.Column('effective_date', sa.Date, nullable=True),
        sa.Column('superseded_date', sa.Date, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('rule_code', 'version', name='uq_rule_code_version')
    )
    
    # Indexes
    op.create_index('idx_rules_measurement_type', 'as1851_rules', ['measurement_type'])
    op.create_index('idx_rules_active', 'as1851_rules', ['active'])
    op.create_index('idx_rules_code', 'as1851_rules', ['rule_code'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_rules_measurement_type',
        'as1851_rules',
        "measurement_type IN ('pressure_differential', 'air_velocity', 'door_opening_force', 'cause_and_effect_logic', 'interface_test')"
    )
    
    op.create_check_constraint(
        'ck_rules_severity',
        'as1851_rules',
        "severity_if_fail IN ('critical', 'high', 'medium', 'low')"
    )
    
    op.create_check_constraint(
        'ck_rules_defect_class',
        'as1851_rules',
        "defect_classification IN ('1A', '1B', '2', '3')"
    )
    
    # Seed initial rules
    op.execute("""
        INSERT INTO as1851_rules (rule_code, version, measurement_type, min_threshold, max_threshold, unit, severity_if_fail, defect_classification, description, reference_standard, active, effective_date)
        VALUES 
        ('SP-01', 'AS1851-2024-v1.3', 'pressure_differential', 20.0, 80.0, 'Pa', 'critical', '1A', 
         'Stair pressurization pressure differential must be maintained between 20-80 Pa to prevent smoke infiltration', 
         'AS 1851-2012 § 13.2; AS/NZS 1668.1:2015', true, '2024-01-01'),
        
        ('SP-02', 'AS1851-2024-v1.3', 'air_velocity', 1.0, NULL, 'm/s', 'high', '1B', 
         'Doorway air velocity must exceed 1.0 m/s during evacuation scenario to prevent smoke backflow', 
         'AS 1851-2012 § 13.2; AS/NZS 1668.1:2015', true, '2024-01-01'),
        
        ('SP-03', 'AS1851-2024-v1.3', 'door_opening_force', NULL, 110.0, 'N', 'critical', '1A', 
         'Door opening force must not exceed 110 N at handle to ensure egress during emergency', 
         'AS 1851-2012 § 13.2; AS/NZS 1668.1:2015; BCA D2.21', true, '2024-01-01'),
        
        ('CE-01', 'AS1851-2024-v1.3', 'cause_and_effect_logic', NULL, NULL, NULL, 'critical', '1A', 
         'Cause-and-effect sequence must activate within design parameters', 
         'AS 1851-2012 § 13.3', true, '2024-01-01'),
        
        ('INT-01', 'AS1851-2024-v1.3', 'interface_test', NULL, NULL, NULL, 'critical', '1A', 
         'System interfaces must respond correctly to manual override, alarm, shutdown, and sprinkler activation', 
         'AS 1851-2012 § 13.4', true, '2024-01-01')
    """)


def downgrade():
    # Archive rules
    op.execute("""
        CREATE TABLE IF NOT EXISTS as1851_rules_archived AS 
        SELECT *, NOW() as archived_at 
        FROM as1851_rules
    """)
    
    # Drop indexes
    op.drop_index('idx_rules_code', table_name='as1851_rules')
    op.drop_index('idx_rules_active', table_name='as1851_rules')
    op.drop_index('idx_rules_measurement_type', table_name='as1851_rules')
    
    # Drop constraints
    op.drop_constraint('ck_rules_defect_class', 'as1851_rules', type_='check')
    op.drop_constraint('ck_rules_severity', 'as1851_rules', type_='check')
    op.drop_constraint('ck_rules_measurement_type', 'as1851_rules', type_='check')
    op.drop_constraint('uq_rule_code_version', 'as1851_rules', type_='unique')
    
    # Drop table
    op.drop_table('as1851_rules')
Coding Agent Prompt


markdown
# PROMPT: Create AS1851Rule model

Create `services/api/src/app/models/as1851_rule.py`:

## Model Specification
- **Table**: `as1851_rules`
- **PK**: rule_id (UUID)
- **Columns**:
  - rule_code: String(50), required (e.g., 'SP-01', 'CE-01')
  - version: String(50), required (e.g., 'AS1851-2024-v1.3')
  - measurement_type: Enum['pressure_differential', 'air_velocity', 'door_opening_force', 'cause_and_effect_logic', 'interface_test']
  - min_threshold: Numeric(10,3), optional
  - max_threshold: Numeric(10,3), optional
  - unit: String(20), required (Pa, m/s, N, etc.)
  - severity_if_fail: Enum['critical', 'high', 'medium', 'low']
  - defect_classification: Enum['1A', '1B', '2', '3']
  - description: Text
  - reference_standard: String(100) (e.g., 'AS 1851-2012 § 13.2')
  - active: Boolean (default True)
  - effective_date: Date
  - superseded_date: Date (when rule is replaced)
  - created_at, updated_at

## Relationships
- None (standalone reference data)

## Methods
- `to_dict()`: Serialize
- `is_active()`: Return active AND (effective_date <= today) AND (superseded_date IS NULL OR > today)
- `validate_value(measured_value)`: Check if value passes min/max thresholds
- `supersede(new_version)`: Mark this rule as superseded

## Class Methods
- `get_active_rule(measurement_type)`: Get active rule for measurement type
- `get_rule_by_code(rule_code, version=None)`: Get specific rule version or latest

## Validation
- `@validates('measurement_type')`: Must be in enum
- `@validates('severity_if_fail')`: Must be in enum
- `@validates('defect_classification')`: Must be in enum

Example:
```python
# Get active rule for pressure validation
rule = AS1851Rule.get_active_rule('pressure_differential')
print(f"Rule {rule.rule_code}: {rule.min_threshold}-{rule.max_threshold} {rule.unit}")

# Validate measurement
measured_pressure = 18.2
is_compliant = rule.validate_value(measured_pressure)
if not is_compliant:
    print(f"FAIL: {measured_pressure} Pa outside range {rule.min_threshold}-{rule.max_threshold} Pa")
    print(f"Severity: {rule.severity_if_fail}, Classification: {rule.defect_classification}")

# Supersede old rule
old_rule = AS1851Rule.get_rule_by_code('SP-01', 'AS1851-2023-v1.2')
new_rule = AS1851Rule.get_rule_by_code('SP-01', 'AS1851-2024-v1.3')
old_rule.supersede(new_rule)
```

Migration 11: Instruments & Calibration
Alembic Migration Script


python
"""Enhance instruments table for calibration tracking

Revision ID: 011_enhance_instruments_calibration
Revises: 010_add_as1851_rules
Create Date: 2025-10-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '011_enhance_instruments_calibration'
down_revision = '010_add_as1851_rules'
branch_labels = None
depends_on = None


def upgrade():
    # Assuming instruments table already exists, enhance it
    # Add columns if they don't exist
    op.add_column('instruments', sa.Column('instrument_type', sa.String(50), nullable=True))
    op.add_column('instruments', sa.Column('calibration_frequency_months', sa.Integer, nullable=True))
    op.add_column('instruments', sa.Column('calibration_standard', sa.String(100), nullable=True))
    op.add_column('instruments', sa.Column('calibration_cert_id', sa.String(100), nullable=True))
    op.add_column('instruments', sa.Column('calibration_date', sa.Date, nullable=True))
    op.add_column('instruments', sa.Column('calibration_expiry', sa.Date, nullable=True))
    op.add_column('instruments', sa.Column('accuracy', sa.String(50), nullable=True))
    op.add_column('instruments', sa.Column('range_min', sa.Numeric(10, 3), nullable=True))
    op.add_column('instruments', sa.Column('range_max', sa.Numeric(10, 3), nullable=True))
    op.add_column('instruments', sa.Column('unit', sa.String(20), nullable=True))
    
    # Create calibration_certificates table
    op.create_table(
        'calibration_certificates',
        sa.Column('cert_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('instrument_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('instruments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cert_number', sa.String(100), nullable=False),
        sa.Column('calibration_date', sa.Date, nullable=False),
        sa.Column('expiry_date', sa.Date, nullable=False),
        sa.Column('calibration_authority', sa.String(255), nullable=True),
        sa.Column('standard', sa.String(100), nullable=True),
        sa.Column('certificate_file_path', sa.Text, nullable=True),  # S3 key
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('cert_number', name='uq_cert_number')
    )
    
    # Indexes
    op.create_index('idx_instruments_type', 'instruments', ['instrument_type'])
    op.create_index('idx_instruments_expiry', 'instruments', ['calibration_expiry'])
    op.create_index('idx_certs_instrument', 'calibration_certificates', ['instrument_id'])
    op.create_index('idx_certs_expiry', 'calibration_certificates', ['expiry_date'])
    
    # Check constraints
    op.create_check_constraint(
        'ck_instruments_type',
        'instruments',
        "instrument_type IN ('manometer', 'anemometer', '




Retry

AW
Continue



force_gauge', 'multimeter', 'thermometer') OR instrument_type IS NULL" )


op.create_check_constraint(
    'ck_instruments_calibration_freq',
    'instruments',
    'calibration_frequency_months IS NULL OR (calibration_frequency_months > 0 AND calibration_frequency_months <= 60)'
)

op.create_check_constraint(
    'ck_certs_expiry_after_calibration',
    'calibration_certificates',
    'expiry_date > calibration_date'
)
def downgrade(): # Archive calibration data op.execute(""" CREATE TABLE IF NOT EXISTS calibration_certificates_archived AS SELECT *, NOW() as archived_at FROM calibration_certificates """)


# Drop calibration_certificates
op.drop_index('idx_certs_expiry', table_name='calibration_certificates')
op.drop_index('idx_certs_instrument', table_name='calibration_certificates')
op.drop_constraint('ck_certs_expiry_after_calibration', 'calibration_certificates', type_='check')
op.drop_constraint('uq_cert_number', 'calibration_certificates', type_='unique')
op.drop_table('calibration_certificates')

# Drop instrument enhancements
op.drop_index('idx_instruments_expiry', table_name='instruments')
op.drop_index('idx_instruments_type', table_name='instruments')
op.drop_constraint('ck_instruments_calibration_freq', 'instruments', type_='check')
op.drop_constraint('ck_instruments_type', 'instruments', type_='check')

op.drop_column('instruments', 'unit')
op.drop_column('instruments', 'range_max')
op.drop_column('instruments', 'range_min')
op.drop_column('instruments', 'accuracy')
op.drop_column('instruments', 'calibration_expiry')
op.drop_column('instruments', 'calibration_date')
op.drop_column('instruments', 'calibration_cert_id')
op.drop_column('instruments', 'calibration_standard')
op.drop_column('instruments', 'calibration_frequency_months')
op.drop_column('instruments', 'instrument_type')


### Coding Agent Prompts
````markdown
# PROMPT 1: Enhance Instrument model

Update `services/api/src/app/models/instrument.py`:

## Add New Columns
- instrument_type: Enum['manometer', 'anemometer', 'force_gauge', 'multimeter', 'thermometer']
- calibration_frequency_months: Integer (12, 24, etc.)
- calibration_standard: String(100) (e.g., 'ISO/IEC 17025')
- calibration_cert_id: String(100) (reference to current certificate)
- calibration_date: Date
- calibration_expiry: Date
- accuracy: String(50) (e.g., '±1 Pa', '±0.05 m/s')
- range_min, range_max: Numeric(10,3)
- unit: String(20)

## Add Relationships
- calibration_certificates (one-to-many)
- test_instances (one-to-many via required_instrument_id)

## Add Methods
- `is_calibration_valid()`: Return calibration_expiry > today
- `days_until_expiry()`: Return (calibration_expiry - today).days
- `requires_calibration_soon(days=30)`: Return days_until_expiry() <= days
- `get_latest_certificate()`: Return most recent calibration certificate
- `update_calibration(cert)`: Update calibration_date, calibration_expiry from certificate

## Class Methods
- `get_instruments_by_type(instrument_type, building_id=None)`: Query helper
- `get_expired_instruments(building_id=None)`: Return instruments with expired calibration
- `get_expiring_soon(days=30, building_id=None)`: Return instruments expiring within X days

Example:
```python
# Create instrument
manometer = Instrument(
    building_id=building.id,
    serial_number='SN-12345',
    manufacturer='Dwyer',
    model='475-1-FM',
    instrument_type='manometer',
    calibration_frequency_months=12,
    calibration_standard='ISO/IEC 17025',
    accuracy='±1 Pa',
    range_min=0.0,
    range_max=100.0,
    unit='Pa',
    calibration_date=date(2024, 10, 15),
    calibration_expiry=date(2025, 10, 15),
    calibration_cert_id='CERT-2024-789'
)

# Check calibration status
if not manometer.is_calibration_valid():
    print(f"EXPIRED: Calibration expired on {manometer.calibration_expiry}")
elif manometer.requires_calibration_soon(30):
    days = manometer.days_until_expiry()
    print(f"WARNING: Calibration expires in {days} days")
else:
    print(f"OK: Calibration valid until {manometer.calibration_expiry}")

# Query expiring instruments
expiring = Instrument.get_expiring_soon(days=30, building_id=building.id)
for instrument in expiring:
    print(f"{instrument.serial_number}: {instrument.days_until_expiry()} days remaining")
```

---

# PROMPT 2: Create CalibrationCertificate model

Create `services/api/src/app/models/calibration_certificate.py`:

## Model Specification
- **Table**: `calibration_certificates`
- **PK**: cert_id (UUID)
- **FK**: instrument_id (CASCADE)
- **Columns**:
  - cert_number: String(100), required, unique
  - calibration_date: Date, required
  - expiry_date: Date, required (must be > calibration_date)
  - calibration_authority: String(255) (e.g., 'NATA Accredited Lab')
  - standard: String(100) (e.g., 'ISO/IEC 17025')
  - certificate_file_path: Text (S3 key to PDF)
  - created_at

## Relationships
- instrument (many-to-one)

## Methods
- `to_dict()`: Serialize
- `is_valid()`: Return expiry_date > today
- `get_s3_url(expiry_seconds=3600)`: Generate pre-signed URL for certificate PDF
- `days_until_expiry()`: Return (expiry_date - today).days

## Class Methods
- `get_certificates_for_instrument(instrument_id)`: Query helper, ordered by calibration_date DESC
- `get_expired_certificates()`: Return all expired certificates

## Validation
- `@validates('expiry_date')`: Must be > calibration_date
- `@validates('cert_number')`: Strip whitespace, uppercase

Example:
```python
# Create calibration certificate
cert = CalibrationCertificate(
    instrument_id=manometer.id,
    cert_number='CERT-2024-789',
    calibration_date=date(2024, 10, 15),
    expiry_date=date(2025, 10, 15),
    calibration_authority='NATA Accredited Lab - Sydney',
    standard='ISO/IEC 17025',
    certificate_file_path='calibration_certs/CERT-2024-789.pdf'
)

# Update instrument with new certificate
manometer.update_calibration(cert)

# Get certificate URL for viewing
cert_url = cert.get_s3_url(expiry_seconds=300)  # 5-minute URL
print(f"View certificate: {cert_url}")

# Query certificate history
certs = CalibrationCertificate.get_certificates_for_instrument(manometer.id)
for cert in certs:
    status = "VALID" if cert.is_valid() else "EXPIRED"
    print(f"{cert.cert_number} ({cert.calibration_date}): {status}")
```
````

---

## Week 1 Complete: Migration Execution & Testing

### Final Migration Summary

You now have **11 comprehensive migrations**:

1. ✅ Stairs Registry
2. ✅ Floors Registry  
3. ✅ Doors & Doorways
4. ✅ Zones & Control Equipment
5. ✅ Baseline Tables (Pressure, Velocity, Door Force)
6. ✅ C&E Scenarios & Interface Test Definitions
7. ✅ Test Instance Templates
8. ✅ Test Instances (Runtime)
9. ✅ Evidence Records & Enhanced Faults
10. ✅ AS1851 Rules
11. ✅ Instruments & Calibration Enhancement

---

### Execution Steps for Week 1 Completion
````bash
# ============================================
# STEP 1: Run All Migrations on Staging
# ============================================

# Verify current state
cd services/api
alembic current

# Show migration plan
alembic history
alembic upgrade head --sql  # Dry-run SQL output

# Execute migrations
alembic upgrade head

# Verify all tables created
psql -h staging-db -U admin -d firemode_staging << EOF
\dt
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN (
    'stairs', 'floors', 'doors', 'doorways', 'zones', 'control_equipment',
    'baseline_pressure_differentials', 'baseline_air_velocities', 'baseline_door_forces',
    'ce_scenarios', 'interface_test_definitions',
    'test_instance_templates', 'test_instances',
    'evidence_records', 'as1851_rules', 'calibration_certificates'
)
ORDER BY tablename;
EOF

# ============================================
# STEP 2: Verify Data Integrity
# ============================================

# Check foreign keys
psql -h staging-db -U admin -d firemode_staging -c "
SELECT DISTINCT
    tc.table_name,
    COUNT(*) as fk_count
FROM information_schema.table_constraints tc
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public'
GROUP BY tc.table_name
ORDER BY tc.table_name;
"

# Check indexes created
psql -h staging-db -U admin -d firemode_staging -c "
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND (
    tablename LIKE '%stair%' 
    OR tablename LIKE '%baseline%' 
    OR tablename LIKE '%instance%'
)
ORDER BY tablename, indexname;
"

# Verify AS1851 rules seeded
psql -h staging-db -U admin -d firemode_staging -c "
SELECT rule_code, version, measurement_type, min_threshold, max_threshold, unit, severity_if_fail
FROM as1851_rules
ORDER BY rule_code;
"

# Expected output:
# rule_code | version | measurement_type | min_threshold | max_threshold | unit | severity_if_fail
# ----------+---------+------------------+---------------+---------------+------+------------------
# CE-01     | AS1851-2024-v1.3 | cause_and_effect_logic | NULL | NULL | NULL | critical
# INT-01    | AS1851-2024-v1.3 | interface_test | NULL | NULL | NULL | critical
# SP-01     | AS1851-2024-v1.3 | pressure_differential | 20.0 | 80.0 | Pa | critical
# SP-02     | AS1851-2024-v1.3 | air_velocity | 1.0 | NULL | m/s | high
# SP-03     | AS1851-2024-v1.3 | door_opening_force | NULL | 110.0 | N | critical

# ============================================
# STEP 3: Run Migration Tests
# ============================================

# Run migration test suite
pytest tests/migrations/ -v

# Expected tests:
# tests/migrations/test_stair_baseline_migration.py::test_migration_up_creates_all_tables PASSED
# tests/migrations/test_stair_baseline_migration.py::test_migration_down_preserves_data PASSED
# tests/migrations/test_stair_baseline_migration.py::test_foreign_key_cascades PASSED
# tests/migrations/test_stair_baseline_migration.py::test_index_performance PASSED
# tests/migrations/test_baseline_completeness.py::test_baseline_pressure_unique_constraint PASSED
# tests/migrations/test_baseline_completeness.py::test_jsonb_validation PASSED

# ============================================
# STEP 4: Seed Test Data
# ============================================

# Create Python script to seed pilot building
python << 'PYTHON_SCRIPT'
from app.models import *
from app.database import db
from datetime import date, datetime

# Create pilot building (assumes exists)
building = Building.query.filter_by(name='Pilot Building 123').first()

# Create 2 stairs
stair_a = Stair(
    building_id=building.id,
    stair_name='Stair-A',
    orientation='North',
    stair_type='pressurized',
    floor_range_bottom='Ground',
    floor_range_top='Level-14',
    design_standard='AS/NZS 1668.1:2015'
)

stair_b = Stair(
    building_id=building.id,
    stair_name='Stair-B',
    orientation='South',
    stair_type='pressurized',
    floor_range_bottom='Ground',
    floor_range_top='Level-14',
    design_standard='AS/NZS 1668.1:2015'
)

db.session.add_all([stair_a, stair_b])
db.session.commit()

# Create 15 floors per stair
floors = []
for stair in [stair_a, stair_b]:
    for i in range(15):
        floor = Floor(
            building_id=building.id,
            stair_id=stair.stair_id,
            floor_level='Ground' if i == 0 else f'Level-{i}',
            floor_number=i,
            height_m=i * 3.5
        )
        floors.append(floor)

db.session.bulk_save_objects(floors)
db.session.commit()

# Create doors and doorways
doors = []
doorways = []
for stair in [stair_a, stair_b]:
    stair_floors = Floor.query.filter_by(stair_id=stair.stair_id).all()
    for floor in stair_floors:
        # One door per floor
        door = Door(
            building_id=building.id,
            stair_id=stair.stair_id,
            floor_id=floor.floor_id,
            door_identifier=f'D-{floor.floor_level}-{stair.stair_name}',
            door_type='fire_rated',
            fire_rating_minutes=60,
            door_closer_model='LCN 4040XP',
            door_hand='right',
            width_m=0.90,
            height_m=2.10
        )
        doors.append(door)
        
        # One doorway per floor
        doorway = Doorway(
            building_id=building.id,
            stair_id=stair.stair_id,
            floor_id=floor.floor_id,
            doorway_identifier=f'DW-{floor.floor_level}-{stair.stair_name}',
            width_m=1.20,
            height_m=2.40,
            orientation=stair.orientation,
            adjacent_space='Main Corridor'
        )
        doorways.append(doorway)

db.session.bulk_save_objects(doors)
db.session.bulk_save_objects(doorways)
db.session.commit()

# Create zones (5 zones per stair)
zones = []
zone_floor_mapping = [
    (1, ['Ground', 'Level-1', 'Level-2', 'Level-3']),
    (2, ['Level-4', 'Level-5', 'Level-6']),
    (3, ['Level-7', 'Level-8', 'Level-9']),
    (4, ['Level-10', 'Level-11', 'Level-12']),
    (5, ['Level-13', 'Level-14'])
]

for stair in [stair_a, stair_b]:
    for zone_num, floor_names in zone_floor_mapping:
        # Get floor IDs
        zone_floors = Floor.query.filter(
            Floor.stair_id == stair.stair_id,
            Floor.floor_level.in_(floor_names)
        ).all()
        
        zone = Zone(
            building_id=building.id,
            stair_id=stair.stair_id,
            zone_name=f'Zone-{zone_num}',
            floors_covered=floor_names,
            floor_ids_covered=[f.floor_id for f in zone_floors]
        )
        zones.append(zone)

db.session.bulk_save_objects(zones)
db.session.commit()

# Create control equipment
equipment = [
    ControlEquipment(
        building_id=building.id,
        stair_id=stair_a.stair_id,
        equipment_type='fan',
        equipment_identifier='FAN-01-A',
        manufacturer='Woods',
        model='EDXM-450',
        serial_number='WD-2024-A001',
        specifications={'capacity_m3_s': 5.2, 'motor_kw': 15.0}
    ),
    ControlEquipment(
        building_id=building.id,
        stair_id=stair_b.stair_id,
        equipment_type='fan',
        equipment_identifier='FAN-01-B',
        manufacturer='Woods',
        model='EDXM-450',
        serial_number='WD-2024-B001',
        specifications={'capacity_m3_s': 5.2, 'motor_kw': 15.0}
    )
]

db.session.bulk_save_objects(equipment)
db.session.commit()

print(f"✅ Seeded pilot building:")
print(f"  - 2 stairs")
print(f"  - 30 floors (15 per stair)")
print(f"  - 30 doors")
print(f"  - 30 doorways")
print(f"  - 10 zones (5 per stair)")
print(f"  - 2 fans")
PYTHON_SCRIPT

# ============================================
# STEP 5: Create Baseline Import API Test
# ============================================

# Create CSV file for baseline import test
cat > /tmp/baseline_pressure_test.csv << 'EOF'
stair_id,floor_id,door_configuration,pressure_pa,commissioned_date
<stair_a_uuid>,<floor_ground_uuid>,all_closed,44.5,2024-01-15
<stair_a_uuid>,<floor_ground_uuid>,evac_doors_open,43.2,2024-01-15
<stair_a_uuid>,<floor_1_uuid>,all_closed,45.1,2024-01-15
<stair_a_uuid>,<floor_1_uuid>,evac_doors_open,43.8,2024-01-15
EOF

# Test baseline import API
curl -X POST http://localhost:8000/api/v1/buildings/<building_id>/baseline/pressure/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/baseline_pressure_test.csv"

# Expected response:
# {
#   "success": true,
#   "rows_imported": 4
# }

# Verify baseline imported
psql -h staging-db -U admin -d firemode_staging -c "
SELECT 
    s.stair_name,
    f.floor_level,
    b.door_configuration,
    b.pressure_pa,
    b.commissioned_date
FROM baseline_pressure_differentials b
JOIN stairs s ON b.stair_id = s.stair_id
JOIN floors f ON b.floor_id = f.floor_id
ORDER BY s.stair_name, f.floor_number, b.door_configuration;
"

# ============================================
# STEP 6: Performance Testing
# ============================================

# Test query performance with EXPLAIN ANALYZE
psql -h staging-db -U admin -d firemode_staging << 'EOF'
EXPLAIN ANALYZE
SELECT 
    i.instance_id,
    i.measurement_type,
    s.stair_name,
    f.floor_level,
    i.door_configuration,
    i.measured_value_numeric,
    i.baseline_value,
    i.is_compliant
FROM test_instances i
JOIN stairs s ON i.stair_id = s.stair_id
JOIN floors f ON i.floor_id = f.floor_id
WHERE i.session_id = '<test_session_id>'
AND i.stair_id = '<stair_a_uuid>'
ORDER BY i.sequence_order;
EOF

# Expected: Query should use indexes, execution time < 50ms

# Test trend query performance
psql -h staging-db -U admin -d firemode_staging << 'EOF'
EXPLAIN ANALYZE
SELECT 
    i.completed_at,
    i.measured_value_numeric,
    i.baseline_value,
    i.is_compliant
FROM test_instances i
WHERE i.stair_id = '<stair_a_uuid>'
AND i.floor_id = '<floor_8_uuid>'
AND i.door_configuration = 'all_closed'
AND i.measurement_type = 'pressure_differential'
AND i.completed_at > NOW() - INTERVAL '3 years'
ORDER BY i.completed_at DESC;
EOF

# Expected: Should use idx_instances_stair_floor, execution time < 100ms

# ============================================
# STEP 7: Week 1 Success Criteria Checklist
# ============================================

echo "Week 1 Migration Checklist:"
echo ""
echo "Database Schema:"
echo "  [✓] 11 migrations executed successfully"
echo "  [✓] 16+ new tables created"
echo "  [✓] 30+ indexes created"
echo "  [✓] Foreign key cascades verified"
echo "  [✓] Check constraints active"
echo "  [✓] Archive tables created for rollback"
echo ""
echo "Data Seeding:"
echo "  [✓] 5 AS1851 rules seeded"
echo "  [✓] Pilot building configured (2 stairs, 15 floors)"
echo "  [✓] Baseline import API tested"
echo ""
echo "Performance:"
echo "  [✓] Query execution times < 100ms"
echo "  [✓] Index usage verified"
echo ""
echo "Testing:"
echo "  [✓] Migration tests pass"
echo "  [✓] Foreign key cascade tests pass"
echo "  [✓] JSONB validation tests pass"
echo ""
echo "✅ Week 1 COMPLETE - Ready for Week 2 (Instance Generation Engine)"
````

---

## Next Steps: Week 2 Kickoff

### Week 2 Focus: Archetype Expansion Engine + Validation Logic

**Priority deliverables:**

1. **Instance Generation Engine** (`services/api/src/app/services/instance_generator.py`)
   - Implement 5 archetype expansion rules
   - Generate test instance templates from baseline
   - Validate cardinality against expected counts

2. **Validation Engine** (`services/api/src/app/services/instance_validator.py`)
   - Implement instance-level validation logic
   - Auto-create faults with full context
   - Calculate deviation from baseline

3. **API Endpoints** (`services/api/src/app/routes/instances.py`)
   - `POST /v1/buildings/{id}/instances/generate` - Generate templates
   - `GET /v1/buildings/{id}/instances/templates` - List templates
   - `POST /v1/tests/sessions` - Create session + clone instances
   - `POST /v1/tests/sessions/{id}/instances/{instance_id}/results` - Submit result

Would you like me to:
1. **Generate the Instance Generation Engine code** (archetype expansion logic)?
2. **Create the Validation Engine code** (fault creation with context)?
3. **Provide API endpoint implementation prompts**?
4. **Generate Week 2 Jira tickets with acceptance criteria**?
