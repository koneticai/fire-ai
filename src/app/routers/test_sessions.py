"""
Test Sessions API router with async operations and CRDT support
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from ..database.core import get_db
from ..models import TestSession, Building
from ..schemas.test_session import (
    TestSessionCreate, TestSessionRead, TestSessionUpdate, 
    TestSessionListResponse, OfflineBundleResponse
)
from ..dependencies import get_current_active_user
from ..schemas.auth import TokenPayload
from ..utils.pagination import encode_cursor, decode_cursor, create_pagination_filter

router = APIRouter(prefix="/v1/tests/sessions", tags=["test_sessions"])


@router.post("/", response_model=TestSessionRead, status_code=status.HTTP_201_CREATED)
async def create_test_session(
    session: TestSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Create a new test session with CRDT initialization.
    
    Validates building exists and initializes vector clock.
    """
    # Verify building exists
    building_query = select(Building).where(Building.id == session.building_id)
    building_result = await db.execute(building_query)
    building = building_result.scalar_one_or_none()
    
    if not building:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Building not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    # Initialize vector clock for CRDT
    initial_vector_clock = {
        str(current_user.user_id): 1
    }
    
    # Create test session
    db_session = TestSession(
        building_id=session.building_id,
        session_name=session.session_name,
        status=session.status or "active",
        session_data=session.session_data or {},
        vector_clock=initial_vector_clock,
        created_by=current_user.user_id
    )
    
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    
    return TestSessionRead.from_orm(db_session)


@router.get("/", response_model=TestSessionListResponse)
async def list_test_sessions(
    limit: int = Query(default=50, ge=1, le=100, description="Number of sessions to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    building_id: Optional[uuid.UUID] = Query(None, description="Filter by building ID"),
    status: Optional[str] = Query(None, description="Filter by session status"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    List test sessions with cursor-based pagination.
    
    Implements CRDT-aware pagination using vector clocks.
    """
    # Decode cursor for pagination
    cursor_data = decode_cursor(cursor)
    
    # Build base query
    query = select(TestSession).order_by(TestSession.created_at.asc(), TestSession.id.asc())
    
    # Apply pagination filters
    pagination_conditions = create_pagination_filter(cursor_data)
    if pagination_conditions:
        query = query.where(and_(*pagination_conditions))
    
    # Apply filters
    conditions = []
    if building_id:
        conditions.append(TestSession.building_id == building_id)
    if status:
        conditions.append(TestSession.status == status)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply limit + 1 to check if there are more results
    query = query.limit(limit + 1)
    
    # Execute query
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    # Check if there are more results
    has_more = len(sessions) > limit
    if has_more:
        sessions = sessions[:limit]
    
    # Generate next cursor
    next_cursor = None
    if has_more and sessions:
        last_session = sessions[-1]
        next_cursor = encode_cursor({
            "id": last_session.id,
            "created_at": last_session.created_at,
            "vector_clock": last_session.vector_clock or {}
        })
    
    # Convert to response format
    session_reads = [TestSessionRead.from_orm(session) for session in sessions]
    
    return TestSessionListResponse(
        sessions=session_reads,
        next_cursor=next_cursor,
        has_more=has_more
    )


@router.get("/{session_id}", response_model=TestSessionRead)
async def get_test_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get a specific test session by ID.
    """
    query = select(TestSession).where(TestSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Test session not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    return TestSessionRead.from_orm(session)


@router.get("/{session_id}/offline-bundle", response_model=OfflineBundleResponse)
async def get_offline_bundle(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Generate offline bundle for test session.
    
    Provides complete session data for offline operations with CRDT sync.
    """
    # Get session with related data
    query = select(TestSession).options(
        selectinload(TestSession.building),
        selectinload(TestSession.evidence)
    ).where(TestSession.id == session_id)
    
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Test session not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    # Build offline bundle
    bundle_data = {
        "session": {
            "id": str(session.id),
            "session_name": session.session_name,
            "status": session.status,
            "session_data": session.session_data or {},
            "building_id": str(session.building_id)
        },
        "building": {
            "id": str(session.building.id),
            "name": session.building.name,
            "address": session.building.address,
            "building_type": session.building.building_type
        } if session.building else None,
        "evidence": [
            {
                "id": str(evidence.id),
                "evidence_type": evidence.evidence_type,
                "file_path": evidence.file_path,
                "metadata": evidence.metadata or {},
                "checksum": evidence.checksum
            }
            for evidence in (session.evidence or [])
        ],
        "sync_metadata": {
            "bundle_created_at": datetime.utcnow().isoformat(),
            "user_id": str(current_user.user_id)
        }
    }
    
    return OfflineBundleResponse(
        session_id=session.id,
        bundle_data=bundle_data,
        vector_clock=session.vector_clock or {},
        expires_at=datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    )


@router.put("/{session_id}", response_model=TestSessionRead)
async def update_test_session(
    session_id: uuid.UUID,
    session_update: TestSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Update a test session with CRDT vector clock management.
    """
    # Get existing session
    query = select(TestSession).where(TestSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Test session not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    # Update vector clock
    current_vector_clock = session.vector_clock or {}
    user_key = str(current_user.user_id)
    current_vector_clock[user_key] = current_vector_clock.get(user_key, 0) + 1
    
    # Update fields
    update_data = session_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)
    
    # Update vector clock
    session.vector_clock = current_vector_clock
    
    # Save changes
    await db.commit()
    await db.refresh(session)
    
    return TestSessionRead.from_orm(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Delete a test session and related data.
    """
    query = select(TestSession).where(TestSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Test session not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    # Delete session (cascade will handle related evidence)
    await db.delete(session)
    await db.commit()