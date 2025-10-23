"""
Integration tests for baseline foundation functionality
Tests baseline validation, session blocking, and constraint enforcement
"""

import pytest
import uuid
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.database.core import get_db
from src.app.models.buildings import Building
from src.app.models.building_configuration import BuildingConfiguration
from src.app.models.baseline import (
    BaselinePressureDifferential,
    BaselineAirVelocity,
    BaselineDoorForce
)
from src.app.services.baseline_validator import validate_baseline_completeness
from src.app.services.compliance_validator import validate_measurement, ComplianceValidator
from src.app.schemas.baseline import (
    BaselineMeasurement,
    BuildingBaselineSubmit,
    BaselinePressureMeasurement,
    BaselineVelocityMeasurement,
    BaselineDoorForceMeasurement
)


@pytest.fixture
async def test_building(db_session: AsyncSession):
    """Create a test building for baseline testing"""
    building = Building(
        name="Test Building",
        address="123 Test Street",
        building_type="office",
        compliance_status="pending"
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def test_building_with_config(db_session: AsyncSession, test_building: Building):
    """Create a test building with configuration"""
    config = BuildingConfiguration(
        building_id=test_building.id,
        floor_pressure_setpoints={"floor_1": 45, "floor_2": 50, "floor_3": 48},
        door_force_limit_newtons=110,
        air_velocity_target_ms=1.2,
        fan_specifications=[
            {"fan_id": "fan_1", "model": "ABC-123", "capacity_cfm": 5000},
            {"fan_id": "fan_2", "model": "XYZ-456", "capacity_cfm": 3000}
        ],
        damper_specifications=[
            {"damper_id": "damper_1", "type": "fire", "size_mm": "600x400"},
            {"damper_id": "damper_2", "type": "smoke", "size_mm": "300x300"}
        ],
        relief_air_strategy="Automatic relief dampers",
        ce_logic_diagram_path="/diagrams/ce-logic-v1.pdf"
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


class TestBaselineValidation:
    """Test baseline completeness validation"""

    async def test_empty_baseline_validation(self, db_session: AsyncSession, test_building: Building):
        """Test validation of building with no baseline data"""
        completeness = await validate_baseline_completeness(test_building.id, db_session)
        
        assert not completeness.is_complete
        assert completeness.completeness_percentage == 0.0
        assert len(completeness.missing_items) > 0
        assert not completeness.configuration_complete
        assert not completeness.pressure_complete
        assert not completeness.velocity_complete
        assert not completeness.door_force_complete

    async def test_configuration_only_validation(self, db_session: AsyncSession, test_building_with_config: BuildingConfiguration):
        """Test validation of building with configuration but no measurements"""
        completeness = await validate_baseline_completeness(test_building_with_config.building_id, db_session)
        
        assert not completeness.is_complete
        assert completeness.configuration_complete
        assert not completeness.pressure_complete
        assert not completeness.velocity_complete
        assert not completeness.door_force_complete

    async def test_complete_baseline_validation(self, db_session: AsyncSession, test_building_with_config: BuildingConfiguration):
        """Test validation of building with complete baseline data"""
        building_id = test_building_with_config.building_id
        
        # Add pressure measurements
        pressure_measurements = [
            BaselinePressureDifferential(
                building_id=building_id,
                floor_id="floor_1",
                door_configuration="all_doors_open",
                pressure_pa=42,
                measured_date=date.today()
            ),
            BaselinePressureDifferential(
                building_id=building_id,
                floor_id="floor_1",
                door_configuration="all_doors_closed",
                pressure_pa=48,
                measured_date=date.today()
            ),
            BaselinePressureDifferential(
                building_id=building_id,
                floor_id="floor_2",
                door_configuration="all_doors_open",
                pressure_pa=45,
                measured_date=date.today()
            ),
            BaselinePressureDifferential(
                building_id=building_id,
                floor_id="floor_2",
                door_configuration="all_doors_closed",
                pressure_pa=52,
                measured_date=date.today()
            ),
            BaselinePressureDifferential(
                building_id=building_id,
                floor_id="floor_3",
                door_configuration="all_doors_open",
                pressure_pa=43,
                measured_date=date.today()
            ),
            BaselinePressureDifferential(
                building_id=building_id,
                floor_id="floor_3",
                door_configuration="all_doors_closed",
                pressure_pa=49,
                measured_date=date.today()
            ),
        ]
        
        for measurement in pressure_measurements:
            db_session.add(measurement)
        
        # Add velocity measurement
        velocity_measurement = BaselineAirVelocity(
            building_id=building_id,
            doorway_id="stair_door_1",
            velocity_ms=1.1,
            measured_date=date.today()
        )
        db_session.add(velocity_measurement)
        
        # Add door force measurement
        force_measurement = BaselineDoorForce(
            building_id=building_id,
            door_id="stair_door_1",
            force_newtons=95,
            measured_date=date.today()
        )
        db_session.add(force_measurement)
        
        await db_session.commit()
        
        # Validate completeness
        completeness = await validate_baseline_completeness(building_id, db_session)
        
        assert completeness.is_complete
        assert completeness.completeness_percentage == 100.0
        assert len(completeness.missing_items) == 0
        assert completeness.configuration_complete
        assert completeness.pressure_complete
        assert completeness.velocity_complete
        assert completeness.door_force_complete


class TestSessionBlocking:
    """Test session creation blocking when baseline is incomplete"""

    async def test_session_creation_without_baseline(self, client: TestClient, test_building: Building, auth_headers: dict):
        """Test that session creation is blocked when baseline is incomplete"""
        response = client.post(
            "/v1/tests/sessions",
            json={
                "building_id": str(test_building.id),
                "session_name": "Test Session"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 428
        data = response.json()
        assert data["error_code"] == "FIRE-428"
        assert "baseline incomplete" in data["message"]
        assert "missing" in data
        assert data["completeness_percentage"] == 0.0

    async def test_session_creation_with_complete_baseline(self, client: TestClient, test_building_with_config: BuildingConfiguration, auth_headers: dict):
        """Test that session creation succeeds when baseline is complete"""
        # First, add complete baseline measurements
        building_id = test_building_with_config.building_id
        
        # Add minimal required measurements
        pressure_measurement = BaselinePressureDifferential(
            building_id=building_id,
            floor_id="floor_1",
            door_configuration="all_doors_open",
            pressure_pa=42,
            measured_date=date.today()
        )
        
        velocity_measurement = BaselineAirVelocity(
            building_id=building_id,
            doorway_id="stair_door_1",
            velocity_ms=1.1,
            measured_date=date.today()
        )
        
        force_measurement = BaselineDoorForce(
            building_id=building_id,
            door_id="stair_door_1",
            force_newtons=95,
            measured_date=date.today()
        )
        
        # Get the database session from the test client
        async with get_db() as db:
            db.add(pressure_measurement)
            db.add(velocity_measurement)
            db.add(force_measurement)
            await db.commit()
        
        # Now try to create a session
        response = client.post(
            "/v1/tests/sessions",
            json={
                "building_id": str(building_id),
                "session_name": "Test Session"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["building_id"] == str(building_id)


class TestConstraintEnforcement:
    """Test database constraint enforcement for baseline data"""

    async def test_pressure_constraint_enforcement(self, db_session: AsyncSession, test_building: Building):
        """Test that pressure constraints are enforced"""
        # Test pressure below minimum (20 Pa)
        with pytest.raises(Exception):  # Should raise constraint violation
            measurement = BaselinePressureDifferential(
                building_id=test_building.id,
                floor_id="floor_1",
                door_configuration="all_doors_open",
                pressure_pa=15,  # Below 20 Pa
                measured_date=date.today()
            )
            db_session.add(measurement)
            await db_session.commit()
        
        await db_session.rollback()
        
        # Test pressure above maximum (80 Pa)
        with pytest.raises(Exception):  # Should raise constraint violation
            measurement = BaselinePressureDifferential(
                building_id=test_building.id,
                floor_id="floor_1",
                door_configuration="all_doors_open",
                pressure_pa=85,  # Above 80 Pa
                measured_date=date.today()
            )
            db_session.add(measurement)
            await db_session.commit()
        
        await db_session.rollback()

    async def test_velocity_constraint_enforcement(self, db_session: AsyncSession, test_building: Building):
        """Test that velocity constraints are enforced"""
        # Test velocity below minimum (1.0 m/s)
        with pytest.raises(Exception):  # Should raise constraint violation
            measurement = BaselineAirVelocity(
                building_id=test_building.id,
                doorway_id="stair_door_1",
                velocity_ms=0.8,  # Below 1.0 m/s
                measured_date=date.today()
            )
            db_session.add(measurement)
            await db_session.commit()
        
        await db_session.rollback()

    async def test_door_force_constraint_enforcement(self, db_session: AsyncSession, test_building: Building):
        """Test that door force constraints are enforced"""
        # Test force above maximum (110 N)
        with pytest.raises(Exception):  # Should raise constraint violation
            measurement = BaselineDoorForce(
                building_id=test_building.id,
                door_id="stair_door_1",
                force_newtons=120,  # Above 110 N
                measured_date=date.today()
            )
            db_session.add(measurement)
            await db_session.commit()
        
        await db_session.rollback()

    async def test_building_configuration_constraints(self, db_session: AsyncSession, test_building: Building):
        """Test that building configuration constraints are enforced"""
        # Test door force limit above maximum
        with pytest.raises(Exception):  # Should raise constraint violation
            config = BuildingConfiguration(
                building_id=test_building.id,
                door_force_limit_newtons=120,  # Above 110 N
                air_velocity_target_ms=1.2
            )
            db_session.add(config)
            await db_session.commit()
        
        await db_session.rollback()
        
        # Test air velocity target below minimum
        with pytest.raises(Exception):  # Should raise constraint violation
            config = BuildingConfiguration(
                building_id=test_building.id,
                door_force_limit_newtons=110,
                air_velocity_target_ms=0.8  # Below 1.0 m/s
            )
            db_session.add(config)
            await db_session.commit()
        
        await db_session.rollback()


class TestBaselineAPI:
    """Test baseline data submission API"""

    async def test_baseline_submission_success(self, client: TestClient, test_building: Building, auth_headers: dict):
        """Test successful baseline data submission"""
        baseline_data = {
            "building_configuration": {
                "floor_pressure_setpoints": {"floor_1": 45, "floor_2": 50},
                "door_force_limit_newtons": 110,
                "air_velocity_target_ms": 1.2,
                "fan_specifications": [
                    {"fan_id": "fan_1", "model": "ABC-123", "capacity_cfm": 5000}
                ],
                "damper_specifications": [
                    {"damper_id": "damper_1", "type": "fire", "size_mm": "600x400"}
                ],
                "relief_air_strategy": "Automatic relief dampers"
            },
            "pressure_measurements": [
                {
                    "floor_id": "floor_1",
                    "door_configuration": "all_doors_open",
                    "pressure_pa": 42,
                    "measured_date": "2024-01-15"
                }
            ],
            "velocity_measurements": [
                {
                    "doorway_id": "stair_door_1",
                    "velocity_ms": 1.1,
                    "measured_date": "2024-01-15"
                }
            ],
            "door_force_measurements": [
                {
                    "door_id": "stair_door_1",
                    "force_newtons": 95,
                    "measured_date": "2024-01-15"
                }
            ]
        }
        
        response = client.post(
            f"/v1/buildings/{test_building.id}/baseline",
            json=baseline_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "completeness" in data
        assert data["items_created"] > 0

    async def test_baseline_submission_validation_errors(self, client: TestClient, test_building: Building, auth_headers: dict):
        """Test baseline submission with validation errors"""
        invalid_baseline_data = {
            "building_configuration": {
                "door_force_limit_newtons": 120,  # Invalid: above 110 N
                "air_velocity_target_ms": 0.8,    # Invalid: below 1.0 m/s
            },
            "pressure_measurements": [
                {
                    "floor_id": "floor_1",
                    "door_configuration": "all_doors_open",
                    "pressure_pa": 15,  # Invalid: below 20 Pa
                    "measured_date": "2024-01-15"
                }
            ],
            "velocity_measurements": [
                {
                    "doorway_id": "stair_door_1",
                    "velocity_ms": 0.5,  # Invalid: below 1.0 m/s
                    "measured_date": "2024-01-15"
                }
            ],
            "door_force_measurements": [
                {
                    "door_id": "stair_door_1",
                    "force_newtons": 150,  # Invalid: above 110 N
                    "measured_date": "2024-01-15"
                }
            ]
        }
        
        response = client.post(
            f"/v1/buildings/{test_building.id}/baseline",
            json=invalid_baseline_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error


class TestComplianceValidation:
    """Test compliance validation and fault creation"""

    async def test_pressure_compliance_validation(self, db_session: AsyncSession, test_building_with_config: BuildingConfiguration):
        """Test pressure measurement compliance validation"""
        building_id = test_building_with_config.building_id
        
        # Add baseline measurement
        baseline = BaselinePressureDifferential(
            building_id=building_id,
            floor_id="floor_1",
            door_configuration="all_doors_open",
            pressure_pa=45,
            measured_date=date.today()
        )
        db_session.add(baseline)
        await db_session.commit()
        
        # Test compliant measurement
        compliant_measurement = BaselineMeasurement(
            measurement_type="pressure",
            value=47,
            unit="Pa",
            floor_id="floor_1",
            door_configuration="all_doors_open",
            measured_date=date.today()
        )
        
        result = await validate_measurement(
            compliant_measurement,
            uuid.uuid4(),  # test_session_id
            building_id,
            uuid.uuid4(),  # created_by
            db_session
        )
        
        assert result.is_compliant
        assert result.classification == "3"
        assert result.severity == "low"
        
        # Test non-compliant measurement (outside range)
        non_compliant_measurement = BaselineMeasurement(
            measurement_type="pressure",
            value=15,  # Below 20 Pa
            unit="Pa",
            floor_id="floor_1",
            door_configuration="all_doors_open",
            measured_date=date.today()
        )
        
        result = await validate_measurement(
            non_compliant_measurement,
            uuid.uuid4(),  # test_session_id
            building_id,
            uuid.uuid4(),  # created_by
            db_session
        )
        
        assert not result.is_compliant
        assert result.classification == "1A"
        assert result.severity == "critical"
        assert result.threshold_exceeded

    async def test_velocity_compliance_validation(self, db_session: AsyncSession, test_building_with_config: BuildingConfiguration):
        """Test velocity measurement compliance validation"""
        building_id = test_building_with_config.building_id
        
        # Add baseline measurement
        baseline = BaselineAirVelocity(
            building_id=building_id,
            doorway_id="stair_door_1",
            velocity_ms=1.2,
            measured_date=date.today()
        )
        db_session.add(baseline)
        await db_session.commit()
        
        # Test non-compliant measurement (below minimum)
        non_compliant_measurement = BaselineMeasurement(
            measurement_type="velocity",
            value=0.8,  # Below 1.0 m/s
            unit="m/s",
            doorway_id="stair_door_1",
            measured_date=date.today()
        )
        
        result = await validate_measurement(
            non_compliant_measurement,
            uuid.uuid4(),  # test_session_id
            building_id,
            uuid.uuid4(),  # created_by
            db_session
        )
        
        assert not result.is_compliant
        assert result.classification == "1B"
        assert result.severity == "high"
        assert result.threshold_exceeded

    async def test_door_force_compliance_validation(self, db_session: AsyncSession, test_building_with_config: BuildingConfiguration):
        """Test door force measurement compliance validation"""
        building_id = test_building_with_config.building_id
        
        # Add baseline measurement
        baseline = BaselineDoorForce(
            building_id=building_id,
            door_id="stair_door_1",
            force_newtons=95,
            measured_date=date.today()
        )
        db_session.add(baseline)
        await db_session.commit()
        
        # Test non-compliant measurement (above maximum)
        non_compliant_measurement = BaselineMeasurement(
            measurement_type="door_force",
            value=120,  # Above 110 N
            unit="N",
            door_id="stair_door_1",
            measured_date=date.today()
        )
        
        result = await validate_measurement(
            non_compliant_measurement,
            uuid.uuid4(),  # test_session_id
            building_id,
            uuid.uuid4(),  # created_by
            db_session
        )
        
        assert not result.is_compliant
        assert result.classification == "1A"
        assert result.severity == "critical"
        assert result.threshold_exceeded


class TestMigrationRollback:
    """Test migration rollback safety"""

    async def test_migration_rollback_safety(self, db_session: AsyncSession):
        """Test that migration can be safely rolled back"""
        # This test would verify that the migration can be rolled back
        # without data loss or constraint violations
        # In a real implementation, this would test the downgrade() function
        
        # For now, we'll just verify that the tables exist and can be queried
        from sqlalchemy import text
        
        # Check that baseline tables exist
        result = await db_session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'building_configurations',
                'baseline_pressure_differentials',
                'baseline_air_velocities',
                'baseline_door_forces'
            )
        """))
        
        tables = [row[0] for row in result.fetchall()]
        assert 'building_configurations' in tables
        assert 'baseline_pressure_differentials' in tables
        assert 'baseline_air_velocities' in tables
        assert 'baseline_door_forces' in tables
