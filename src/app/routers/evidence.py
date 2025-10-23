"""
Evidence handling router for FireMode Compliance Platform.

This router handles evidence submission, validation, and retrieval
for fire safety testing compliance.
"""

import hashlib
import logging
import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_active_user
from ..database.core import get_db
from ..models.test_sessions import TestSession
from ..models.evidence import Evidence
from ..models.defects import Defect
from ..schemas.token import TokenData
from ..schemas.auth import TokenPayload
from ..schemas.evidence import (
    EvidenceRead,
    EvidenceDownloadResponse,
    EvidenceFlagRequest,
    EvidenceFlagResponse,
    EvidenceLinkDefectRequest,
    EvidenceResponse
)
from ..proxy import get_go_service_proxy, GoServiceProxy


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/evidence", tags=["evidence"])
security = HTTPBearer()


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


def validate_device_attestation(headers: dict) -> bool:
    """MVP stub - Week 4 will add DeviceCheck integration"""
    token = headers.get('X-Device-Attestation')
    if not token or token == 'emulator':
        raise HTTPException(
            status_code=422,
            detail="ATTESTATION_FAILED: Emulator not allowed"
        )
    return True


@router.post("/submit", response_model=EvidenceResponse)
async def submit_evidence(
    session_id: str = Form(..., description="Test session ID"),
    evidence_type: str = Form(..., description="Type of evidence (photo, video, document, etc.)"),
    file: UploadFile = File(..., description="Evidence file to upload"),
    metadata: Optional[str] = Form(None, description="Additional metadata as JSON string"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user),
    proxy: GoServiceProxy = Depends(get_go_service_proxy)
):
    """
    Submit evidence for a test session with hash verification.
    
    This endpoint handles file uploads with integrity verification
    and forwards the request to the Go service for processing.
    """
    # Validate device attestation (MVP stub)
    if request:
        validate_device_attestation(request.headers)
    
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


@router.get("/{evidence_id}", response_model=EvidenceRead)
async def get_evidence_metadata(
    evidence_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get evidence metadata by ID.
    
    Returns evidence metadata (NOT file content) including:
    - id, filename, file_type, file_size, hash
    - device_attestation_status, uploaded_at, flagged_for_review
    
    Requires JWT authentication and ownership check.
    """
    # Get evidence with ownership check through test session
    result = await db.execute(
        select(Evidence)
        .join(TestSession, Evidence.session_id == TestSession.id)
        .where(
            and_(
                Evidence.id == evidence_id,
                TestSession.created_by == current_user.user_id
            )
        )
    )
    evidence = result.scalar_one_or_none()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Extract metadata for response
    metadata = evidence.evidence_metadata or {}
    
    return EvidenceRead(
        id=evidence.id,
        session_id=evidence.session_id,
        evidence_type=evidence.evidence_type,
        filename=metadata.get("filename"),
        file_type=metadata.get("file_type"),
        file_size=metadata.get("file_size"),
        hash=evidence.checksum,
        device_attestation_status=metadata.get("device_attestation_status"),
        uploaded_at=evidence.created_at,
        flagged_for_review=evidence.flagged_for_review,
        evidence_metadata=metadata
    )


@router.get("/{evidence_id}/download", response_model=EvidenceDownloadResponse)
async def get_evidence_download_url(
    evidence_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get pre-signed S3 URL for downloading evidence file.
    
    Returns a pre-signed S3 URL with 7-day expiry.
    Requires JWT authentication and ownership check.
    """
    # Get evidence with ownership check through test session
    result = await db.execute(
        select(Evidence)
        .join(TestSession, Evidence.session_id == TestSession.id)
        .where(
            and_(
                Evidence.id == evidence_id,
                TestSession.created_by == current_user.user_id
            )
        )
    )
    evidence = result.scalar_one_or_none()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    if not evidence.file_path:
        raise HTTPException(status_code=404, detail="Evidence file not found")
    
    try:
        # Initialize S3 client (assuming AWS credentials are configured)
        s3_client = boto3.client('s3')
        
        # Extract bucket and key from file_path
        # Assuming file_path format: "s3://bucket-name/key"
        if evidence.file_path.startswith("s3://"):
            path_parts = evidence.file_path[5:].split("/", 1)
            bucket_name = path_parts[0]
            key = path_parts[1]
        else:
            # Fallback: assume it's just the key and use default bucket
            bucket_name = "firemode-evidence"  # Default bucket name
            key = evidence.file_path
        
        # Generate pre-signed URL with 7-day expiry
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=7 * 24 * 60 * 60  # 7 days in seconds
        )
        
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        logger.info(f"Generated download URL for evidence {evidence_id} for user {current_user.user_id}")
        
        return EvidenceDownloadResponse(
            download_url=download_url,
            expires_at=expires_at
        )
        
    except Exception as e:
        logger.error(f"Failed to generate download URL for evidence {evidence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate download URL")


