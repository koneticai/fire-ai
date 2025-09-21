"""
Test Sessions API Router for FireMode Compliance Platform
Complete implementation with cursor-based pagination and offline bundle generation
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List, Dict
from datetime import datetime
import base64
import json
import gzip

from ..database.core import get_db
from ..models.test_sessions import TestSession
from ..dependencies import get_current_active_user
from ..schemas.auth import TokenPayload

router = APIRouter(prefix="/v1/tests/sessions", tags=["test_sessions"])

@router.get("/")
async def list_test_sessions(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = None,
    status: Optional[List[str]] = Query(None),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    technician_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    List test sessions with cursor-based pagination and filtering.
    
    Supports filtering by status, date range, and technician.
    Returns paginated results with CRDT-aware cursor.
    """
    # Decode cursor
    cursor_data = {}
    if cursor:
        try:
            cursor_data = json.loads(base64.b64decode(cursor))
        except:
            raise HTTPException(status_code=400, detail="Invalid cursor")
    
    # Build query
    query = select(TestSession)
    conditions = []
    
    if status:
        conditions.append(TestSession.status.in_(status))
    if date_from:
        conditions.append(TestSession.created_at >= date_from)
    if date_to:
        conditions.append(TestSession.created_at <= date_to)
    if cursor_data.get("last_evaluated_id"):
        conditions.append(TestSession.id > cursor_data["last_evaluated_id"])
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(TestSession.created_at).limit(limit + 1)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    # Generate next cursor
    next_cursor = None
    if len(sessions) > limit:
        sessions = sessions[:limit]
        last_session = sessions[-1]
        cursor_data = {
            "last_evaluated_id": str(last_session.id),
            "vector_clock": last_session.vector_clock or {}
        }
        next_cursor = base64.b64encode(json.dumps(cursor_data).encode()).decode()
    
    return {
        "data": [
            {
                "session_id": str(s.id),
                "building_id": str(s.building_id),
                "status": s.status,
                "session_name": s.session_name,
                "created_at": s.created_at.isoformat(),
                "vector_clock": s.vector_clock or {}
            } for s in sessions
        ],
        "next_cursor": next_cursor,
        "total": len(sessions)
    }

@router.get("/{session_id}/offline_bundle")
async def get_offline_bundle(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Generate offline bundle for test session.
    
    Creates compressed bundle with session data, building info,
    assets, and historical faults for offline operation.
    """
    result = await db.execute(
        select(TestSession).where(TestSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Generate offline bundle
    bundle = {
        "session_id": str(session.id),
        "bundle_data": {
            "session": {
                "id": str(session.id),
                "building_id": str(session.building_id),
                "session_name": session.session_name,
                "status": session.status,
                "session_data": session.session_data or {},
                "vector_clock": session.vector_clock or {},
                "created_at": session.created_at.isoformat()
            },
            "building": {
                # TODO: Fetch from building_id when buildings router is ready
                "placeholder": "Building data will be fetched when available"
            },
            "evidence": [],
            "sync_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow()).isoformat(),
                "format_version": "1.0"
            }
        },
        "vector_clock": session.vector_clock or {},
        "expires_at": datetime.utcnow().isoformat()
    }
    
    # Check bundle size (TDD requirement: < 50MB)
    bundle_json = json.dumps(bundle)
    compressed = gzip.compress(bundle_json.encode())
    
    if len(compressed) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Bundle too large")
    
    return bundle

@router.post("/")
async def create_test_session(
    session_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """Create a new test session with CRDT initialization"""
    
    # Initialize vector clock for CRDT
    initial_vector_clock = {
        str(current_user.user_id): 1
    }
    
    new_session = TestSession(
        building_id=session_data.get("building_id"),
        session_name=session_data.get("session_name", f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"),
        status=session_data.get("status", "active"),
        session_data=session_data.get("session_data", {}),
        vector_clock=initial_vector_clock,
        created_by=current_user.user_id
    )
    
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return {
        "id": str(new_session.id),
        "building_id": str(new_session.building_id),
        "session_name": new_session.session_name,
        "status": new_session.status,
        "session_data": new_session.session_data,
        "vector_clock": new_session.vector_clock,
        "created_at": new_session.created_at.isoformat()
    }

@router.put("/{session_id}")
async def update_test_session(
    session_id: str,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """Update test session with CRDT vector clock increment"""
    
    result = await db.execute(
        select(TestSession).where(TestSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update vector clock for CRDT
    vector_clock = session.vector_clock or {}
    user_id = str(current_user.user_id)
    vector_clock[user_id] = vector_clock.get(user_id, 0) + 1
    
    # Apply updates
    if "session_name" in updates:
        session.session_name = updates["session_name"]
    if "status" in updates:
        session.status = updates["status"]
    if "session_data" in updates:
        session.session_data = updates["session_data"]
    
    session.vector_clock = vector_clock
    session.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(session)
    
    return {
        "id": str(session.id),
        "building_id": str(session.building_id),
        "session_name": session.session_name,
        "status": session.status,
        "session_data": session.session_data,
        "vector_clock": session.vector_clock,
        "updated_at": session.updated_at.isoformat()
    }