"""
Pydantic schemas for C&E (Containment & Efficiency) Test API endpoints
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class CETestStatus(str, Enum):
    """Allowed C&E test session statuses."""

    ACTIVE = "active"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CETestType(str, Enum):
    """Allowed C&E test types."""

    CONTAINMENT = "containment_efficiency"
    INTERFACE = "interface_sequence"
    ALARM = "alarm_cause_effect"


class CETestSeverity(str, Enum):
    """Deviation severity labels."""

    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class CETestSessionBase(BaseModel):
    """Base C&E test session schema with common fields"""
    session_name: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Descriptive name for the C&E testing session"
    )
    test_type: CETestType = Field(
        default=CETestType.CONTAINMENT,
        description="Type of C&E test being performed"
    )
    compliance_standard: str = Field(
        default="AS1851-2012",
        max_length=100,
        description="Compliance standard being tested against"
    )
    status: CETestStatus = Field(
        default=CETestStatus.ACTIVE,
        description="Current status of the test session"
    )
    test_configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration parameters for the test"
    )


class CETestSessionCreate(CETestSessionBase):
    """Schema for creating a new C&E test session"""
    building_id: UUID = Field(..., description="Building being tested in this session")


class CETestSessionUpdate(BaseModel):
    """Schema for updating an existing C&E test session"""
    session_name: Optional[str] = Field(None, min_length=1, max_length=255)
    test_type: Optional[CETestType] = Field(None)
    compliance_standard: Optional[str] = Field(None, max_length=100)
    status: Optional[CETestStatus] = Field(None)
    test_configuration: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None
    deviation_analysis: Optional[Dict[str, Any]] = None
    compliance_score: Optional[float] = Field(None, ge=0, le=100)


class CETestSessionRead(CETestSessionBase):
    """Schema for reading C&E test session data"""
    id: UUID = Field(..., description="Unique test session identifier")
    building_id: UUID = Field(..., description="Building being tested")
    test_results: Optional[Dict[str, Any]] = Field(None, description="Test results and measurements")
    deviation_analysis: Optional[Dict[str, Any]] = Field(None, description="Deviation analysis")
    compliance_score: Optional[float] = Field(None, ge=0, le=100, description="Overall compliance score (0-100)")
    created_by: UUID = Field(..., description="User who created this session")
    created_at: datetime = Field(..., description="When the session was created")
    updated_at: Optional[datetime] = Field(None, description="When the session was last updated")

    class Config:
        from_attributes = True


class CETestMeasurementBase(BaseModel):
    """Base C&E test measurement schema"""
    measurement_type: str = Field(
        ..., 
        max_length=100,
        description="Type of measurement (pressure, velocity, temperature, etc.)"
    )
    location_id: str = Field(
        ..., 
        max_length=255,
        description="Zone, room, or specific location where measurement was taken"
    )
    measurement_value: float = Field(..., description="The measured value")
    unit: str = Field(
        ..., 
        max_length=20,
        description="Unit of measurement (Pa, m/s, °C, etc.)"
    )
    measurement_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata about the measurement"
    )


class CETestMeasurementCreate(CETestMeasurementBase):
    """Schema for creating a new C&E test measurement"""
    test_session_id: UUID = Field(..., description="C&E test session this measurement belongs to")
    timestamp: Optional[datetime] = Field(None, description="When the measurement was taken")


class CETestMeasurementRead(CETestMeasurementBase):
    """Schema for reading C&E test measurement data"""
    id: UUID = Field(..., description="Unique measurement identifier")
    test_session_id: UUID = Field(..., description="C&E test session this measurement belongs to")
    timestamp: datetime = Field(..., description="When the measurement was taken")
    created_at: datetime = Field(..., description="When the measurement record was created")

    class Config:
        from_attributes = True


class CETestDeviationBase(BaseModel):
    """Base C&E test deviation schema"""
    deviation_type: str = Field(
        ..., 
        max_length=100,
        description="Type of deviation (pressure_drop, velocity_exceeded, etc.)"
    )
    severity: CETestSeverity = Field(..., description="Severity level (minor, major, critical)")
    location_id: str = Field(
        ..., 
        max_length=255,
        description="Location where the deviation was detected"
    )
    expected_value: Optional[float] = Field(None, description="Expected value according to standards")
    actual_value: float = Field(..., description="Actual measured value")
    tolerance_percentage: Optional[float] = Field(None, ge=0, description="Allowed tolerance percentage")
    deviation_percentage: float = Field(..., ge=0, description="Percentage deviation from expected value")
    description: Optional[str] = Field(None, description="Description of the deviation")
    recommended_action: Optional[str] = Field(None, description="Recommended action to address the deviation")


class CETestDeviationCreate(CETestDeviationBase):
    """Schema for creating a new C&E test deviation"""
    test_session_id: UUID = Field(..., description="C&E test session this deviation belongs to")


class CETestDeviationUpdate(BaseModel):
    """Schema for updating an existing C&E test deviation"""
    is_resolved: Optional[bool] = Field(None, description="Whether this deviation has been resolved")
    resolved_by: Optional[UUID] = Field(None, description="User who resolved this deviation")
    description: Optional[str] = Field(None, description="Description of the deviation")
    recommended_action: Optional[str] = Field(None, description="Recommended action to address the deviation")


class CETestDeviationRead(CETestDeviationBase):
    """Schema for reading C&E test deviation data"""
    id: UUID = Field(..., description="Unique deviation identifier")
    test_session_id: UUID = Field(..., description="C&E test session this deviation belongs to")
    is_resolved: bool = Field(..., description="Whether this deviation has been resolved")
    resolved_at: Optional[datetime] = Field(None, description="When the deviation was resolved")
    resolved_by: Optional[UUID] = Field(None, description="User who resolved this deviation")
    created_at: datetime = Field(..., description="When the deviation was recorded")

    class Config:
        from_attributes = True


class CETestReportBase(BaseModel):
    """Base C&E test report schema"""
    report_type: str = Field(
        default="compliance_report",
        max_length=100,
        description="Type of report generated"
    )
    report_data: Dict[str, Any] = Field(..., description="The report content and data")
    is_final: bool = Field(
        default=False,
        description="Whether this is the final report for the session"
    )


class CETestReportCreate(CETestReportBase):
    """Schema for creating a new C&E test report"""
    test_session_id: UUID = Field(..., description="C&E test session this report belongs to")


class CETestReportRead(CETestReportBase):
    """Schema for reading C&E test report data"""
    id: UUID = Field(..., description="Unique report identifier")
    test_session_id: UUID = Field(..., description="C&E test session this report belongs to")
    generated_by: UUID = Field(..., description="User who generated this report")
    generated_at: datetime = Field(..., description="When the report was generated")

    class Config:
        from_attributes = True


class CETestSessionWithDetails(CETestSessionRead):
    """Schema for C&E test session with related data"""
    measurements: List[CETestMeasurementRead] = Field(default_factory=list)
    deviations: List[CETestDeviationRead] = Field(default_factory=list)
    reports: List[CETestReportRead] = Field(default_factory=list)


class CETestSessionListResponse(BaseModel):
    """Schema for C&E test session list API response"""
    sessions: List[CETestSessionRead] = Field(..., description="List of C&E test sessions")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")
    has_more: bool = Field(..., description="Whether there are more results")
    total_items: Optional[int] = Field(None, description="Optional total count for paginated queries")


class CETestAnalysisRequest(BaseModel):
    """Schema for requesting C&E test analysis"""
    test_session_id: UUID = Field(..., description="C&E test session to analyze")
    analysis_type: str = Field(
        default="compliance_analysis",
        description="Type of analysis to perform"
    )
    include_recommendations: bool = Field(
        default=True,
        description="Whether to include recommendations in the analysis"
    )


class CETestAnalysisResponse(BaseModel):
    """Schema for C&E test analysis response"""
    test_session_id: UUID = Field(..., description="C&E test session that was analyzed")
    analysis_type: str = Field(..., description="Type of analysis performed")
    compliance_score: float = Field(..., ge=0, le=100, description="Overall compliance score (0-100)")
    deviation_count: int = Field(..., description="Number of deviations found")
    critical_deviations: int = Field(..., description="Number of critical deviations")
    major_deviations: int = Field(..., description="Number of major deviations")
    minor_deviations: int = Field(..., description="Number of minor deviations")
    analysis_summary: str = Field(..., description="Summary of the analysis")
    recommendations: Optional[List[str]] = Field(None, description="List of recommendations")
    generated_at: datetime = Field(..., description="When the analysis was generated")
