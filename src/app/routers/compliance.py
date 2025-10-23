"""
Compliance verification endpoints for WORM storage.

Provides endpoints for verifying AS 1851-2012 compliance,
generating audit reports, and creating compliance certificates.
"""

import logging
import io
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_active_user
from ..database.core import get_db
from ..schemas.token import TokenData
from ..services.compliance.worm_verifier import WormComplianceVerifier, ComplianceReport, ComplianceCheck

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])

# Pydantic models for request/response
class EvidenceComplianceResponse(BaseModel):
    """Response model for evidence compliance verification."""
    evidence_id: str
    session_id: str
    evidence_type: str
    created_at: str
    file_path: Optional[str]
    hash: str
    object_lock_verification: Optional[Dict[str, Any]]
    compliant: bool
    verified_at: str
    error: Optional[str] = None

class AuditReportRequest(BaseModel):
    """Request model for audit report generation."""
    start_date: datetime = Field(..., description="Start date for audit period")
    end_date: datetime = Field(..., description="End date for audit period")
    include_evidence_details: bool = Field(False, description="Include detailed evidence information")

class AuditReportResponse(BaseModel):
    """Response model for audit report."""
    report_id: str
    generated_at: str
    evidence_count: int
    overall_compliance: bool
    summary: str
    checks: List[Dict[str, Any]]

class ComplianceCertificateRequest(BaseModel):
    """Request model for compliance certificate generation."""
    evidence_ids: List[str] = Field(..., description="List of evidence IDs to include in certificate")
    include_audit_summary: bool = Field(False, description="Include audit summary in certificate")

class ComplianceCertificateResponse(BaseModel):
    """Response model for compliance certificate."""
    certificate_id: str
    evidence_count: int
    generated_at: str
    valid_until: str
    download_url: Optional[str] = None

class BucketComplianceResponse(BaseModel):
    """Response model for bucket compliance verification."""
    bucket_name: str
    object_lock_enabled: bool
    encryption_enabled: bool
    versioning_enabled: bool
    public_access_blocked: bool
    compliance_status: str
    verified_at: str
    error: Optional[str] = None

