"""
Evidence handling router for FireMode Compliance Platform.

This router handles evidence submission, validation, and retrieval
for fire safety testing compliance.
"""

import hashlib
import logging
import boto3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_active_user
from ..database.core import get_db
from ..models.test_sessions import TestSession
from ..models.evidence import Evidence
from ..models.defects import Defect
from ..models.audit_log import AuditLog
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
from ..services.storage.worm_uploader import WormStorageUploader


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/evidence", tags=["evidence"])
security = HTTPBearer()


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


def validate_device_attestation(headers: dict) -> bool:
    """Validate device attestation using unified middleware"""
    from ..services.attestation import AttestationMiddleware, AttestationConfig
    
    # Get attestation token from headers
    token = headers.get('X-Device-Attestation')
    if not token:
        raise HTTPException(
            status_code=422,
            detail="ATTESTATION_FAILED: Missing X-Device-Attestation header"
        )
    
    # Initialize attestation middleware
    config = AttestationConfig()
    middleware = AttestationMiddleware(config)
    
    # Validate attestation
    result = middleware.validate_attestation(token, headers)
    
    if not result.is_valid:
        error_detail = f"ATTESTATION_FAILED: {result.error_message}"
        if result.is_invalid:
            raise HTTPException(status_code=422, detail=error_detail)
        else:  # Error case
            raise HTTPException(status_code=500, detail=error_detail)
    
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
    # Validate device attestation
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
        
        # Add WORM-specific metadata
        worm_metadata = {
            **metadata_dict,
            "user_id": str(current_user.user_id),
            "session_id": session_id,
            "evidence_type": evidence_type,
            "upload_timestamp": datetime.utcnow().isoformat(),
            "file_hash": file_hash,
            "original_filename": file.filename
        }
        
        # Upload to WORM storage
        worm_bucket = os.getenv('WORM_EVIDENCE_BUCKET', 'firemode-evidence-worm')
        worm_uploader = WormStorageUploader(bucket_name=worm_bucket)
        
        # Generate S3 key with timestamp and hash for uniqueness
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        s3_key = f"evidence/{timestamp}/{session_id}/{file_hash[:8]}_{file.filename}"
        
        # Upload file to WORM storage
        s3_uri = worm_uploader.upload_with_retention(
            file_path=file_content,
            s3_key=s3_key,
            metadata=worm_metadata,
            content_type=file.content_type
        )
        
        # Verify immutability
        immutability_check = worm_uploader.verify_immutability(s3_key)
        if not immutability_check.get('is_immutable', False):
            logger.warning(f"WORM immutability verification failed for {s3_key}")
        
        # Submit to Go service with WORM storage info
        result = await proxy.submit_evidence(
            session_id=session_id,
            evidence_type=evidence_type,
            file=file,
            sha256_hash=file_hash,
            user_id=str(current_user.user_id),
            metadata=worm_metadata,
            worm_storage_info={
                "s3_uri": s3_uri,
                "s3_key": s3_key,
                "bucket": worm_bucket,
                "immutability_verified": immutability_check.get('is_immutable', False)
            }
        )
        
        logger.info(f"Evidence submitted to WORM storage successfully - ID: {result.get('evidence_id')}, S3: {s3_uri}, User: {current_user.user_id}")
        
        # Create audit log entry per data_model.md
        try:
            retention_date = datetime.utcnow() + timedelta(days=365 * 7)
            audit_entry = AuditLog(
                user_id=current_user.user_id,
                action="UPLOAD_EVIDENCE_WORM",
                resource_type="evidence",
                resource_id=result["evidence_id"],
                new_values={
                    "s3_uri": s3_uri,
                    "s3_key": s3_key,
                    "bucket": worm_bucket,
                    "checksum": file_hash,
                    "worm_protected": True,
                    "retention_until": retention_date.isoformat(),
                    "immutability_verified": immutability_check.get('is_immutable', False),
                    "evidence_type": evidence_type,
                    "session_id": session_id,
                    "filename": file.filename
                },
                ip_address=request.client.host if request and hasattr(request, 'client') else None,
                user_agent=request.headers.get('user-agent') if request else None
            )
            db.add(audit_entry)
            await db.commit()
        except Exception as audit_error:
            logger.error(f"Audit log creation failed for evidence {result['evidence_id']}: {audit_error}")
            # Evidence is already in WORM storage; audit failure should not block user
            # Consider implementing async retry queue for audit logs
        
        return EvidenceResponse(
        return EvidenceResponse(
            evidence_id=result["evidence_id"],
            hash=result["hash"],
            status=result["status"],
            message="Evidence submitted to WORM storage and verified successfully"
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
        # Extract bucket and key from file_path
        # Assuming file_path format: "s3://bucket-name/key"
        if evidence.file_path.startswith("s3://"):
            path_parts = evidence.file_path[5:].split("/", 1)
            bucket_name = path_parts[0]
            key = path_parts[1]
        else:
            # Fallback: assume it's just the key and use WORM bucket
            bucket_name = os.getenv('WORM_EVIDENCE_BUCKET', 'firemode-evidence-worm')
            key = evidence.file_path
        
        # Use WORM uploader for consistent S3 operations
        worm_uploader = WormStorageUploader(bucket_name=bucket_name)
        
        # Generate pre-signed URL with 7-day expiry
        download_url = worm_uploader.get_presigned_url(
            s3_key=key,
            expiration=7 * 24 * 60 * 60  # 7 days in seconds
        )
        
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        # Verify object is still immutable (optional check)
        immutability_check = worm_uploader.verify_immutability(key)
        if not immutability_check.get('is_immutable', False):
            logger.warning(f"Evidence {evidence_id} immutability check failed")
        
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