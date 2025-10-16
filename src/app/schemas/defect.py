"""
Pydantic schemas for Defects
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator


class DefectSeverity(str, Enum):
    """Defect severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectStatus(str, Enum):
    """Defect status workflow"""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    REPAIR_SCHEDULED = "repair_scheduled"
    REPAIRED = "repaired"
    VERIFIED = "verified"
    CLOSED = "closed"


class DefectBase(BaseModel):
    """Base defect schema with common fields"""
    severity: DefectSeverity = Field(
        ..., 
        description="Defect severity level",
        examples=["critical", "high", "medium", "low"]
    )
    category: Optional[str] = Field(
        None,
        max_length=50,
        description="Defect category",
        examples=["extinguisher_pressure", "hose_reel_leak", "alarm_system"]
    )
    description: str = Field(
        ..., 
        min_length=1,
        description="Detailed description of the defect",
        examples=["Fire extinguisher pressure gauge shows 150 PSI, below minimum threshold of 180 PSI"]
    )
    as1851_rule_code: Optional[str] = Field(
        None,
        max_length=20,
        description="AS1851 rule code that was violated",
        examples=["FE-01", "HR-03", "AS-15"]
    )
    asset_id: Optional[UUID] = Field(
        None,
        description="Optional - specific equipment that has the defect"
    )


class DefectCreate(DefectBase):
    """Schema for creating a new defect"""
    test_session_id: UUID = Field(
        ...,
        description="Test session (inspection) where defect was discovered"
    )
    
    @validator('test_session_id')
    def validate_test_session_id(cls, v):
        if not v:
            raise ValueError("test_session_id is required")
        return v


class DefectUpdate(BaseModel):
    """Schema for updating a defect (workflow transitions)"""
    status: Optional[DefectStatus] = Field(
        None,
        description="New defect status"
    )
    acknowledged_at: Optional[datetime] = Field(
        None,
        description="When the defect was acknowledged"
    )
    acknowledged_by: Optional[UUID] = Field(
        None,
        description="User who acknowledged the defect"
    )
    repaired_at: Optional[datetime] = Field(
        None,
        description="When the defect was repaired"
    )
    verified_at: Optional[datetime] = Field(
        None,
        description="When the repair was verified"
    )
    closed_at: Optional[datetime] = Field(
        None,
        description="When the defect was closed"
    )
    repair_evidence_ids: Optional[List[UUID]] = Field(
        None,
        description="Evidence IDs showing repair completion"
    )


class DefectRead(DefectBase):
    """Schema for reading a defect"""
    id: UUID = Field(
        ...,
        description="Unique identifier for the defect"
    )
    test_session_id: UUID = Field(
        ...,
        description="Test session where defect was discovered"
    )
    building_id: UUID = Field(
        ...,
        description="Building where defect was found"
    )
    status: DefectStatus = Field(
        ...,
        description="Current defect status"
    )
    discovered_at: datetime = Field(
        ...,
        description="When the defect was discovered"
    )
    acknowledged_at: Optional[datetime] = Field(
        None,
        description="When the defect was acknowledged"
    )
    acknowledged_by: Optional[UUID] = Field(
        None,
        description="User who acknowledged the defect"
    )
    repaired_at: Optional[datetime] = Field(
        None,
        description="When the defect was repaired"
    )
    verified_at: Optional[datetime] = Field(
        None,
        description="When the repair was verified"
    )
    closed_at: Optional[datetime] = Field(
        None,
        description="When the defect was closed"
    )
    evidence_ids: List[UUID] = Field(
        default_factory=list,
        description="Evidence IDs showing the defect"
    )
    repair_evidence_ids: List[UUID] = Field(
        default_factory=list,
        description="Evidence IDs showing repair completion"
    )
    created_at: datetime = Field(
        ...,
        description="When the defect record was created"
    )
    updated_at: datetime = Field(
        ...,
        description="When the defect record was last updated"
    )
    created_by: Optional[UUID] = Field(
        None,
        description="User who created this defect record"
    )

    class Config:
        from_attributes = True


class DefectWithEvidence(DefectRead):
    """Schema for defect with expanded evidence metadata"""
    evidence_metadata: Optional[List[dict]] = Field(
        None,
        description="Expanded evidence metadata"
    )
    repair_evidence_metadata: Optional[List[dict]] = Field(
        None,
        description="Expanded repair evidence metadata"
    )


class DefectListResponse(BaseModel):
    """Schema for paginated defect list response"""
    defects: List[DefectRead] = Field(
        ...,
        description="List of defects"
    )
    total: int = Field(
        ...,
        description="Total number of defects"
    )
    next_cursor: Optional[str] = Field(
        None,
        description="Cursor for next page"
    )
    has_more: bool = Field(
        ...,
        description="Whether there are more defects"
    )


class DefectStats(BaseModel):
    """Schema for defect statistics"""
    total_defects: int = Field(
        ...,
        description="Total number of defects"
    )
    open_defects: int = Field(
        ...,
        description="Number of open defects"
    )
    critical_defects: int = Field(
        ...,
        description="Number of critical defects"
    )
    high_defects: int = Field(
        ...,
        description="Number of high severity defects"
    )
    medium_defects: int = Field(
        ...,
        description="Number of medium severity defects"
    )
    low_defects: int = Field(
        ...,
        description="Number of low severity defects"
    )
    average_mttr_days: Optional[float] = Field(
        None,
        description="Average Mean Time To Repair in days"
    )


class EvidenceLinkRequest(BaseModel):
    """Schema for linking evidence to defect"""
    evidence_id: UUID = Field(
        ...,
        description="Evidence ID to link to the defect"
    )
    is_repair_evidence: bool = Field(
        False,
        description="Whether this is repair evidence (vs defect evidence)"
    )
