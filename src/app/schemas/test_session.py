"""
Pydantic schemas for Test Session API endpoints
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class TestSessionBase(BaseModel):
    """Base test session schema with common fields"""
    session_name: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Descriptive name for the testing session"
    )
    status: Optional[str] = Field(
        default="active", 
        max_length=50,
        description="Current status of the testing session"
    )
    session_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Flexible data storage for session-specific information"
    )


class TestSessionCreate(TestSessionBase):
    """Schema for creating a new test session"""
    building_id: UUID = Field(..., description="Building being tested in this session")


class TestSessionUpdate(BaseModel):
    """Schema for updating an existing test session"""
    session_name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, max_length=50)
    session_data: Optional[Dict[str, Any]] = None


class TestSessionRead(TestSessionBase):
    """Schema for reading test session data"""
    id: UUID = Field(..., description="Unique test session identifier")
    building_id: UUID = Field(..., description="Building being tested")
    vector_clock: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="CRDT vector clock for distributed updates"
    )
    created_by: Optional[UUID] = Field(None, description="User who created this session")
    created_at: datetime = Field(..., description="When the session was created")
    updated_at: Optional[datetime] = Field(None, description="When the session was last updated")

    class Config:
        from_attributes = True


class TestSessionListResponse(BaseModel):
    """Schema for test session list API response"""
    sessions: list[TestSessionRead] = Field(..., description="List of test sessions")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    has_more: bool = Field(..., description="Whether there are more results")


class OfflineBundleResponse(BaseModel):
    """Schema for offline bundle response"""
    session_id: UUID = Field(..., description="Test session ID")
    bundle_data: Dict[str, Any] = Field(..., description="Offline bundle data")
    vector_clock: Dict[str, Any] = Field(..., description="Current vector clock state")
    expires_at: datetime = Field(..., description="When the bundle expires")