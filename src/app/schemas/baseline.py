"""
Pydantic schemas for Baseline API endpoints
"""

from datetime import date, datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, validator


class FloorPressureSetpoint(BaseModel):
    """Individual floor pressure setpoint configuration"""
    floor_id: str = Field(..., min_length=1, max_length=50, description="Floor identifier")
    pressure_pa: float = Field(..., ge=20, le=80, description="Pressure setpoint in Pascals (AS 1851-2012: 20-80 Pa)")


class FanSpecification(BaseModel):
    """Fan equipment specification"""
    fan_id: str = Field(..., description="Unique fan identifier")
    model: Optional[str] = Field(None, description="Fan model number")
    capacity_cfm: Optional[float] = Field(None, ge=0, description="Fan capacity in cubic feet per minute")
    static_pressure_pa: Optional[float] = Field(None, ge=0, description="Static pressure in Pascals")
    motor_hp: Optional[float] = Field(None, ge=0, description="Motor horsepower")


class DamperSpecification(BaseModel):
    """Damper equipment specification"""
    damper_id: str = Field(..., description="Unique damper identifier")
    type: Optional[str] = Field(None, description="Damper type (e.g., 'fire', 'smoke', 'relief')")
    size_mm: Optional[str] = Field(None, description="Damper size in millimeters")
    actuator_type: Optional[str] = Field(None, description="Actuator type")


class ManualOverrideLocation(BaseModel):
    """Manual override control location"""
    location_id: str = Field(..., description="Unique location identifier")
    description: str = Field(..., description="Location description")
    floor: Optional[str] = Field(None, description="Floor where override is located")
    coordinates: Optional[Dict[str, float]] = Field(None, description="GPS or building coordinates")


class InterfacingSystem(BaseModel):
    """System that interfaces with stair pressurization"""
    system_id: str = Field(..., description="Unique system identifier")
    system_type: str = Field(..., description="Type of interfacing system")
    interface_type: str = Field(..., description="Type of interface (e.g., 'fire_alarm', 'hvac')")
    description: Optional[str] = Field(None, description="Interface description")


class BuildingConfigurationData(BaseModel):
    """Building configuration data for submission"""
    floor_pressure_setpoints: Optional[Dict[str, float]] = Field(
        None, 
        description="Floor-by-floor pressure setpoints: {\"floor_1\": 45, \"floor_2\": 50, ...}"
    )
    door_force_limit_newtons: Optional[int] = Field(
        None, 
        ge=50, 
        le=110, 
        description="Maximum door opening force in Newtons (AS 1851-2012: 50-110 N)"
    )
    air_velocity_target_ms: Optional[float] = Field(
        None, 
        ge=1.0, 
        description="Target air velocity through doorways in m/s (AS 1851-2012: ≥1.0 m/s)"
    )
    fan_specifications: Optional[List[FanSpecification]] = Field(
        None, 
        description="Fan equipment specifications"
    )
    damper_specifications: Optional[List[DamperSpecification]] = Field(
        None, 
        description="Damper equipment specifications"
    )
    relief_air_strategy: Optional[str] = Field(
        None, 
        max_length=50, 
        description="Strategy for relief air management"
    )
    ce_logic_diagram_path: Optional[str] = Field(
        None, 
        description="Path to cause-and-effect logic diagram"
    )
    manual_override_locations: Optional[List[ManualOverrideLocation]] = Field(
        None, 
        description="Locations of manual override controls"
    )
    interfacing_systems: Optional[List[InterfacingSystem]] = Field(
        None, 
        description="Other systems that interface with stair pressurization"
    )

    @validator('floor_pressure_setpoints')
    def validate_pressure_setpoints(cls, v):
        if v is not None:
            for floor_id, pressure in v.items():
                if not (20 <= pressure <= 80):
                    raise ValueError(f"Pressure for {floor_id} must be between 20-80 Pa (AS 1851-2012)")
        return v


class BaselinePressureMeasurement(BaseModel):
    """Baseline pressure differential measurement"""
    floor_id: str = Field(..., min_length=1, max_length=50, description="Floor identifier")
    door_configuration: str = Field(..., min_length=1, max_length=50, description="Door configuration")
    pressure_pa: float = Field(..., ge=20, le=80, description="Measured pressure in Pascals (AS 1851-2012: 20-80 Pa)")
    measured_date: date = Field(..., description="Date when measurement was taken")