@router.patch("/{evidence_id}/flag", response_model=EvidenceFlagResponse)
async def flag_evidence_for_review(
    evidence_id: UUID,
    flag_request: EvidenceFlagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Flag evidence for review (soft-delete).
    
    This is an admin-only endpoint that flags evidence for review.
    Sets flagged_for_review=true, flagged_at=now(), flagged_by=user_id.
    """
    # For now, we'll implement a simple admin check based on username
    # In a real system, you'd have proper role-based access control
    if not current_user.username.endswith("_admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    
    # Get evidence
    result = await db.execute(
        select(Evidence).where(Evidence.id == evidence_id)
    )
    evidence = result.scalar_one_or_none()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Update evidence with flag information
    evidence.flagged_for_review = True
    evidence.flag_reason = flag_request.flag_reason
    evidence.flagged_at = datetime.utcnow()
    evidence.flagged_by = current_user.user_id
    
    await db.commit()
    await db.refresh(evidence)
    
    logger.info(f"Evidence {evidence_id} flagged for review by admin {current_user.user_id}")
    
    return EvidenceFlagResponse(
        id=evidence.id,
        flagged_for_review=evidence.flagged_for_review,
        flag_reason=evidence.flag_reason,
        flagged_at=evidence.flagged_at,
        flagged_by=evidence.flagged_by
    )


@router.post("/{evidence_id}/link-defect")
async def link_evidence_to_defect(
    evidence_id: UUID,
    link_request: EvidenceLinkDefectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Link evidence to a defect.
    
    Updates defect.evidence_ids array by appending evidence_id.
    Validates that defect exists and user owns both evidence and defect.
    """
    # Verify evidence exists and user owns it through test session
    evidence_result = await db.execute(
        select(Evidence)
        .join(TestSession, Evidence.session_id == TestSession.id)
        .where(
            and_(
                Evidence.id == evidence_id,
                TestSession.created_by == current_user.user_id
            )
        )
    )
    evidence = evidence_result.scalar_one_or_none()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Verify defect exists and user owns it through test session
    defect_result = await db.execute(
        select(Defect)
        .join(TestSession, Defect.test_session_id == TestSession.id)
        .where(
            and_(
                Defect.id == link_request.defect_id,
                TestSession.created_by == current_user.user_id
            )
        )
    )
    defect = defect_result.scalar_one_or_none()
    
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    
    # Update defect's evidence_ids array
    if defect.evidence_ids is None:
        defect.evidence_ids = []
    
    if evidence_id not in defect.evidence_ids:
        defect.evidence_ids.append(evidence_id)
        await db.commit()
        await db.refresh(defect)
        
        logger.info(f"Linked evidence {evidence_id} to defect {defect.id} by user {current_user.user_id}")
        
        return {
            "defect_id": defect.id,
            "evidence_id": evidence_id,
            "evidence_ids": defect.evidence_ids,
            "message": "Evidence successfully linked to defect"
        }
    else:
        return {
            "defect_id": defect.id,
            "evidence_id": evidence_id,
            "evidence_ids": defect.evidence_ids,
            "message": "Evidence already linked to defect"
        }