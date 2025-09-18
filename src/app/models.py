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
    session_name: str = Field(..., min_length=1, max_length=255)
    status: str = Field(default="active", max_length=50)
    session_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

class TestSessionCreate(TestSessionBase):
    building_id: UUID

class TestSession(TestSessionBase, TimestampedModel):
    id: UUID
    building_id: UUID
    vector_clock: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_by: Optional[UUID] = None

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
    rule_code: str = Field(..., min_length=1, max_length=50)
    rule_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    rule_schema: Dict[str, Any]
    is_active: bool = True

class AS1851RuleCreate(AS1851RuleBase):
    pass

class AS1851Rule(AS1851RuleBase, TimestampedModel):
    id: UUID

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