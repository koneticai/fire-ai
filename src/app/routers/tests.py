"""
Test sessions router for FireMode Compliance Platform
Handles CRUD operations for test sessions with cursor-based pagination
"""

import base64
import json
from typing import Optional
from uuid import UUID

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from ..models import (
    TestSession, TestSessionCreate, TestSessionListParams, 
    TestSessionListResponse, CRDTChangesRequest
)
from ..dependencies import get_current_active_user, get_database_connection, TokenData

# Import automerge for CRDT operations
try:
    from automerge.core import Document, ROOT, ObjType, ScalarType
    AUTOMERGE_AVAILABLE = True
except ImportError:
    AUTOMERGE_AVAILABLE = False

router = APIRouter()

def apply_crdt_changes(doc_bytes: bytes, changes: list) -> bytes:
    """Apply CRDT changes using automerge library"""
    if not AUTOMERGE_AVAILABLE:
        # Fallback implementation - simple JSON merge
        if doc_bytes:
            doc = json.loads(doc_bytes.decode())
        else:
            doc = {}
        
        for change in changes:
            if change.get("operation") == "set":
                path = change.get("path", [])
                value = change.get("value")
                
                current = doc
                for key in path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                if path:
                    current[path[-1]] = value
        
        return json.dumps(doc).encode()
    
    # Use automerge for proper CRDT operations
    try:
        doc = Document()
        if doc_bytes:
            # Load existing document
            doc = Document.load(doc_bytes)
        
        with doc.transaction() as tx:
            for change in changes:
                operation = change.get("operation")
                path = change.get("path", [])
                value = change.get("value")
                
                if operation == "set" and path:
                    # Navigate to the correct position and set value
                    current_obj = ROOT
                    for key in path[:-1]:
                        # Create nested objects as needed
                        try:
                            current_obj = tx.get(current_obj, key)
                        except:
                            current_obj = tx.put_object(current_obj, key, ObjType.Map)
                    
                    # Set the final value
                    if isinstance(value, str):
                        tx.put(current_obj, path[-1], ScalarType.Str, value)
                    elif isinstance(value, (int, float)):
                        tx.put(current_obj, path[-1], ScalarType.F64, value)
                    elif isinstance(value, bool):
                        tx.put(current_obj, path[-1], ScalarType.Boolean, value)
        
        return doc.save()
    
    except Exception as e:
        # Fallback to simple merge if automerge fails
        return apply_crdt_changes(doc_bytes, changes)

@router.get("/sessions", response_model=TestSessionListResponse)
async def list_test_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """List test sessions with cursor-based pagination using vector_clock"""
    
    try:
        cursor_condition = ""
        params = [limit]
        
        if cursor:
            try:
                # Decode base64 cursor to get vector_clock
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                cursor_condition = "AND vector_clock::text > %s"
                params.append(json.dumps(cursor_data))
            except (ValueError, json.JSONDecodeError):
                raise HTTPException(status_code=400, detail="Invalid cursor format")
        
        with conn.cursor() as db_cursor:
            query = f"""
                SELECT id, building_id, session_name, status, vector_clock, 
                       session_data, created_by, created_at, updated_at
                FROM test_sessions 
                WHERE 1=1 {cursor_condition}
                ORDER BY vector_clock::text
                LIMIT %s
            """
            
            db_cursor.execute(query, params)
            rows = db_cursor.fetchall()
            
            sessions = []
            next_cursor = None
            
            for row in rows:
                session = TestSession(
                    id=row[0],
                    building_id=row[1],
                    session_name=row[2],
                    status=row[3],
                    vector_clock=row[4] or {},
                    session_data=row[5] or {},
                    created_by=row[6],
                    created_at=row[7],
                    updated_at=row[8]
                )
                sessions.append(session)
            
            # Generate next cursor if we have more results
            has_more = len(sessions) == limit
            if has_more and sessions:
                last_session = sessions[-1]
                next_cursor = base64.b64encode(
                    json.dumps(last_session.vector_clock).encode()
                ).decode()
        
        conn.close()
        
        return TestSessionListResponse(
            sessions=sessions,
            next_cursor=next_cursor,
            has_more=has_more
        )
        
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list test sessions: {str(e)}"
        )

@router.post("/sessions", response_model=TestSession)
async def create_test_session(
    session_data: TestSessionCreate,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Create a new test session"""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO test_sessions 
                (building_id, session_name, status, session_data, created_by, vector_clock)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, created_at, updated_at
            """, (
                session_data.building_id,
                session_data.session_name,
                session_data.status,
                json.dumps(session_data.session_data),
                current_user.user_id,
                json.dumps({"created": 1, "actor": current_user.user_id})
            ))
            
            result = cursor.fetchone()
            session_id, created_at, updated_at = result
            
            conn.commit()
        
        conn.close()
        
        return TestSession(
            id=session_id,
            building_id=session_data.building_id,
            session_name=session_data.session_name,
            status=session_data.status,
            vector_clock={"created": 1, "actor": current_user.user_id},
            session_data=session_data.session_data,
            created_by=current_user.user_id,
            created_at=created_at,
            updated_at=updated_at
        )
        
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create test session: {str(e)}"
        )

@router.get("/sessions/{session_id}", response_model=TestSession)
async def get_test_session(
    session_id: UUID,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Get a specific test session by ID"""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, building_id, session_name, status, vector_clock,
                       session_data, created_by, created_at, updated_at
                FROM test_sessions 
                WHERE id = %s
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Test session not found")
            
            session = TestSession(
                id=row[0],
                building_id=row[1],
                session_name=row[2],
                status=row[3],
                vector_clock=row[4] or {},
                session_data=row[5] or {},
                created_by=row[6],
                created_at=row[7],
                updated_at=row[8]
            )
        
        conn.close()
        return session
        
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get test session: {str(e)}"
        )

@router.post("/sessions/{session_id}/crdt-changes")
async def apply_session_changes(
    session_id: UUID,
    changes_request: CRDTChangesRequest,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Apply CRDT changes to a test session (stub implementation)"""
    
    try:
        with conn.cursor() as cursor:
            # Get current vector_clock
            cursor.execute(
                "SELECT vector_clock FROM test_sessions WHERE id = %s",
                (session_id,)
            )
            
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Test session not found")
            
            current_vector_clock = result[0] or {}
            
            # Apply CRDT changes (simplified implementation)
            doc_bytes = json.dumps(current_vector_clock).encode()
            change_data = [
                {
                    "operation": change.operation,
                    "path": change.path,
                    "value": change.value
                }
                for change in changes_request.changes
            ]
            
            updated_doc_bytes = apply_crdt_changes(doc_bytes, change_data)
            updated_vector_clock = json.loads(updated_doc_bytes.decode())
            
            # Update the session
            cursor.execute("""
                UPDATE test_sessions 
                SET vector_clock = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (json.dumps(updated_vector_clock), session_id))
            
            conn.commit()
        
        conn.close()
        
        return JSONResponse(
            content={
                "status": "changes_applied",
                "session_id": str(session_id),
                "changes_count": len(changes_request.changes)
            }
        )
        
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply CRDT changes: {str(e)}"
        )