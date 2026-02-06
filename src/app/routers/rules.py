"""
AS1851 rules router for FireMode Compliance Platform
Handles rule management and fault classification

Refactored to use async SQLAlchemy instead of raw psycopg2.
"""

import ipaddress
from datetime import datetime
from typing import List, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AS1851Rule, AS1851RuleCreate, AS1851RuleDB
from ..models.evidence import Evidence
from ..models.audit_log import AuditLog
from ..schemas.token import APIResponse, TokenData
from ..dependencies import get_current_active_user
from ..database.core import get_db


# Legacy classification models (kept for backward compatibility)
class FaultClassificationRequest(BaseModel):
    evidence_id: str
    rule_codes: List[str]
    context: Optional[str] = None


class FaultClassificationResult(BaseModel):
    classification_id: str
    evidence_id: str
    classifications: List[Any]
    confidence_scores: dict
    applied_rules: List[str]
    timestamp: Optional[datetime] = None


router = APIRouter(tags=["AS1851 Rules"])


def _safe_client_ip(request: Request) -> Optional[str]:
    """Extract a valid IP address from the request, or return None.

    Checks X-Forwarded-For first (proxy-aware), then request.client.host.
    Returns None when neither source yields a valid IPv4/IPv6 literal,
    which is safe for PostgreSQL INET columns.
    """
    raw_ip: Optional[str] = None

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        raw_ip = forwarded.split(",")[0].strip()
    elif request.client:
        raw_ip = request.client.host

    if raw_ip:
        try:
            ipaddress.ip_address(raw_ip)
            return raw_ip
        except ValueError:
            return None
    return None


@router.get(
    "/",
    response_model=List[AS1851Rule],
    summary="List AS1851 Rules",
    description="Retrieve all active AS1851 compliance rules available in the system, sorted by rule code"
)
async def list_rules(
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all active AS1851 rules"""
    query = (
        select(AS1851RuleDB)
        .where(AS1851RuleDB.is_active == True)
        .order_by(AS1851RuleDB.rule_code)
    )
    result = await db.execute(query)
    db_rules = result.scalars().all()

    return [
        AS1851Rule(
            id=rule.id,
            rule_code=rule.rule_code,
            rule_name=rule.rule_name,
            description=rule.description,
            rule_schema=rule.rule_schema,
            version=rule.version or "1.0.0",
            is_active=rule.is_active,
            created_at=rule.created_at
        )
        for rule in db_rules
    ]


@router.post(
    "/",
    response_model=AS1851Rule,
    summary="Create AS1851 Rule",
    description="Create a new AS1851 compliance rule with schema definition for fault classification"
)
async def create_rule(
    rule_data: AS1851RuleCreate,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new AS1851 rule"""
    # Check for existing rule with same code
    existing_query = select(AS1851RuleDB).where(
        AS1851RuleDB.rule_code == rule_data.rule_code
    )
    result = await db.execute(existing_query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Rule code already exists"
        )

    # Create new rule
    new_rule = AS1851RuleDB(
        rule_code=rule_data.rule_code,
        version=rule_data.version,
        rule_name=rule_data.rule_name,
        description=rule_data.description,
        rule_schema=rule_data.rule_schema,
        is_active=True
    )

    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)

    return AS1851Rule(
        id=new_rule.id,
        rule_code=new_rule.rule_code,
        rule_name=new_rule.rule_name,
        description=new_rule.description,
        rule_schema=new_rule.rule_schema,
        version=new_rule.version,
        is_active=new_rule.is_active,
        created_at=new_rule.created_at
    )


