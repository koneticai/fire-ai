"""
Defects CRUD API Router for FireMode Compliance Platform
Complete implementation with all 6 endpoints for defect management
"""

import base64
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.core import get_db
from ..dependencies import get_current_active_user
from ..models.defects import Defect
from ..models.test_sessions import TestSession
from ..models.buildings import Building
from ..schemas.auth import TokenPayload
from ..schemas.defect import (
    DefectCreate,
    DefectRead,
    DefectUpdate,
    DefectWithEvidence,
    DefectListResponse,
    DefectSeverity,
    DefectStatus
)

router = APIRouter(prefix="/v1/defects", tags=["defects"])


@router.post("/", response_model=DefectRead, status_code=201)
async def create_defect(
    defect_data: DefectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """Create new defect during inspection"""
    # Validate test_session exists and get building_id
    result = await db.execute(
        select(TestSession).where(
            and_(
                TestSession.id == defect_data.test_session_id,
                TestSession.created_by == current_user.user_id
            )
        )
    )
    test_session = result.scalar_one_or_none()
    
    if not test_session:
        raise HTTPException(
            status_code=404, 
            detail="Test session not found or you don't have permission to access it"
        )
    
    # Validate severity enum
    try:
        DefectSeverity(defect_data.severity)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity '{defect_data.severity}'. Must be one of: critical, high, medium, low"
        )
    
    # Create defect with auto-populated fields
    defect = Defect(
        id=uuid.uuid4(),
        test_session_id=defect_data.test_session_id,
        building_id=test_session.building_id,
        severity=defect_data.severity,
        category=defect_data.category,
        description=defect_data.description,
        as1851_rule_code=defect_data.as1851_rule_code,
        asset_id=defect_data.asset_id,
        status='open',
        discovered_at=datetime.utcnow(),
        created_by=current_user.user_id,
        evidence_ids=[],
        repair_evidence_ids=[]
    )
    
    db.add(defect)
    await db.commit()
    await db.refresh(defect)
    
    return defect


@router.get("/", response_model=DefectListResponse)
async def list_defects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    status: Optional[List[DefectStatus]] = Query(None, description="Filter by defect status"),
    severity: Optional[List[DefectSeverity]] = Query(None, description="Filter by defect severity"),
    building_id: Optional[uuid.UUID] = Query(None, description="Filter by building ID"),
    test_session_id: Optional[uuid.UUID] = Query(None, description="Filter by test session ID"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """List all defects (paginated, filterable)"""
    # Base query with user's buildings filter
    query = select(Defect).join(Building).where(
        Building.owner_id == current_user.user_id
    )
    
    # Apply filters
    conditions = []
    
    if status:
        conditions.append(Defect.status.in_([s.value for s in status]))
    if severity:
        conditions.append(Defect.severity.in_([s.value for s in severity]))
    if building_id:
        conditions.append(Defect.building_id == building_id)
    if test_session_id:
        conditions.append(Defect.test_session_id == test_session_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count
    count_query = select(func.count(Defect.id)).join(Building).where(
        Building.owner_id == current_user.user_id
    )
    if conditions:
        count_query = count_query.where(and_(*conditions))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Defect.discovered_at)).offset(offset).limit(page_size + 1)
    
    result = await db.execute(query)
    defects = result.scalars().all()
    
    # Determine if there are more pages
    has_more = len(defects) > page_size
    if has_more:
        defects = defects[:page_size]
    
    return DefectListResponse(
        defects=defects,
        total=total,
        next_cursor=None,  # Using page-based pagination
        has_more=has_more
    )


