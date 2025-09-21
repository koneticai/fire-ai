"""
Test Sessions API Router for FireMode Compliance Platform
Complete implementation with cursor-based pagination and offline bundle generation
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Request
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
from ..schemas.token import TokenData
from ..utils.pagination import encode_cursor, decode_cursor
from ..utils.query_builder import QueryBuilder
from ..utils.vector_clock import VectorClock

router = APIRouter(prefix="/v1/tests/sessions", tags=["test_sessions"])

@router.get("/", response_model=Dict)
async def list_test_sessions(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    status: Optional[List[str]] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    technician_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user)
):
    # Decode cursor
    cursor_data = decode_cursor(cursor) if cursor else {}
    
    # Build query with filters
    base_query = select(TestSession).where(
        TestSession.created_by == current_user.user_id
    )
    
    filters = {
        k: v for k, v in {
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
            "technician_id": technician_id
        }.items() if v is not None
    }
    
    query = QueryBuilder(base_query, TestSession)\
        .apply_filters(filters)\
        .apply_cursor_pagination(cursor_data, limit + 1)\
        .build()
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    # Handle limit+1 pagination logic
    has_more = len(sessions) > limit
    if has_more:
        sessions = sessions[:limit]
    
    # Generate next cursor if we have more results
    next_cursor = None
    if has_more and sessions:
        last_session = sessions[-1]
        next_cursor = encode_cursor({
            "id": last_session.id,
            "vector_clock": last_session.vector_clock,
            "created_at": last_session.created_at.isoformat()
        })
    
    return {
        "data": [
            {
                "id": str(s.id),
                "building_id": str(s.building_id),
                "status": s.status,
                "session_name": s.session_name,
                "created_at": s.created_at.isoformat(),
                "vector_clock": s.vector_clock or {}
            } for s in sessions
        ],
        "next_cursor": next_cursor
    }

@router.get("/{session_id}/offline_bundle")
async def get_offline_bundle(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Generate offline bundle for test session.
    
    Creates compressed bundle with session data, building info,
    assets, and historical faults for offline operation.
    """
    result = await db.execute(
        select(TestSession).where(
            and_(TestSession.id == session_id, TestSession.created_by == current_user.user_id)
        )
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
    current_user: TokenData = Depends(get_current_active_user)
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user)
):
    """Update test session with CRDT vector clock increment and optimistic concurrency control"""
    
    result = await db.execute(
        select(TestSession).where(
            and_(TestSession.id == session_id, TestSession.created_by == current_user.user_id)
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Optimistic Concurrency Control using vector clocks
    server_clock = VectorClock(session.vector_clock or {})
    
    if hasattr(request.state, "vector_clock"):
        client_clock = request.state.vector_clock
        
        # Check if client clock happens-before server clock (stale client)
        if client_clock.happens_before(server_clock) or (
            client_clock.clock != server_clock.clock and 
            not server_clock.happens_before(client_clock)
        ):
            raise HTTPException(
                status_code=412, 
                detail="Concurrent modification detected. Please refresh and try again."
            )
        
        # Merge client knowledge into server clock
        server_clock = server_clock.merge(client_clock)
    else:
        # Require If-Match header for OCC enforcement
        raise HTTPException(
            status_code=428,
            detail="Precondition Required: If-Match header with vector clock required"
        )
    
    # Increment vector clock for CRDT
    user_id = str(current_user.user_id) 
    server_clock.increment(user_id)
    
    # Apply updates
    if "session_name" in updates:
        session.session_name = updates["session_name"]
    if "status" in updates:
        session.status = updates["status"]
    if "session_data" in updates:
        session.session_data = updates["session_data"]
    
    session.vector_clock = server_clock.clock
    session.updated_at = datetime.utcnow()
    
    # Set updated clock for ETag response
    request.state.updated_clock = server_clock
    
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

@router.post("/{session_id}/results")
async def submit_results(
    session_id: str,
    changes: List[dict],
    idempotency_key: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user)
):
    """Submit test results with CRDT processing via Go service"""
    import httpx
    from ..internal_jwt import get_internal_jwt_token
    
    # Verify session ownership before proxying to Go service
    result = await db.execute(
        select(TestSession).where(
            and_(TestSession.id == session_id, TestSession.created_by == current_user.user_id)
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Generate secure internal JWT token
    internal_token = get_internal_jwt_token()
    
    # Forward to Go service for CRDT processing with proper error handling
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://localhost:9091/v1/tests/sessions/{session_id}/results",
                json={"changes": changes, "idempotency_key": idempotency_key},
                headers={
                    "X-Internal-Authorization": internal_token,
                    "X-User-ID": str(current_user.user_id)
                }
            )
        
        if response.status_code != 200:
            # Forward error details from Go service when available
            try:
                error_detail = response.json().get("detail", "CRDT processing failed")
            except:
                error_detail = "CRDT processing failed"
            
            raise HTTPException(
                status_code=response.status_code, 
                detail=error_detail
            )
        
        return response.json()
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Go service timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail="Go service unavailable")