@router.get("/verify/{evidence_id}", response_model=EvidenceComplianceResponse)
async def verify_evidence_compliance(
    evidence_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Verify WORM compliance for a specific evidence file.
    
    This endpoint checks if an evidence file is properly stored in WORM-compliant
    storage with Object Lock enabled and correct retention settings.
    """
    try:
        verifier = WormComplianceVerifier()
        result = verifier.verify_evidence_compliance(evidence_id)
        
        if not result.get('compliant', False) and 'error' not in result:
            logger.warning(f"Evidence {evidence_id} compliance check failed for user {current_user.user_id}")
        
        return EvidenceComplianceResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to verify evidence compliance for {evidence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify evidence compliance")

@router.post("/audit", response_model=AuditReportResponse)
async def generate_audit_report(
    request: AuditReportRequest,
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Generate comprehensive audit report for WORM compliance.
    
    This endpoint creates a detailed audit report covering all evidence files
    in the specified date range, verifying WORM storage compliance.
    """
    try:
        # Validate date range
        if request.end_date <= request.start_date:
            raise HTTPException(status_code=400, detail="End date must be after start date")
        
        # Limit audit period to 1 year maximum
        max_period = timedelta(days=365)
        if request.end_date - request.start_date > max_period:
            raise HTTPException(
                status_code=400, 
                detail="Audit period cannot exceed 1 year"
            )
        
        verifier = WormComplianceVerifier()
        report = verifier.create_audit_report(request.start_date, request.end_date)
        
        # Convert ComplianceCheck objects to dictionaries
        checks_data = []
        for check in report.checks:
            checks_data.append({
                "check_name": check.check_name,
                "passed": check.passed,
                "details": check.details,
                "timestamp": check.timestamp.isoformat(),
                "severity": check.severity
            })
        
        logger.info(f"Generated audit report {report.report_id} for user {current_user.user_id}")
        
        return AuditReportResponse(
            report_id=report.report_id,
            generated_at=report.generated_at.isoformat(),
            evidence_count=report.evidence_count,
            overall_compliance=report.overall_compliance,
            summary=report.summary,
            checks=checks_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate audit report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audit report")

@router.post("/certificate", response_model=ComplianceCertificateResponse)
async def generate_compliance_certificate(
    request: ComplianceCertificateRequest,
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Generate compliance certificate for evidence files.
    
    This endpoint creates a digitally signed PDF certificate confirming
    that the specified evidence files are stored in WORM-compliant storage.
    """
    try:
        # Validate evidence IDs
        if not request.evidence_ids:
            raise HTTPException(status_code=400, detail="At least one evidence ID is required")
        
        if len(request.evidence_ids) > 1000:
            raise HTTPException(status_code=400, detail="Maximum 1000 evidence IDs allowed per certificate")
        
        verifier = WormComplianceVerifier()
        
        # Generate certificate
        pdf_bytes = verifier.generate_compliance_certificate(request.evidence_ids)
        
        # Generate certificate ID
        certificate_id = f"CERT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Store certificate in WORM storage (optional)
        # This would typically be stored in the reports WORM bucket
        # For now, we'll return the PDF directly
        
        logger.info(f"Generated compliance certificate {certificate_id} for {len(request.evidence_ids)} evidence files")
        
        return ComplianceCertificateResponse(
            certificate_id=certificate_id,
            evidence_count=len(request.evidence_ids),
            generated_at=datetime.utcnow().isoformat(),
            valid_until=(datetime.utcnow() + timedelta(days=365)).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate compliance certificate: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate compliance certificate")

@router.get("/certificate/{certificate_id}/download")
async def download_compliance_certificate(
    certificate_id: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Download compliance certificate PDF.
    
    This endpoint provides the actual PDF certificate file for download.
    Note: In a production system, certificates would be stored in WORM storage
    and accessed via presigned URLs.
    """
    try:
        # For demo purposes, we'll generate a new certificate
        # In production, this would retrieve from WORM storage
        
        # Extract evidence IDs from certificate ID (this is a simplified approach)
        # In production, you'd store the mapping in the database
        
        # For now, return a placeholder response
        raise HTTPException(
            status_code=501, 
            detail="Certificate download not yet implemented. Use /certificate endpoint to generate new certificates."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download certificate {certificate_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download certificate")

@router.get("/certificate/{certificate_id}/pdf")
async def get_compliance_certificate_pdf(
    certificate_id: str,
    evidence_ids: List[str] = Query(..., description="Evidence IDs to include in certificate"),
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Get compliance certificate as PDF stream.
    
    This endpoint returns the compliance certificate as a PDF file stream.
    """
    try:
        if not evidence_ids:
            raise HTTPException(status_code=400, detail="Evidence IDs are required")
        
        verifier = WormComplianceVerifier()
        pdf_bytes = verifier.generate_compliance_certificate(evidence_ids)
        
        # Return PDF as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=compliance_certificate_{certificate_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate PDF certificate {certificate_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF certificate")

@router.get("/bucket/verify", response_model=List[BucketComplianceResponse])
async def verify_bucket_compliance(
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Verify WORM bucket compliance configuration.
    
    This endpoint checks if the WORM storage buckets are properly configured
    with Object Lock, encryption, versioning, and access controls.
    """
    try:
        verifier = WormComplianceVerifier()
        
        # Check evidence bucket
        evidence_result = verifier.check_bucket_compliance()
        
        # Check reports bucket
        reports_verifier = WormComplianceVerifier(
            evidence_bucket=None,
            reports_bucket=verifier.reports_bucket
        )
        reports_result = reports_verifier.check_bucket_compliance()
        
        results = []
        
        # Evidence bucket result
        results.append(BucketComplianceResponse(
            bucket_name=evidence_result.get('bucket_name', 'unknown'),
            object_lock_enabled=evidence_result.get('object_lock_enabled', False),
            encryption_enabled=evidence_result.get('encryption_enabled', False),
            versioning_enabled=evidence_result.get('versioning_enabled', False),
            public_access_blocked=evidence_result.get('public_access_blocked', False),
            compliance_status=evidence_result.get('compliance_status', 'ERROR'),
            verified_at=datetime.utcnow().isoformat(),
            error=evidence_result.get('error')
        ))
        
        # Reports bucket result
        results.append(BucketComplianceResponse(
            bucket_name=reports_result.get('bucket_name', 'unknown'),
            object_lock_enabled=reports_result.get('object_lock_enabled', False),
            encryption_enabled=reports_result.get('encryption_enabled', False),
            versioning_enabled=reports_result.get('versioning_enabled', False),
            public_access_blocked=reports_result.get('public_access_blocked', False),
            compliance_status=reports_result.get('compliance_status', 'ERROR'),
            verified_at=datetime.utcnow().isoformat(),
            error=reports_result.get('error')
        ))
        
        logger.info(f"Bucket compliance verification completed for user {current_user.user_id}")
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to verify bucket compliance: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify bucket compliance")

@router.get("/status")
async def get_compliance_status(
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Get overall WORM compliance status.
    
    This endpoint provides a high-level overview of the system's
    WORM compliance status and any issues that need attention.
    """
    try:
        verifier = WormComplianceVerifier()
        
        # Quick compliance check
        evidence_bucket_check = verifier.check_bucket_compliance()
        
        # Get recent evidence count (last 30 days)
        from ..database.core import get_db
        db = next(get_db())
        
        recent_evidence_count = 0
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM evidence
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                """)
                result = cursor.fetchone()
                recent_evidence_count = result['count'] if result else 0
        except Exception as e:
            logger.warning(f"Failed to get recent evidence count: {e}")
        
        # Determine overall status
        overall_status = "HEALTHY"
        issues = []
        
        if evidence_bucket_check.get('compliance_status') != 'COMPLIANT':
            overall_status = "DEGRADED"
            issues.append("Evidence bucket compliance issues")
        
        if recent_evidence_count == 0:
            issues.append("No recent evidence submissions")
        
        status_response = {
            "overall_status": overall_status,
            "evidence_bucket_status": evidence_bucket_check.get('compliance_status', 'UNKNOWN'),
            "recent_evidence_count": recent_evidence_count,
            "issues": issues,
            "last_checked": datetime.utcnow().isoformat(),
            "compliance_standard": "AS 1851-2012",
            "retention_period_years": 7
        }
        
        logger.info(f"Compliance status check completed for user {current_user.user_id}: {overall_status}")
        
        return status_response
        
    except Exception as e:
        logger.error(f"Failed to get compliance status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get compliance status")
