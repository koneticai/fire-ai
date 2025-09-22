"""
Test results router for FireMode Compliance Platform.

This router handles test result submission and CRDT processing
for fire safety testing compliance.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..dependencies import get_current_active_user
from ..schemas.auth import TokenPayload
from ..proxy import get_go_service_proxy, GoServiceProxy


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tests", tags=["test_results"])


class TestResultSubmission(BaseModel):
    """Request model for test result submission."""
    session_id: str
    results: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class TestResultResponse(BaseModel):
    """Response model for test result submission."""
    session_id: str
    status: str
    message: str
    processed_at: Optional[str] = None


@router.post("/sessions/{session_id}/results", response_model=TestResultResponse)
async def submit_test_results(
    session_id: str,
    results_data: TestResultSubmission,
    current_user: TokenPayload = Depends(get_current_active_user),
    proxy: GoServiceProxy = Depends(get_go_service_proxy)
):
    """
    Submit test results for CRDT processing.
    
    This endpoint handles test result submission and processes them
    through the Go service for optimal CRDT operations.
    """
    # Validate that session_id matches request body
    if results_data.session_id != session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID in URL must match session ID in request body"
        )
    
    try:
        # Submit results to Go service
        result = await proxy.submit_test_results(
            session_id=session_id,
            results=results_data.results,
            user_id=str(current_user.user_id)
        )
        
        logger.info(f"Test results submitted successfully - Session: {session_id}, User: {current_user.user_id}")
        
        return TestResultResponse(
            session_id=session_id,
            status=result.get("status", "processed"),
            message=result.get("message", "Test results processed successfully"),
            processed_at=result.get("processed_at")
        )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions from proxy (includes 503 for service unavailable)
        if e.status_code == 503:
            logger.error(f"Go service unavailable for session {session_id}")
        raise
    except Exception as e:
        logger.error(f"Test results submission failed for session {session_id}, user {current_user.user_id}: {e}")
        # Map connection errors to service unavailable
        if "connection" in str(e).lower() or "timeout" in str(e).lower():
            raise HTTPException(status_code=503, detail="Go service unavailable")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during test results processing"
        )


@router.get("/sessions/{session_id}/results")
async def get_test_results(
    session_id: str,
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get test results for a specific session.
    
    This endpoint retrieves processed test results and CRDT state
    for a given test session.
    """
    # TODO: Implement test results retrieval from database
    # This would typically query the database for test results
    # associated with the session_id
    
    # For now, return a placeholder response
    return {
        "session_id": session_id,
        "results": {},
        "crdt_state": {},
        "message": "Test results retrieval not yet implemented"
    }


@router.get("/sessions/{session_id}/status")
async def get_session_status(
    session_id: str,
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get the status of a test session.
    
    This endpoint provides information about the current state
    of a test session including completion status and result summary.
    """
    # TODO: Implement session status retrieval from database
    # This would typically query the database for session status
    # and aggregate result information
    
    # For now, return a placeholder response
    return {
        "session_id": session_id,
        "status": "unknown",
        "completion_percentage": 0,
        "total_tests": 0,
        "completed_tests": 0,
        "message": "Session status retrieval not yet implemented"
    }