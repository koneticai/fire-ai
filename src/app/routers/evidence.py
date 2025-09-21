"""
Evidence handling router for FireMode Compliance Platform.

This router handles evidence submission, validation, and retrieval
for fire safety testing compliance.
"""

import hashlib
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_active_user
from ..database.core import get_db
from ..models.test_sessions import TestSession
from ..schemas.token import TokenData
from ..proxy import get_go_service_proxy, GoServiceProxy


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/evidence", tags=["evidence"])
security = HTTPBearer()


class EvidenceMetadata(BaseModel):
    """Metadata for evidence submission."""
    test_type: Optional[str] = None
    location: Optional[str] = None
    inspector: Optional[str] = None
    equipment_id: Optional[str] = None
    additional_notes: Optional[str] = None


class EvidenceResponse(BaseModel):
    """Response model for evidence submission."""
    evidence_id: str
    hash: str
    status: str
    message: Optional[str] = None


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


@router.post("/submit", response_model=EvidenceResponse)
async def submit_evidence(
    session_id: str = Form(..., description="Test session ID"),
    evidence_type: str = Form(..., description="Type of evidence (photo, video, document, etc.)"),
    file: UploadFile = File(..., description="Evidence file to upload"),
    metadata: Optional[str] = Form(None, description="Additional metadata as JSON string"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user),
    proxy: GoServiceProxy = Depends(get_go_service_proxy)
):
    """
    Submit evidence for a test session with hash verification.
    
    This endpoint handles file uploads with integrity verification
    and forwards the request to the Go service for processing.
    """
    # Verify session ownership before allowing evidence submission
    result = await db.execute(
        select(TestSession).where(
            and_(TestSession.id == session_id, TestSession.created_by == current_user.user_id)
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Read file content for hash calculation
    file_content = await file.read()
    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="File cannot be empty")
    
    # Calculate hash
    file_hash = calculate_file_hash(file_content)
    
    # Reset file position for proxy
    file.file.seek(0)
    
    try:
        # Parse metadata if provided
        metadata_dict = {}
        if metadata:
            import json
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in metadata field")
        
        # Submit to Go service
        result = await proxy.submit_evidence(
            session_id=session_id,
            evidence_type=evidence_type,
            file=file,
            sha256_hash=file_hash,
            user_id=str(current_user.user_id),
            metadata=metadata_dict
        )
        
        logger.info(f"Evidence submitted successfully - ID: {result.get('evidence_id')}, User: {current_user.user_id}")
        
        return EvidenceResponse(
            evidence_id=result["evidence_id"],
            hash=result["hash"],
            status=result["status"],
            message="Evidence submitted and verified successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions from proxy
        raise
    except Exception as e:
        logger.error(f"Evidence submission failed for user {current_user.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during evidence submission")


@router.get("/session/{session_id}")
async def get_session_evidence(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Get all evidence for a specific test session.
    
    This endpoint retrieves evidence metadata and file references
    for a given test session that the user owns.
    """
    # Verify session ownership before retrieving evidence
    result = await db.execute(
        select(TestSession).where(
            and_(TestSession.id == session_id, TestSession.created_by == current_user.user_id)
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # TODO: Query evidence table once it's implemented
    # For now, return basic session info with empty evidence list
    return {
        "session_id": session_id,
        "evidence": [],
        "message": "Evidence retrieval from database not yet implemented"
    }


@router.get("/verify/{evidence_id}")
async def verify_evidence(
    evidence_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Verify the integrity of stored evidence.
    
    This endpoint checks that evidence files haven't been tampered with
    by comparing stored and calculated hashes.
    """
    # TODO: Implement evidence verification
    # This would typically:
    # 1. Retrieve evidence record from database (with ownership check)
    # 2. Read the actual file
    # 3. Calculate current hash
    # 4. Compare with stored hash
    
    return {
        "evidence_id": evidence_id,
        "verified": False,
        "message": "Evidence verification not yet implemented - requires evidence database table"
    }