class BaselineVelocityMeasurement(BaseModel):
    """Baseline air velocity measurement"""
    doorway_id: str = Field(..., min_length=1, max_length=100, description="Doorway identifier")
    velocity_ms: float = Field(..., ge=1.0, description="Measured velocity in m/s (AS 1851-2012: ≥1.0 m/s)")
    measured_date: date = Field(..., description="Date when measurement was taken")


class BaselineDoorForceMeasurement(BaseModel):
    """Baseline door force measurement"""
    door_id: str = Field(..., min_length=1, max_length=100, description="Door identifier")
    force_newtons: float = Field(..., le=110, description="Measured force in Newtons (AS 1851-2012: ≤110 N)")
    measured_date: date = Field(..., description="Date when measurement was taken")


class BuildingBaselineSubmit(BaseModel):
    """Request schema for submitting building baseline data"""
    building_configuration: Optional[BuildingConfigurationData] = Field(
        None, 
        description="Building configuration and design parameters"
    )
    pressure_measurements: Optional[List[BaselinePressureMeasurement]] = Field(
        None, 
        description="Baseline pressure differential measurements"
    )
    velocity_measurements: Optional[List[BaselineVelocityMeasurement]] = Field(
        None, 
        description="Baseline air velocity measurements"
    )
    door_force_measurements: Optional[List[BaselineDoorForceMeasurement]] = Field(
        None, 
        description="Baseline door force measurements"
    )


class MissingBaselineItem(BaseModel):
    """Individual missing baseline item"""
    type: str = Field(..., description="Type of missing item (pressure, velocity, door_force)")
    identifier: str = Field(..., description="Floor/doorway/door identifier")
    configuration: Optional[str] = Field(None, description="Door configuration (for pressure measurements)")
    description: str = Field(..., description="Human-readable description of missing item")


class BaselineCompleteness(BaseModel):
    """Baseline completeness validation result"""
    is_complete: bool = Field(..., description="Whether baseline is complete")
    completeness_percentage: float = Field(..., ge=0, le=100, description="Completeness percentage")
    missing_items: List[MissingBaselineItem] = Field(..., description="List of missing baseline items")
    total_expected: int = Field(..., description="Total number of expected measurements")
    total_present: int = Field(..., description="Total number of present measurements")
    
    # Breakdown by type
    pressure_complete: bool = Field(..., description="Whether pressure measurements are complete")
    velocity_complete: bool = Field(..., description="Whether velocity measurements are complete")
    door_force_complete: bool = Field(..., description="Whether door force measurements are complete")
    configuration_complete: bool = Field(..., description="Whether building configuration is complete")


class BaselineSubmissionResponse(BaseModel):
    """Response schema for baseline data submission"""
    success: bool = Field(..., description="Whether submission was successful")
    message: str = Field(..., description="Success or error message")
    completeness: BaselineCompleteness = Field(..., description="Updated baseline completeness")
    items_created: int = Field(..., description="Number of baseline items created")
    items_updated: int = Field(..., description="Number of baseline items updated")


class BaselineMeasurement(BaseModel):
    """Generic baseline measurement for compliance validation"""
    measurement_type: str = Field(..., description="Type of measurement (pressure, velocity, door_force)")
    value: float = Field(..., description="Measured value")
    unit: str = Field(..., description="Unit of measurement")
    floor_id: Optional[str] = Field(None, description="Floor identifier")
    door_configuration: Optional[str] = Field(None, description="Door configuration")
    doorway_id: Optional[str] = Field(None, description="Doorway identifier")
    door_id: Optional[str] = Field(None, description="Door identifier")
    measured_date: date = Field(..., description="Date when measurement was taken")
    baseline_value: Optional[float] = Field(None, description="Baseline value for comparison")
    deviation_percentage: Optional[float] = Field(None, description="Deviation from baseline as percentage")


class ComplianceResult(BaseModel):
    """Result of compliance validation against AS 1851-2012"""
    is_compliant: bool = Field(..., description="Whether measurement is compliant")
    classification: str = Field(..., description="AS 1851 classification (1A, 1B, 2, 3)")
    severity: str = Field(..., description="Fault severity (critical, high, medium, low)")
    rule_applied: str = Field(..., description="AS 1851 rule code applied")
    deviation_from_baseline: float = Field(..., description="Deviation from baseline value")
    threshold_exceeded: bool = Field(..., description="Whether threshold was exceeded")
    recommendation: Optional[str] = Field(None, description="Recommended action")
    measurement: BaselineMeasurement = Field(..., description="Original measurement data")
