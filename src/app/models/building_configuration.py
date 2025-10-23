"""
SQLAlchemy model for Building Configuration
"""

import uuid
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database.core import Base


class BuildingConfiguration(Base):
    """
    SQLAlchemy model for Building Configuration table
    
    Stores stair pressurization design parameters and equipment specifications
    for buildings. Extends the basic building information with AS 1851-2012
    compliance requirements.
    """
    __tablename__ = 'building_configurations'
    
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
        doc="Building this configuration applies to"
    )
    
    # Stair pressurization design parameters
    floor_pressure_setpoints = Column(
        JSONB, 
        nullable=True,
        doc="Floor-by-floor pressure setpoints: {\"floor_1\": 45, \"floor_2\": 50, ...}"
    )
    door_force_limit_newtons = Column(
        Integer, 
        nullable=True, 
        default=110,
        doc="Maximum door opening force in Newtons (AS 1851-2012: 50-110 N)"
    )
    air_velocity_target_ms = Column(
        Float, 
        nullable=True, 
        default=1.0,
        doc="Target air velocity through doorways in m/s (AS 1851-2012: ≥1.0 m/s)"
    )
    fan_specifications = Column(
        JSONB, 
        nullable=True,
        doc="Fan equipment specifications and settings"
    )
    damper_specifications = Column(
        JSONB, 
        nullable=True,
        doc="Damper equipment specifications and settings"
    )
    relief_air_strategy = Column(
        String(50), 
        nullable=True,
        doc="Strategy for relief air management"
    )
    ce_logic_diagram_path = Column(
        Text, 
        nullable=True,
        doc="Path to cause-and-effect logic diagram"
    )
    manual_override_locations = Column(
        JSONB, 
        nullable=True,
        doc="Locations of manual override controls"
    )
    interfacing_systems = Column(
        JSONB, 
        nullable=True,
        doc="Other systems that interface with stair pressurization"
    )
    
    # User tracking
    created_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True,
        doc="User who created this configuration"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        doc="When the configuration was created"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        doc="When the configuration was last updated"
    )
    
    # Relationships
    building = relationship("Building", back_populates="building_configuration")
    
    def __repr__(self):
        return f"<BuildingConfiguration(id={self.id}, building_id={self.building_id})>"
