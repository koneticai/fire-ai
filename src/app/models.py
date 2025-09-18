"""
Pydantic models for the FireMode Compliance Platform
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

import semver
from pydantic import BaseModel, Field, validator

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

# AS1851 rules models - Versioned and immutable
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

class AS1851RuleCreate(AS1851RuleBase):
    version: str = Field(
        description="Semantic version for this rule (e.g., '1.2.0')",
        examples=["1.0.0", "2.1.0"]
    )
    
    @validator('version')
    def validate_version(cls, v):
        try:
            semver.VersionInfo.parse(v)
        except ValueError:
            raise ValueError("Version string must be a valid semantic version (e.g., '1.2.3')")
        return v

class AS1851Rule(AS1851RuleBase):
    id: UUID = Field(
        ...,
        description="Unique identifier for the AS1851 rule record"
    )
    version: str = Field(
        ...,
        description="Semantic version for this rule"
    )
    is_active: bool = Field(
        True,
        description="Whether this rule version is currently active"
    )
    created_at: datetime = Field(
        ...,
        description="When this rule version was created"
    )

# Classification models for v1/classify endpoint
class FaultDataInput(BaseModel):
    item_code: str = Field(
        description="The AS1851 rule code for the item being inspected",
        examples=["AS1851-2012-FE-01"]
    )
    observed_condition: str = Field(
        description="A machine-readable key for the observed condition",
        examples=["extinguisher_pressure_low"]
    )

class ClassificationResult(BaseModel):
    classification: str = Field(
        description="The resulting classification based on the rule",
        examples=["critical_defect"]
    )
    rule_applied: str = Field(
        description="The rule code that was applied",
        examples=["AS1851-2012-FE-01"]
    )
    version_applied: str = Field(
        description="The specific version of the rule that was applied",
        examples=["1.2.0"]
    )
    audit_log_id: UUID = Field(
        description="The unique ID for the audit log entry created for this transaction"
    )

# Legacy classification models (kept for backward compatibility)
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

# User profile models
class UserProfile(BaseModel):
    id: UUID = Field(
        description="Unique identifier for the user"
    )
    username: str = Field(
        description="Username for the user account"
    )
    email: str = Field(
        description="Email address for the user"
    )
    full_name: str = Field(
        description="Full name of the user (decrypted)"
    )
    is_active: bool = Field(
        description="Whether the user account is active"
    )
    created_at: datetime = Field(
        description="When the user account was created"
    )

# Audit log response models
class AuditLogEntry(BaseModel):
    id: UUID = Field(
        description="Unique identifier for the audit log entry"
    )
    action: str = Field(
        description="Action that was performed",
        examples=["CLASSIFY_FAULT", "CLASSIFY_FAULT_FAILED"]
    )
    resource_type: str = Field(
        description="Type of resource that was acted upon",
        examples=["as1851_rule", "token"]
    )
    resource_id: Optional[UUID] = Field(
        None,
        description="ID of the specific resource"
    )
    old_values: Optional[Dict[str, Any]] = Field(
        None,
        description="Previous values before the action"
    )
    new_values: Optional[Dict[str, Any]] = Field(
        None,
        description="New values after the action"
    )
    ip_address: Optional[str] = Field(
        None,
        description="IP address from which the action was performed"
    )
    user_agent: Optional[str] = Field(
        None,
        description="User agent string from the request"
    )
    created_at: datetime = Field(
        description="When the audit log entry was created"
    )

# API Response models
class APIResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[int] = None