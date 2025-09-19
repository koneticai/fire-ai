"""
Pydantic schemas for Building API endpoints
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class BuildingBase(BaseModel):
    """Base building schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Building name/identifier")
    address: str = Field(..., min_length=1, description="Full address of the building")
    building_type: str = Field(..., min_length=1, max_length=100, description="Type/category of building")
    compliance_status: Optional[str] = Field(default="pending", max_length=50, description="Current compliance status")


class BuildingCreate(BaseModel):
    """Schema for creating a new building"""
    site_name: str = Field(..., description="Building site name")
    site_address: str = Field(..., description="Building site address") 
    building_type: str = Field(..., min_length=1, max_length=100, description="Type/category of building")
    compliance_status: Optional[str] = Field(default="pending", max_length=50, description="Current compliance status")
    owner_id: Optional[UUID] = Field(None, description="Optional owner/manager of the building")


class BuildingUpdate(BaseModel):
    """Schema for updating an existing building"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1)
    building_type: Optional[str] = Field(None, min_length=1, max_length=100)
    compliance_status: Optional[str] = Field(None, max_length=50)
    owner_id: Optional[UUID] = None


class BuildingRead(BuildingBase):
    """Schema for reading building data"""
    id: UUID = Field(..., description="Unique building identifier")
    building_id: UUID = Field(..., description="Unique building identifier (alias)", alias="id")
    owner_id: Optional[UUID] = Field(None, description="Owner/manager of the building")
    created_at: datetime = Field(..., description="When the building was created")
    updated_at: Optional[datetime] = Field(None, description="When the building was last updated")
    status: str = Field(default="active", description="Building status")

    class Config:
        from_attributes = True
        allow_population_by_field_name = True


class BuildingListResponse(BaseModel):
    """Schema for building list API response"""
    buildings: list[BuildingRead] = Field(..., description="List of buildings")
    total: int = Field(..., description="Total number of buildings")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    has_more: bool = Field(..., description="Whether there are more results")