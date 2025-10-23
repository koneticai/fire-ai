"""
SQLAlchemy models for Baseline Measurements
"""

import uuid
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class BaselinePressureDifferential(Base):
    """
    SQLAlchemy model for Baseline Pressure Differentials table
    
    Stores commissioning pressure differential measurements for each floor
    and door configuration. Used to establish baseline values for AS 1851-2012
    compliance testing.
    """
    __tablename__ = 'baseline_pressure_differentials'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Foreign key to buildings
    building_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('buildings.id', ondelete='CASCADE'), 
        nullable=False,
        doc="Building this baseline measurement applies to"
    )
    
    # Measurement context
    floor_id = Column(
        String(50), 
        nullable=False,
        doc="Floor identifier (e.g., 'floor_1', 'ground', 'level_2')"
    )
    door_configuration = Column(
        String(50), 
        nullable=False,
        doc="Door configuration (e.g., 'all_doors_open', 'all_doors_closed')"
    )
    pressure_pa = Column(
        Float, 
        nullable=False,
        doc="Measured pressure differential in Pascals (AS 1851-2012: 20-80 Pa)"
    )
    measured_date = Column(
        Date, 
        nullable=False,
        doc="Date when baseline measurement was taken"
    )
    
    # User tracking
    created_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True,
        doc="User who recorded this baseline measurement"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the baseline measurement was recorded"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the baseline measurement was last updated"
    )
    
    # Relationships
    building = relationship("Building", back_populates="baseline_pressure_differentials")
    
    def __repr__(self):
        return f"<BaselinePressureDifferential(id={self.id}, building_id={self.building_id}, floor={self.floor_id}, pressure={self.pressure_pa}Pa)>"


class BaselineAirVelocity(Base):
    """
    SQLAlchemy model for Baseline Air Velocities table
    
    Stores commissioning air velocity measurements for doorways. Used to
    establish baseline values for AS 1851-2012 compliance testing.
    """
    __tablename__ = 'baseline_air_velocities'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Foreign key to buildings
    building_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('buildings.id', ondelete='CASCADE'), 
        nullable=False,
        doc="Building this baseline measurement applies to"
    )
    
    # Measurement context
    doorway_id = Column(
        String(100), 
        nullable=False,
        doc="Doorway identifier (e.g., 'stair_door_1', 'main_entrance')"
    )
    velocity_ms = Column(
        Float, 
        nullable=False,
        doc="Measured air velocity in meters per second (AS 1851-2012: ≥1.0 m/s)"
    )
    measured_date = Column(
        Date, 
        nullable=False,
        doc="Date when baseline measurement was taken"
    )
    
    # User tracking
    created_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True,
        doc="User who recorded this baseline measurement"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the baseline measurement was recorded"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the baseline measurement was last updated"
    )
    
    # Relationships
    building = relationship("Building", back_populates="baseline_air_velocities")
    
    def __repr__(self):
        return f"<BaselineAirVelocity(id={self.id}, building_id={self.building_id}, doorway={self.doorway_id}, velocity={self.velocity_ms}m/s)>"


class BaselineDoorForce(Base):
    """
    SQLAlchemy model for Baseline Door Forces table
    
    Stores commissioning door opening force measurements. Used to establish
    baseline values for AS 1851-2012 compliance testing.
    """
    __tablename__ = 'baseline_door_forces'
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )
    
    # Foreign key to buildings
    building_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('buildings.id', ondelete='CASCADE'), 
        nullable=False,
        doc="Building this baseline measurement applies to"
    )
    
    # Measurement context
    door_id = Column(
        String(100), 
        nullable=False,
        doc="Door identifier (e.g., 'stair_door_1', 'fire_door_2')"
    )
    force_newtons = Column(
        Float, 
        nullable=False,
        doc="Measured door opening force in Newtons (AS 1851-2012: ≤110 N)"
    )
    measured_date = Column(
        Date, 
        nullable=False,
        doc="Date when baseline measurement was taken"
    )
    
    # User tracking
    created_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True,
        doc="User who recorded this baseline measurement"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the baseline measurement was recorded"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the baseline measurement was last updated"
    )
    
    # Relationships
    building = relationship("Building", back_populates="baseline_door_forces")
    
    def __repr__(self):
        return f"<BaselineDoorForce(id={self.id}, building_id={self.building_id}, door={self.door_id}, force={self.force_newtons}N)>"
