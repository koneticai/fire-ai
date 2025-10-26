"""
Pydantic schemas for Interface Test API endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field

from .interface_test_enums import InterfaceType, SessionStatus, ComplianceOutcome


class InterfaceTestDefinitionBase(BaseModel):
    """Base schema for interface test definitions."""

    interface_type: InterfaceType = Field(
        ...,
        description="Interface scenario type (manual_override, alarm_coordination, etc.)",
    )
    location_id: str = Field(
        ...,
        max_length=100,
        description="Unique identifier for the control location",
    )
    location_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Human readable location name",
    )
    test_action: Optional[str] = Field(
        None,
        description="Action technicians should perform during the test",
    )
    expected_result: Optional[str] = Field(
        None,
        description="Expected system response when action is performed",
    )
    expected_response_time_s: Optional[int] = Field(
        None,
        ge=0,
        description="Expected response time in seconds according to baseline",
    )
    guidance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured guidance and checklists",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the definition is currently active",
    )


class InterfaceTestDefinitionCreate(InterfaceTestDefinitionBase):
    """Schema for creating a new interface test definition."""

    building_id: UUID = Field(..., description="Building this definition belongs to")


class InterfaceTestDefinitionUpdate(BaseModel):
    """Schema for updating an interface test definition."""

    interface_type: Optional[InterfaceType] = None
    location_id: Optional[str] = Field(None, max_length=100)
    location_name: Optional[str] = Field(None, max_length=255)
    test_action: Optional[str] = None
    expected_result: Optional[str] = None
    expected_response_time_s: Optional[int] = Field(None, ge=0)
    guidance: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class InterfaceTestDefinitionRead(InterfaceTestDefinitionBase):
    """Schema for reading interface test definition data."""

    id: UUID = Field(..., description="Definition identifier")
    building_id: UUID = Field(..., description="Building identifier")
    created_by: Optional[UUID] = Field(None, description="User who created the definition")
    created_at: datetime = Field(..., description="When the definition was created")
    updated_at: datetime = Field(..., description="When the definition was last updated")

    class Config:
        from_attributes = True


class InterfaceTestSessionCreate(BaseModel):
    """Schema for creating an interface test session."""

    definition_id: UUID = Field(..., description="Baseline definition to execute")
    test_session_id: Optional[UUID] = Field(
        None, description="Optional link to broader fire test session"
    )
    status: SessionStatus = Field(
        default=SessionStatus.SCHEDULED,
        description="Initial status for the interface test",
    )
    expected_response_time_s: Optional[int] = Field(
        None,
        ge=0,
        description="Override expected response time in seconds",
    )
    observed_response_time_s: Optional[float] = Field(
        None,
        ge=0,
        description="Observed response time in seconds (if already captured)",
    )
    observed_outcome: Dict[str, Any] = Field(
        default_factory=dict,
        description="Observed outcome details captured during execution",
    )
    failure_reasons: List[str] = Field(
        default_factory=list,
        description="Initial failure reasons if known on creation",
    )
    validation_summary: Optional[str] = Field(
        None,
        description="Initial validation summary if already available",
    )
    started_at: Optional[datetime] = Field(
        None, description="Execution start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Execution completion timestamp"
    )


class InterfaceTestSessionUpdate(BaseModel):
    """Schema for updating an interface test session."""

    status: Optional[SessionStatus] = None
    compliance_outcome: Optional[ComplianceOutcome] = None
    expected_response_time_s: Optional[int] = Field(None, ge=0)
    observed_response_time_s: Optional[float] = Field(None, ge=0)
    observed_outcome: Optional[Dict[str, Any]] = None
    failure_reasons: Optional[List[str]] = None
    validation_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    validated_by: Optional[UUID] = None


class InterfaceTestSessionRead(BaseModel):
    """Schema for reading interface test session data."""

    id: UUID = Field(..., description="Session identifier")
    definition_id: UUID = Field(..., description="Baseline definition identifier")
    test_session_id: Optional[UUID] = Field(
        None, description="Linked fire test session identifier"
    )
    building_id: UUID = Field(..., description="Building identifier")
    interface_type: InterfaceType = Field(..., description="Interface scenario type")
    location_id: str = Field(..., description="Location identifier")
    status: SessionStatus = Field(..., description="Current execution status")
    compliance_outcome: ComplianceOutcome = Field(..., description="Compliance outcome")
    expected_response_time_s: Optional[int] = Field(
        None, description="Expected response time in seconds"
    )
    observed_response_time_s: Optional[float] = Field(
        None, description="Observed response time in seconds"
    )
    response_time_delta_s: Optional[float] = Field(
        None, description="Difference between observed and expected times"
    )
    observed_outcome: Optional[Dict[str, Any]] = Field(
        None, description="Structured observations captured during execution"
    )
    failure_reasons: List[str] = Field(
        default_factory=list,
        description="List of failure reasons when outcome is fail",
    )
    validation_summary: Optional[str] = Field(
        None, description="Summary generated by validator service"
    )
    started_at: Optional[datetime] = Field(
        None, description="Execution start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Execution completion timestamp"
    )
    validated_at: Optional[datetime] = Field(
        None, description="Validation completion timestamp"
    )
    created_by: Optional[UUID] = Field(None, description="User who created the session")
    validated_by: Optional[UUID] = Field(
        None, description="User who validated the session"
    )
    created_at: datetime = Field(..., description="When the session record was created")
    updated_at: datetime = Field(..., description="When the session record was last updated")

    class Config:
        from_attributes = True


class InterfaceTestEventBase(BaseModel):
    """Base schema for interface test events."""

    event_type: str = Field(
        ...,
        max_length=50,
        description="Event type recorded during execution timeline",
    )
    event_at: Optional[datetime] = Field(
        None,
        description="Timestamp the event occurred",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional notes describing the event",
    )
    event_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        alias="metadata",
        description="Structured metadata for the event",
    )

    class Config:
        populate_by_name = True


class InterfaceTestEventCreate(InterfaceTestEventBase):
    """Schema for creating an interface test event."""

    interface_test_session_id: UUID = Field(
        ..., description="Associated interface test session identifier"
    )


class InterfaceTestEventRead(InterfaceTestEventBase):
    """Schema for reading interface test event data."""

    id: UUID = Field(..., description="Event identifier")
    interface_test_session_id: UUID = Field(
        ..., description="Associated interface test session identifier"
    )
    created_at: datetime = Field(..., description="When the event record was created")

    class Config:
        from_attributes = True
        populate_by_name = True


class InterfaceTestSessionWithEvents(InterfaceTestSessionRead):
    """Schema for interface test session including timeline events."""

    events: List[InterfaceTestEventRead] = Field(
        default_factory=list,
        description="Timeline events associated with the session",
    )


class InterfaceTestSessionListResponse(BaseModel):
    """Schema for listing interface test sessions with cursor pagination."""

    sessions: List[InterfaceTestSessionRead] = Field(
        ..., description="Interface test sessions"
    )
    next_cursor: Optional[str] = Field(
        None, description="Cursor for fetching the next page"
    )
    has_more: bool = Field(..., description="Whether more sessions are available")


class InterfaceTestValidationRequest(BaseModel):
    """Schema for interface test validation request."""

    session_id: UUID = Field(..., description="Interface test session to validate")
    tolerance_seconds: float = Field(
        2.0,
        ge=0,
        description="Allowed variance in response time compared to expected",
    )
    validator_user_id: Optional[UUID] = Field(
        None, description="Override validator user (defaults to current user)"
    )


class InterfaceTestValidationResponse(BaseModel):
    """Schema for interface test validation response."""

    session_id: UUID = Field(..., description="Validated interface test session")
    compliance_outcome: ComplianceOutcome = Field(..., description="Resulting compliance outcome")
    expected_response_time_s: Optional[int] = Field(
        None, description="Baseline expected response time in seconds"
    )
    observed_response_time_s: Optional[float] = Field(
        None, description="Observed response time in seconds"
    )
    response_time_delta_s: Optional[float] = Field(
        None, description="Difference between observed and expected times"
    )
    tolerance_seconds: float = Field(
        ..., description="Tolerance used during validation"
    )
    failure_reasons: List[str] = Field(
        default_factory=list,
        description="Failure reasons generated by validator",
    )
    validation_summary: str = Field(..., description="Summary message from validator")
    validated_at: datetime = Field(
        ..., description="Timestamp the validation completed"
    )
