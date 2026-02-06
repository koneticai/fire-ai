"""
Versioned AS1851 rules router for FireMode Compliance Platform
Implements immutable rule management with semantic versioning

Refactored to use async SQLAlchemy instead of raw psycopg2.
"""

import ipaddress
from typing import List, Optional
from uuid import UUID

import semver
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AS1851Rule, AS1851RuleCreate, AS1851RuleDB
from ..models.audit_log import AuditLog
from ..dependencies import get_current_active_user
from ..database.core import get_db
from ..schemas.token import TokenData

router = APIRouter(tags=["AS1851 Rules (Versioned)"])


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


@router.post(
    "/",
    response_model=AS1851Rule,
    status_code=status.HTTP_201_CREATED,
    summary="Create Versioned AS1851 Rule",
    description="Creates a new versioned AS1851 rule. Each version is immutable and prevents duplicates."
)
async def create_versioned_rule(
    rule: AS1851RuleCreate,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new, versioned AS1851 rule. Rejects duplicates."""
    # Check if this exact version already exists
    existing_query = select(AS1851RuleDB).where(
        and_(
            AS1851RuleDB.rule_code == rule.rule_code,
            AS1851RuleDB.version == rule.version
        )
    )
    result = await db.execute(existing_query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule {rule.rule_code} version {rule.version} already exists."
        )

    # Insert the new versioned rule
    new_rule = AS1851RuleDB(
        rule_code=rule.rule_code,
        version=rule.version,
        rule_name=rule.rule_name,
        description=rule.description,
        rule_schema=rule.rule_schema,
        is_active=True
    )

    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)

    return AS1851Rule(
        id=new_rule.id,
        rule_code=new_rule.rule_code,
        version=new_rule.version,
        rule_name=new_rule.rule_name,
        description=new_rule.description,
        rule_schema=new_rule.rule_schema,
        is_active=True,
        created_at=new_rule.created_at
    )


@router.get(
    "/",
    response_model=List[AS1851Rule],
    summary="List All Active Versioned Rules",
    description="Lists all active AS1851 rule versions available in the system."
)
async def get_all_active_versioned_rules(
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all active AS1851 rules (all versions)."""
    query = (
        select(AS1851RuleDB)
        .where(AS1851RuleDB.is_active == True)
        .order_by(AS1851RuleDB.rule_code, AS1851RuleDB.version.desc())
    )
    result = await db.execute(query)
    db_rules = result.scalars().all()

    return [
        AS1851Rule(
            id=rule.id,
            rule_code=rule.rule_code,
            version=rule.version,
            rule_name=rule.rule_name,
            description=rule.description,
            rule_schema=rule.rule_schema,
            is_active=rule.is_active,
            created_at=rule.created_at
        )
        for rule in db_rules
    ]


@router.get(
    "/{rule_code}/latest",
    response_model=AS1851Rule,
    summary="Get Latest Active Rule Version",
    description="Gets the latest active version of a rule by its code using semantic versioning."
)
async def get_latest_active_rule_by_code(
    rule_code: str,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Gets the latest active version of a rule by its code."""
    query = (
        select(AS1851RuleDB)
        .where(
            and_(
                AS1851RuleDB.rule_code == rule_code,
                AS1851RuleDB.is_active == True
            )
        )
        .order_by(AS1851RuleDB.version.desc())
    )
    result = await db.execute(query)
    db_rules = result.scalars().all()

    if not db_rules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active rule with code {rule_code} not found."
        )

    # Find the highest semantic version
    latest_rule = None
    latest_version = None

    for rule in db_rules:
        try:
            current_version = semver.VersionInfo.parse(rule.version)
            if latest_version is None or current_version > latest_version:
                latest_version = current_version
                latest_rule = rule
        except ValueError:
            # Skip invalid semantic versions
            continue

    if latest_rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No valid semantic versions found for rule {rule_code}"
        )

    return AS1851Rule(
        id=latest_rule.id,
        rule_code=latest_rule.rule_code,
        version=latest_rule.version,
        rule_name=latest_rule.rule_name,
        description=latest_rule.description,
        rule_schema=latest_rule.rule_schema,
        is_active=latest_rule.is_active,
        created_at=latest_rule.created_at
    )


@router.get(
    "/{rule_code}/versions",
    response_model=List[AS1851Rule],
    summary="Get All Rule Versions",
    description="Gets all versions of a specific rule by its code, sorted by version."
)
async def get_all_rule_versions(
    rule_code: str,
    include_inactive: bool = False,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Gets all versions of a specific rule by its code."""
    if include_inactive:
        query = (
            select(AS1851RuleDB)
            .where(AS1851RuleDB.rule_code == rule_code)
            .order_by(AS1851RuleDB.version.desc())
        )
    else:
        query = (
            select(AS1851RuleDB)
            .where(
                and_(
                    AS1851RuleDB.rule_code == rule_code,
                    AS1851RuleDB.is_active == True
                )
            )
            .order_by(AS1851RuleDB.version.desc())
        )

    result = await db.execute(query)
    db_rules = result.scalars().all()

    return [
        AS1851Rule(
            id=rule.id,
            rule_code=rule.rule_code,
            version=rule.version,
            rule_name=rule.rule_name,
            description=rule.description,
            rule_schema=rule.rule_schema,
            is_active=rule.is_active,
            created_at=rule.created_at
        )
        for rule in db_rules
    ]


@router.put(
    "/id/{rule_id}/deactivate",
    response_model=AS1851Rule,
    summary="Deactivate Rule Version",
    description="Deactivates a specific rule version. This is the only way to 'update' a rule - no in-place modifications allowed."
)
async def deactivate_rule_version(
    rule_id: UUID,
    request: Request,
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivates a specific rule version. This is the only way to 'update' a rule."""
    # Get the current rule before deactivating
    query = select(AS1851RuleDB).where(AS1851RuleDB.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )

    if not rule.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rule is already deactivated"
        )

    # Deactivate the rule
    rule.is_active = False

    # Log the deactivation in audit log
    client_ip = _safe_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    audit_entry = AuditLog(
        user_id=current_user.user_id,
        action="deactivate_rule",
        resource_type="as1851_rule",
        resource_id=rule_id,
        old_values={
            "is_active": True,
            "rule_code": rule.rule_code,
            "version": rule.version
        },
        new_values={
            "is_active": False,
            "rule_code": rule.rule_code,
            "version": rule.version
        },
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit_entry)
    await db.commit()

    return AS1851Rule(
        id=rule.id,
        rule_code=rule.rule_code,
        version=rule.version,
        rule_name=rule.rule_name,
        description=rule.description,
        rule_schema=rule.rule_schema,
        is_active=False,
        created_at=rule.created_at
    )
