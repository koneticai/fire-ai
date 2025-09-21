"""
Pydantic models for AS1851 Rules
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

import semver
from pydantic import BaseModel, Field, validator


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