@router.get("/{defect_id}", response_model=DefectWithEvidence)
async def get_defect(
    defect_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """Get single defect with full details"""
    # Get defect with ownership check
    result = await db.execute(
        select(Defect).join(Building).where(
            and_(
                Defect.id == defect_id,
                Building.owner_id == current_user.user_id
            )
        )
    )
    defect = result.scalar_one_or_none()
    
    if not defect:
        raise HTTPException(
            status_code=404, 
            detail="Defect not found or you don't have permission to access it"
        )
    
    # For now, return defect without expanded evidence metadata
    # TODO: Implement evidence expansion when evidence service is available
    return DefectWithEvidence(
        **defect.__dict__,
        evidence_metadata=None,
        repair_evidence_metadata=None
    )


@router.patch("/{defect_id}", response_model=DefectRead)
async def update_defect(
    defect_id: uuid.UUID,
    defect_update: DefectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """Update defect (acknowledge, change status)"""
    # Get defect with ownership check
    result = await db.execute(
        select(Defect).join(Building).where(
            and_(
                Defect.id == defect_id,
                Building.owner_id == current_user.user_id
            )
        )
    )
    defect = result.scalar_one_or_none()
    
    if not defect:
        raise HTTPException(
            status_code=404, 
            detail="Defect not found or you don't have permission to access it"
        )
    
    # Validate status transitions
    if defect_update.status:
        current_status = DefectStatus(defect.status)
        new_status = defect_update.status
        
        # Define valid status transitions
        valid_transitions = {
            DefectStatus.OPEN: [DefectStatus.ACKNOWLEDGED],
            DefectStatus.ACKNOWLEDGED: [DefectStatus.REPAIR_SCHEDULED],
            DefectStatus.REPAIR_SCHEDULED: [DefectStatus.REPAIRED],
            DefectStatus.REPAIRED: [DefectStatus.VERIFIED],
            DefectStatus.VERIFIED: [DefectStatus.CLOSED]
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status transition from '{current_status.value}' to '{new_status.value}'"
            )
    
    # Update fields
    update_data = defect_update.dict(exclude_unset=True)
    
    # Auto-populate timestamps based on status changes
    if defect_update.status == DefectStatus.ACKNOWLEDGED:
        update_data['acknowledged_at'] = datetime.utcnow()
        update_data['acknowledged_by'] = current_user.user_id
    elif defect_update.status == DefectStatus.REPAIRED:
        update_data['repaired_at'] = datetime.utcnow()
    elif defect_update.status == DefectStatus.VERIFIED:
        update_data['verified_at'] = datetime.utcnow()
    elif defect_update.status == DefectStatus.CLOSED:
        update_data['closed_at'] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(defect, field, value)
    
    await db.commit()
    await db.refresh(defect)
    
    return defect


@router.get("/buildings/{building_id}/defects", response_model=List[DefectRead])
async def get_building_defects(
    building_id: uuid.UUID,
    status: Optional[DefectStatus] = Query(None, description="Filter by defect status"),
    severity: Optional[DefectSeverity] = Query(None, description="Filter by defect severity"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """Get all defects for a building (for compliance score)"""
    # Validate building ownership
    building_result = await db.execute(
        select(Building).where(
            and_(
                Building.id == building_id,
                Building.owner_id == current_user.user_id
            )
        )
    )
    building = building_result.scalar_one_or_none()
    
    if not building:
        raise HTTPException(
            status_code=404, 
            detail="Building not found or you don't have permission to access it"
        )
    
    # Query defects for this building
    query = select(Defect).where(Defect.building_id == building_id)
    
    # Apply filters
    conditions = []
    if status:
        conditions.append(Defect.status == status.value)
    if severity:
        conditions.append(Defect.severity == severity.value)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(desc(Defect.discovered_at))
    
    result = await db.execute(query)
    defects = result.scalars().all()
    
    return defects


@router.get("/test-sessions/{session_id}/defects", response_model=List[DefectRead])
async def get_test_session_defects(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """Get defects discovered in this inspection"""
    # Validate test session ownership
    session_result = await db.execute(
        select(TestSession).where(
            and_(
                TestSession.id == session_id,
                TestSession.created_by == current_user.user_id
            )
        )
    )
    test_session = session_result.scalar_one_or_none()
    
    if not test_session:
        raise HTTPException(
            status_code=404, 
            detail="Test session not found or you don't have permission to access it"
        )
    
    # Query defects for this test session
    result = await db.execute(
        select(Defect)
        .where(Defect.test_session_id == session_id)
        .order_by(desc(Defect.discovered_at))
    )
    defects = result.scalars().all()
    
    return defects
