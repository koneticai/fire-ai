"""
Baseline validation service for FireMode Compliance Platform
Implements business logic for checking baseline completeness and calculating missing items
"""

from typing import List, Dict, Set, Tuple
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.buildings import Building
from ..models.building_configuration import BuildingConfiguration
from ..models.baseline import (
    BaselinePressureDifferential, 
    BaselineAirVelocity, 
    BaselineDoorForce
)
from ..schemas.baseline import (
    BaselineCompleteness, 
    MissingBaselineItem
)


class BaselineValidator:
    """
    Service for validating baseline data completeness for stair pressurization compliance.
    
    Checks that buildings have all required baseline measurements before allowing
    test session creation, following AS 1851-2012 requirements.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_baseline_completeness(
        self, 
        building_id: UUID
    ) -> BaselineCompleteness:
        """
        Validate that a building has complete baseline data for stair pressurization testing.
        
        Returns detailed completeness information including missing items.
        """
        # Get building configuration
        config_result = await self.db.execute(
            select(BuildingConfiguration).where(
                BuildingConfiguration.building_id == building_id
            )
        )
        building_config = config_result.scalar_one_or_none()
        
        # Get all baseline measurements
        pressure_result = await self.db.execute(
            select(BaselinePressureDifferential).where(
                BaselinePressureDifferential.building_id == building_id
            )
        )
        pressure_measurements = pressure_result.scalars().all()
        
        velocity_result = await self.db.execute(
            select(BaselineAirVelocity).where(
                BaselineAirVelocity.building_id == building_id
            )
        )
        velocity_measurements = velocity_result.scalars().all()
        
        force_result = await self.db.execute(
            select(BaselineDoorForce).where(
                BaselineDoorForce.building_id == building_id
            )
        )
        force_measurements = force_result.scalars().all()
        
        # Analyze completeness
        missing_items = []
        
        # Check configuration completeness
        config_complete = self._validate_configuration_completeness(building_config, missing_items)
        
        # Check pressure measurements completeness
        pressure_complete = self._validate_pressure_completeness(
            building_config, pressure_measurements, missing_items
        )
        
        # Check velocity measurements completeness
        velocity_complete = self._validate_velocity_completeness(
            velocity_measurements, missing_items
        )
        
        # Check door force measurements completeness
        door_force_complete = self._validate_door_force_completeness(
            force_measurements, missing_items
        )
        
        # Calculate overall completeness
        total_expected = self._calculate_expected_measurements(building_config)
        total_present = len(pressure_measurements) + len(velocity_measurements) + len(force_measurements)
        
        if total_expected > 0:
            completeness_percentage = (total_present / total_expected) * 100
        else:
            completeness_percentage = 0.0
        
        is_complete = (
            config_complete and 
            pressure_complete and 
            velocity_complete and 
            door_force_complete
        )
        
        return BaselineCompleteness(
            is_complete=is_complete,
            completeness_percentage=completeness_percentage,
            missing_items=missing_items,
            total_expected=total_expected,
            total_present=total_present,
            pressure_complete=pressure_complete,
            velocity_complete=velocity_complete,
            door_force_complete=door_force_complete,
            configuration_complete=config_complete
        )
    
    def _validate_configuration_completeness(
        self, 
        building_config: BuildingConfiguration, 
        missing_items: List[MissingBaselineItem]
    ) -> bool:
        """Validate that building configuration is complete"""
        if not building_config:
            missing_items.append(MissingBaselineItem(
                type="configuration",
                identifier="building_configuration",
                description="Building configuration not found"
            ))
            return False
        
        # Check required configuration fields
        required_fields = [
            ('floor_pressure_setpoints', 'Floor pressure setpoints'),
            ('door_force_limit_newtons', 'Door force limit'),
            ('air_velocity_target_ms', 'Air velocity target'),
        ]
        
        config_complete = True
        for field_name, description in required_fields:
            if not hasattr(building_config, field_name) or getattr(building_config, field_name) is None:
                missing_items.append(MissingBaselineItem(
                    type="configuration",
                    identifier=field_name,
                    description=f"Missing {description}"
                ))
                config_complete = False
        
        return config_complete
    
    def _validate_pressure_completeness(
        self, 
        building_config: BuildingConfiguration, 
        pressure_measurements: List[BaselinePressureDifferential],
        missing_items: List[MissingBaselineItem]
    ) -> bool:
        """Validate that pressure measurements are complete for all floors and door configurations"""
        if not building_config or not building_config.floor_pressure_setpoints:
            return True  # Can't validate without configuration
        
        # Expected measurements: each floor × each door configuration
        expected_measurements = set()
        door_configurations = ['all_doors_open', 'all_doors_closed']  # Standard configurations
        
        for floor_id in building_config.floor_pressure_setpoints.keys():
            for door_config in door_configurations:
                expected_measurements.add((floor_id, door_config))
        
        # Present measurements
        present_measurements = set()
        for measurement in pressure_measurements:
            present_measurements.add((measurement.floor_id, measurement.door_configuration))
        
        # Find missing measurements
        missing_measurements = expected_measurements - present_measurements
        for floor_id, door_config in missing_measurements:
            missing_items.append(MissingBaselineItem(
                type="pressure",
                identifier=floor_id,
                configuration=door_config,
                description=f"Missing pressure measurement for {floor_id} with {door_config}"
            ))
        
        return len(missing_measurements) == 0
    
    def _validate_velocity_completeness(
        self, 
        velocity_measurements: List[BaselineAirVelocity],
        missing_items: List[MissingBaselineItem]
    ) -> bool:
        """Validate that velocity measurements are complete for all doorways"""
        # For MVP, we expect at least one velocity measurement per building
        # In a full implementation, this would check against a predefined list of doorways
        if not velocity_measurements:
            missing_items.append(MissingBaselineItem(
                type="velocity",
                identifier="all_doorways",
                description="No air velocity measurements found"
            ))
            return False
        
        return True
    
    def _validate_door_force_completeness(
        self, 
        force_measurements: List[BaselineDoorForce],
        missing_items: List[MissingBaselineItem]
    ) -> bool:
        """Validate that door force measurements are complete for all doors"""
        # For MVP, we expect at least one door force measurement per building
        # In a full implementation, this would check against a predefined list of doors
        if not force_measurements:
            missing_items.append(MissingBaselineItem(
                type="door_force",
                identifier="all_doors",
                description="No door force measurements found"
            ))
            return False
        
        return True
    
    def _calculate_expected_measurements(
        self, 
        building_config: BuildingConfiguration
    ) -> int:
        """Calculate total number of expected baseline measurements"""
        if not building_config or not building_config.floor_pressure_setpoints:
            return 0
        
        # Expected pressure measurements: floors × door configurations
        num_floors = len(building_config.floor_pressure_setpoints)
        num_door_configs = 2  # all_doors_open, all_doors_closed
        expected_pressure = num_floors * num_door_configs
        
        # Expected velocity measurements: at least 1 per building
        expected_velocity = 1
        
        # Expected door force measurements: at least 1 per building
        expected_door_force = 1
        
        return expected_pressure + expected_velocity + expected_door_force


async def validate_baseline_completeness(
    building_id: UUID, 
    db: AsyncSession
) -> BaselineCompleteness:
    """
    Convenience function for validating baseline completeness.
    
    Args:
        building_id: UUID of the building to validate
        db: Async database session
        
    Returns:
        BaselineCompleteness object with detailed validation results
    """
    validator = BaselineValidator(db)
    return await validator.validate_baseline_completeness(building_id)
