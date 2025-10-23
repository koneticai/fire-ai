"""
Compliance validation service for FireMode Compliance Platform
Implements AS 1851-2012 rule enforcement and automatic fault creation
"""

from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.defects import Defect
from ..models.baseline import (
    BaselinePressureDifferential, 
    BaselineAirVelocity, 
    BaselineDoorForce
)
from ..schemas.baseline import (
    BaselineMeasurement, 
    ComplianceResult
)


class ComplianceValidator:
    """
    Service for validating measurements against AS 1851-2012 requirements
    and automatically creating defects when thresholds are exceeded.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_measurement(
        self,
        measurement: BaselineMeasurement,
        test_session_id: UUID,
        building_id: UUID,
        created_by: UUID
    ) -> ComplianceResult:
        """
        Validate a measurement against AS 1851-2012 rules and create defects if needed.
        
        Args:
            measurement: The measurement to validate
            test_session_id: Test session where this measurement was taken
            building_id: Building being tested
            created_by: User who took the measurement
            
        Returns:
            ComplianceResult with validation outcome and any created defects
        """
        # Get baseline for comparison
        baseline = await self._get_baseline_measurement(measurement, building_id)
        
        # Apply AS 1851-2012 rules based on measurement type
        if measurement.measurement_type == "pressure":
            return await self._validate_pressure_measurement(
                measurement, baseline, test_session_id, building_id, created_by
            )
        elif measurement.measurement_type == "velocity":
            return await self._validate_velocity_measurement(
                measurement, baseline, test_session_id, building_id, created_by
            )
        elif measurement.measurement_type == "door_force":
            return await self._validate_door_force_measurement(
                measurement, baseline, test_session_id, building_id, created_by
            )
        else:
            # Unknown measurement type - mark as non-compliant
            return ComplianceResult(
                is_compliant=False,
                classification="3",
                severity="medium",
                rule_applied="AS1851-2012-UNKNOWN",
                deviation_from_baseline=0.0,
                threshold_exceeded=True,
                recommendation="Unknown measurement type - manual review required",
                measurement=measurement
            )
    
    async def _get_baseline_measurement(
        self, 
        measurement: BaselineMeasurement, 
        building_id: UUID
    ) -> Optional[BaselineMeasurement]:
        """Get the corresponding baseline measurement for comparison"""
        if measurement.measurement_type == "pressure":
            result = await self.db.execute(
                select(BaselinePressureDifferential).where(
                    and_(
                        BaselinePressureDifferential.building_id == building_id,
                        BaselinePressureDifferential.floor_id == measurement.floor_id,
                        BaselinePressureDifferential.door_configuration == measurement.door_configuration
                    )
                )
            )
            baseline = result.scalar_one_or_none()
            if baseline:
                return BaselineMeasurement(
                    measurement_type="pressure",
                    value=baseline.pressure_pa,
                    unit="Pa",
                    floor_id=baseline.floor_id,
                    door_configuration=baseline.door_configuration,
                    measured_date=baseline.measured_date
                )
        
        elif measurement.measurement_type == "velocity":
            result = await self.db.execute(
                select(BaselineAirVelocity).where(
                    and_(
                        BaselineAirVelocity.building_id == building_id,
                        BaselineAirVelocity.doorway_id == measurement.doorway_id
                    )
                )
            )
            baseline = result.scalar_one_or_none()
            if baseline:
                return BaselineMeasurement(
                    measurement_type="velocity",
                    value=baseline.velocity_ms,
                    unit="m/s",
                    doorway_id=baseline.doorway_id,
                    measured_date=baseline.measured_date
                )
        
        elif measurement.measurement_type == "door_force":
            result = await self.db.execute(
                select(BaselineDoorForce).where(
                    and_(
                        BaselineDoorForce.building_id == building_id,
                        BaselineDoorForce.door_id == measurement.door_id
                    )
                )
            )
            baseline = result.scalar_one_or_none()
            if baseline:
                return BaselineMeasurement(
                    measurement_type="door_force",
                    value=baseline.force_newtons,
                    unit="N",
                    door_id=baseline.door_id,
                    measured_date=baseline.measured_date
                )
        
        return None
    
    async def _validate_pressure_measurement(
        self,
        measurement: BaselineMeasurement,
        baseline: Optional[BaselineMeasurement],
        test_session_id: UUID,
        building_id: UUID,
        created_by: UUID
    ) -> ComplianceResult:
        """Validate pressure measurement against AS 1851-2012 rules"""
        # AS 1851-2012: Pressure must be 20-80 Pa
        pressure = measurement.value
        
        if pressure < 20 or pressure > 80:
            # Critical fault - outside acceptable range
            classification = "1A"
            severity = "critical"
            threshold_exceeded = True
            is_compliant = False
            
            # Create defect
            await self._create_defect(
                test_session_id=test_session_id,
                building_id=building_id,
                severity=severity,
                category="pressure_out_of_range",
                description=f"Pressure measurement {pressure} Pa is outside AS 1851-2012 range (20-80 Pa)",
                as1851_rule_code="AS1851-2012-SP-01",
                created_by=created_by
            )
            
            recommendation = "Immediate action required - pressure outside acceptable range"
        else:
            # Check deviation from baseline
            deviation = 0.0
            if baseline:
                deviation = abs(pressure - baseline.value) / baseline.value * 100
                
                if deviation > 20:  # More than 20% deviation
                    classification = "2"
                    severity = "medium"
                    threshold_exceeded = True
                    is_compliant = False
                    recommendation = f"Significant deviation from baseline ({deviation:.1f}%) - investigate cause"
                else:
                    classification = "3"
                    severity = "low"
                    threshold_exceeded = False
                    is_compliant = True
                    recommendation = "Within acceptable range"
            else:
                classification = "3"
                severity = "low"
                threshold_exceeded = False
                is_compliant = True
                recommendation = "Within acceptable range (no baseline for comparison)"
        
        return ComplianceResult(
            is_compliant=is_compliant,
            classification=classification,
            severity=severity,
            rule_applied="AS1851-2012-SP-01",
            deviation_from_baseline=deviation,
            threshold_exceeded=threshold_exceeded,
            recommendation=recommendation,
            measurement=measurement
        )
    
    async def _validate_velocity_measurement(
        self,
        measurement: BaselineMeasurement,
        baseline: Optional[BaselineMeasurement],
        test_session_id: UUID,
        building_id: UUID,
        created_by: UUID
    ) -> ComplianceResult:
        """Validate velocity measurement against AS 1851-2012 rules"""
        # AS 1851-2012: Velocity must be ≥1.0 m/s
        velocity = measurement.value
        
        if velocity < 1.0:
            # High fault - below minimum velocity
            classification = "1B"
            severity = "high"
            threshold_exceeded = True
            is_compliant = False
            
            # Create defect
            await self._create_defect(
                test_session_id=test_session_id,
                building_id=building_id,
                severity=severity,
                category="velocity_below_minimum",
                description=f"Air velocity {velocity} m/s is below AS 1851-2012 minimum (1.0 m/s)",
                as1851_rule_code="AS1851-2012-SP-02",
                created_by=created_by
            )
            
            recommendation = "Air velocity below minimum - check fan operation and damper settings"
        else:
            # Check deviation from baseline
            deviation = 0.0
            if baseline:
                deviation = abs(velocity - baseline.value) / baseline.value * 100
                
                if deviation > 25:  # More than 25% deviation
                    classification = "2"
                    severity = "medium"
                    threshold_exceeded = True
                    is_compliant = False
                    recommendation = f"Significant deviation from baseline ({deviation:.1f}%) - investigate cause"
                else:
                    classification = "3"
                    severity = "low"
                    threshold_exceeded = False
                    is_compliant = True
                    recommendation = "Within acceptable range"
            else:
                classification = "3"
                severity = "low"
                threshold_exceeded = False
                is_compliant = True
                recommendation = "Within acceptable range (no baseline for comparison)"
        
        return ComplianceResult(
            is_compliant=is_compliant,
            classification=classification,
            severity=severity,
            rule_applied="AS1851-2012-SP-02",
            deviation_from_baseline=deviation,
            threshold_exceeded=threshold_exceeded,
            recommendation=recommendation,
            measurement=measurement
        )
    
    async def _validate_door_force_measurement(
        self,
        measurement: BaselineMeasurement,
        baseline: Optional[BaselineMeasurement],
        test_session_id: UUID,
        building_id: UUID,
        created_by: UUID
    ) -> ComplianceResult:
        """Validate door force measurement against AS 1851-2012 rules"""
        # AS 1851-2012: Door force must be ≤110 N
        force = measurement.value
        
        if force > 110:
            # Critical fault - above maximum force
            classification = "1A"
            severity = "critical"
            threshold_exceeded = True
            is_compliant = False
            
            # Create defect
            await self._create_defect(
                test_session_id=test_session_id,
                building_id=building_id,
                severity=severity,
                category="door_force_excessive",
                description=f"Door opening force {force} N exceeds AS 1851-2012 maximum (110 N)",
                as1851_rule_code="AS1851-2012-SP-03",
                created_by=created_by
            )
            
            recommendation = "Immediate action required - door force exceeds maximum allowable"
        else:
            # Check deviation from baseline
            deviation = 0.0
            if baseline:
                deviation = abs(force - baseline.value) / baseline.value * 100
                
                if deviation > 15:  # More than 15% deviation
                    classification = "2"
                    severity = "medium"
                    threshold_exceeded = True
                    is_compliant = False
                    recommendation = f"Significant deviation from baseline ({deviation:.1f}%) - investigate cause"
                else:
                    classification = "3"
                    severity = "low"
                    threshold_exceeded = False
                    is_compliant = True
                    recommendation = "Within acceptable range"
            else:
                classification = "3"
                severity = "low"
                threshold_exceeded = False
                is_compliant = True
                recommendation = "Within acceptable range (no baseline for comparison)"
        
        return ComplianceResult(
            is_compliant=is_compliant,
            classification=classification,
            severity=severity,
            rule_applied="AS1851-2012-SP-03",
            deviation_from_baseline=deviation,
            threshold_exceeded=threshold_exceeded,
            recommendation=recommendation,
            measurement=measurement
        )
    
    async def _create_defect(
        self,
        test_session_id: UUID,
        building_id: UUID,
        severity: str,
        category: str,
        description: str,
        as1851_rule_code: str,
        created_by: UUID
    ) -> Defect:
        """Create a defect record for non-compliant measurements"""
        defect = Defect(
            test_session_id=test_session_id,
            building_id=building_id,
            severity=severity,
            category=category,
            description=description,
            as1851_rule_code=as1851_rule_code,
            status="open",
            created_by=created_by
        )
        
        self.db.add(defect)
        await self.db.commit()
        await self.db.refresh(defect)
        
        return defect


async def validate_measurement(
    measurement: BaselineMeasurement,
    test_session_id: UUID,
    building_id: UUID,
    created_by: UUID,
    db: AsyncSession
) -> ComplianceResult:
    """
    Convenience function for validating measurements against AS 1851-2012 rules.
    
    Args:
        measurement: The measurement to validate
        test_session_id: Test session where this measurement was taken
        building_id: Building being tested
        created_by: User who took the measurement
        db: Async database session
        
    Returns:
        ComplianceResult with validation outcome and any created defects
    """
    validator = ComplianceValidator(db)
    return await validator.validate_measurement(
        measurement, test_session_id, building_id, created_by
    )
