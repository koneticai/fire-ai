"""
Pydantic models for the FireMode Compliance Platform
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field

# Base models
class TimestampedModel(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None

# User models
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)

class User(UserBase, TimestampedModel):
    id: UUID
    # Note: full_name is encrypted in database, so not included in response

# Building models
class BuildingBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    building_type: str = Field(..., min_length=1, max_length=100)
    compliance_status: str = Field(default="pending", max_length=50)

class BuildingCreate(BuildingBase):
    owner_id: Optional[UUID] = None

class Building(BuildingBase, TimestampedModel):
    id: UUID
    owner_id: Optional[UUID] = None

# Test session models
class TestSessionBase(BaseModel):
    session_name: str = Field(
        min_length=1, 
        max_length=255,
        description="Descriptive name for the fire safety testing session",
        examples=["Building A - Q2 2024 Monthly Inspection"]
    )
    status: str = Field(
        default="active", 
        max_length=50,
        description="Current status of the testing session",
        examples=["active"]
    )
    session_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Flexible data storage for session-specific information and test results",
        examples=[{
            "inspector": "John Smith",
            "weather_conditions": "Clear",
            "equipment_tested": ["FE-001", "FE-002"]
        }]
    )

class TestSessionCreate(TestSessionBase):
    building_id: UUID

class TestSession(TestSessionBase, TimestampedModel):
    id: UUID = Field(
        ...,
        description="Unique identifier for the test session"
    )
    building_id: UUID = Field(
        ...,
        description="UUID of the building being tested"
    )
    vector_clock: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="CRDT vector clock for conflict-free distributed updates",
        examples=[{"actor_1": 5, "actor_2": 3}]
    )
    created_by: Optional[UUID] = Field(
        None,
        description="UUID of the user who created this test session"
    )

# Evidence models
class EvidenceBase(BaseModel):
    evidence_type: str = Field(..., min_length=1, max_length=100)
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class EvidenceCreate(EvidenceBase):
    session_id: UUID
    data: Optional[str] = None

class Evidence(EvidenceBase, TimestampedModel):
    id: UUID
    session_id: UUID
    checksum: Optional[str] = None

# AS1851 rules models
class AS1851RuleBase(BaseModel):
    rule_code: str = Field(
        min_length=1, 
        max_length=50,
        description="Unique identifier for the AS1851 rule",
        examples=["AS1851-2012-FE-01"]
    )
    rule_name: str = Field(
        min_length=1, 
        max_length=255,
        description="Human-readable name for the compliance rule",
        examples=["Fire Extinguisher Monthly Inspection"]
    )
    description: Optional[str] = Field(
        None,
        description="Detailed description of what this rule checks and validates",
        examples=["Validates that fire extinguishers are inspected monthly according to AS1851-2012 standards"]
    )
    rule_schema: Dict[str, Any] = Field(
        description="JSON schema defining the validation rules and required fields for compliance",
        examples=[{
            "required_fields": ["pressure_reading", "pin_status", "visual_condition"],
            "validation_rules": {
                "pressure_reading": {"type": "number", "min": 180, "max": 220}
            }
        }]
    )
    is_active: bool = Field(
        True,
        description="Whether this rule is currently active and available for use in classifications"
    )

class AS1851RuleCreate(AS1851RuleBase):
    pass

class AS1851Rule(AS1851RuleBase, TimestampedModel):
    id: UUID = Field(
        ...,
        description="Unique identifier for the AS1851 rule record"
    )

# Classification models
class FaultClassificationRequest(BaseModel):
    evidence_id: UUID
    rule_codes: List[str]
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class FaultClassificationResult(BaseModel):
    evidence_id: UUID
    classifications: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    timestamp: datetime

# Test session pagination
class TestSessionListParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    cursor: Optional[str] = None  # Base64 encoded vector_clock

class TestSessionListResponse(BaseModel):
    sessions: List[TestSession]
    next_cursor: Optional[str] = None
    has_more: bool

# CRDT operation models
class CRDTChange(BaseModel):
    operation: str
    path: List[str]
    value: Any
    timestamp: datetime
    actor_id: str

class CRDTChangesRequest(BaseModel):
    changes: List[CRDTChange]

# Token models
class TokenData(BaseModel):
    username: str
    user_id: UUID
    jti: str
    exp: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# API Response models
class APIResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[int] = None