@router.get(
    "/code/{rule_code}",
    response_model=AS1851Rule,
    summary="Get AS1851 Rule by Code",
    description="Retrieve a specific AS1851 rule by its unique rule code"
)
async def get_rule_by_code(
    rule_code: str,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific rule by code"""
    query = select(AS1851RuleDB).where(AS1851RuleDB.rule_code == rule_code)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return AS1851Rule(
        id=rule.id,
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        description=rule.description,
        rule_schema=rule.rule_schema,
        version=rule.version or "1.0.0",
        is_active=rule.is_active,
        created_at=rule.created_at
    )


@router.post(
    "/classify-faults",
    response_model=FaultClassificationResult,
    summary="Classify Faults",
    description="Apply AS1851 rules to evidence for automated fault classification and compliance assessment"
)
async def classify_faults(
    classification_request: FaultClassificationRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Classify faults based on evidence and rules"""
    # Validate evidence_id is a valid UUID before querying
    try:
        evidence_uuid = UUID(classification_request.evidence_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid evidence_id: must be a valid UUID")

    # Get evidence details
    evidence_query = select(Evidence).where(
        Evidence.id == evidence_uuid
    )
    result = await db.execute(evidence_query)
    evidence = result.scalar_one_or_none()

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Get requested rules
    rules_query = (
        select(AS1851RuleDB)
        .where(AS1851RuleDB.rule_code.in_(classification_request.rule_codes))
        .where(AS1851RuleDB.is_active == True)
    )
    result = await db.execute(rules_query)
    rules = result.scalars().all()

    if not rules:
        raise HTTPException(status_code=400, detail="No valid rules found")

    # Apply rule schemas (simplified implementation)
    # NOTE: This is stubbed classification logic - returns "compliant" for all rules
    classifications = []
    confidence_scores = {}

    for rule in rules:
        classification = {
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "evidence_type": evidence.evidence_type,
            "applied_schema": rule.rule_schema,
            "result": "compliant",  # Stubbed - would contain actual classification logic
            "details": {
                "checksum_verified": bool(evidence.checksum),
                "metadata_complete": bool(evidence.metadata),
                "context_provided": bool(classification_request.context)
            }
        }
        classifications.append(classification)
        confidence_scores[rule.rule_code] = 0.85  # Mock confidence score

    # Log the classification in audit_log
    client_ip = _safe_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    audit_entry = AuditLog(
        user_id=current_user.user_id,
        action="classify_faults",
        resource_type="evidence",
        resource_id=evidence.id,
        new_values={
            "rule_codes": classification_request.rule_codes,
            "classifications": classifications,
            "confidence_scores": confidence_scores
        },
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit_entry)
    await db.commit()

    return FaultClassificationResult(
        classification_id=str(evidence.id),
        evidence_id=classification_request.evidence_id,
        classifications=classifications,
        confidence_scores=confidence_scores,
        applied_rules=[r.rule_code for r in rules],
        timestamp=datetime.utcnow()
    )


@router.get(
    "/id/{rule_id}",
    response_model=AS1851Rule,
    summary="Get AS1851 Rule by ID",
    description="Retrieve a specific AS1851 rule by its unique UUID identifier"
)
async def get_rule_by_id(
    rule_id: UUID,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific rule by UUID"""
    query = select(AS1851RuleDB).where(AS1851RuleDB.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return AS1851Rule(
        id=rule.id,
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        description=rule.description,
        rule_schema=rule.rule_schema,
        version=rule.version or "1.0.0",
        is_active=rule.is_active,
        created_at=rule.created_at
    )


@router.put(
    "/id/{rule_id}",
    response_model=AS1851Rule,
    summary="Update AS1851 Rule",
    description="Update an existing AS1851 rule by its UUID identifier"
)
async def update_rule(
    rule_id: UUID,
    rule_data: AS1851RuleCreate,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing AS1851 rule"""
    # First, check if the rule exists
    query = select(AS1851RuleDB).where(AS1851RuleDB.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Check for duplicate rule_code (if changing)
    if rule_data.rule_code != rule.rule_code:
        dup_query = select(AS1851RuleDB).where(
            AS1851RuleDB.rule_code == rule_data.rule_code
        )
        dup_result = await db.execute(dup_query)
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Rule code already exists"
            )

    # Update fields
    rule.rule_code = rule_data.rule_code
    rule.rule_name = rule_data.rule_name
    rule.description = rule_data.description
    rule.rule_schema = rule_data.rule_schema
    rule.version = rule_data.version

    await db.commit()
    await db.refresh(rule)

    return AS1851Rule(
        id=rule.id,
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        description=rule.description,
        rule_schema=rule.rule_schema,
        version=rule.version,
        is_active=rule.is_active,
        created_at=rule.created_at
    )


@router.put(
    "/{rule_code}/deactivate",
    response_model=APIResponse,
    summary="Deactivate Rule",
    description="Deactivate an AS1851 rule to prevent it from being used in new fault classifications"
)
async def deactivate_rule(
    rule_code: str,
    request: Request,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a rule"""
    query = select(AS1851RuleDB).where(AS1851RuleDB.rule_code == rule_code)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if not rule.is_active:
        raise HTTPException(status_code=400, detail="Rule is already deactivated")

    rule.is_active = False

    # Audit log for compliance traceability (parity with versioned endpoint)
    client_ip = _safe_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    audit_entry = AuditLog(
        user_id=current_user.user_id,
        action="deactivate_rule",
        resource_type="as1851_rule",
        resource_id=rule.id,
        old_values={
            "is_active": True,
            "rule_code": rule.rule_code,
            "version": rule.version,
        },
        new_values={
            "is_active": False,
            "rule_code": rule.rule_code,
            "version": rule.version,
        },
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit_entry)
    await db.commit()

    return APIResponse(
        status="success",
        message=f"Rule {rule_code} deactivated successfully"
    )
