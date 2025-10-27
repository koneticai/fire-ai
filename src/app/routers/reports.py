"""
Reports API Router for FireMode Compliance Platform
Handles report generation, trend analysis, and download endpoints
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from ..database.core import get_db
from ..dependencies import get_current_active_user
from ..schemas.auth import TokenPayload
from ..services.report_generator_v2 import ReportGeneratorV2
from ..services.trend_analyzer import TrendAnalyzer
from ..services.storage.worm_uploader import WormStorageUploader
from ..models import Building, CETestReport
from ..models.audit_log import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/reports", tags=["reports"])


class ReportGenerationRequest(BaseModel):
    """Request model for report generation"""
    building_id: UUID = Field(..., description="Building ID to generate report for")
    years_back: int = Field(3, ge=1, le=10, description="Number of years to analyze (1-10)")
    include_trends: bool = Field(True, description="Include trend analysis in report")
    include_charts: bool = Field(True, description="Include charts in report")
    report_type: str = Field("compliance", description="Type of report to generate")


class ReportGenerationResponse(BaseModel):
    """Response model for report generation"""
    report_id: UUID = Field(..., description="Generated report ID")
    building_id: UUID = Field(..., description="Building ID")
    report_type: str = Field(..., description="Type of report generated")
    generated_at: datetime = Field(..., description="When the report was generated")
    file_size_bytes: int = Field(..., description="Size of the generated report")
    download_url: str = Field(..., description="URL to download the report")


class TrendAnalysisRequest(BaseModel):
    """Request model for trend analysis"""
    building_id: UUID = Field(..., description="Building ID to analyze")
    years_back: int = Field(3, ge=1, le=10, description="Number of years to analyze")
    analysis_types: List[str] = Field(
        default=["pressure_differential", "air_velocity", "door_force", "defects"],
        description="Types of analysis to perform"
    )


class TrendAnalysisResponse(BaseModel):
    """Response model for trend analysis"""
    building_id: UUID = Field(..., description="Building ID")
    analysis_period_years: int = Field(..., description="Analysis period in years")
    analysis_date: datetime = Field(..., description="When analysis was performed")
    building_health_score: float = Field(..., description="Overall building health score (0-100)")
    critical_issues: List[Dict[str, Any]] = Field(..., description="Critical issues found")
    recommendations: List[str] = Field(..., description="Maintenance recommendations")
    trend_data: Dict[str, Any] = Field(..., description="Detailed trend analysis data")


class ReportFinalizeRequest(BaseModel):
    """Request model for report finalization with engineer sign-off"""
    engineer_signature: str = Field(..., description="Base64-encoded engineer signature")
    compliance_statement: str = Field(..., description="AS 1851-2012 compliance statement")
    engineer_license: str = Field(..., description="Engineer license number")
    
    class Config:
        json_schema_extra = {
            "example": {
                "engineer_signature": "data:image/png;base64,iVBORw0KGgo...",
                "compliance_statement": "This report complies with AS 1851-2012 fire safety requirements",
                "engineer_license": "ENG-12345"
            }
        }


class ReportFinalizeResponse(BaseModel):
    """Response model for report finalization"""
    report_id: UUID = Field(..., description="Finalized report ID")
    finalized: bool = Field(..., description="Finalization status")
    worm_storage_uri: str = Field(..., description="S3 URI with WORM protection")
    retention_until: str = Field(..., description="Retention end date (ISO 8601)")
    finalized_at: str = Field(..., description="Finalization timestamp (ISO 8601)")
    finalized_by: UUID = Field(..., description="Engineer user ID")
    engineer_license: str = Field(..., description="Engineer license number")


@router.post("/generate", response_model=ReportGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: ReportGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Generate a comprehensive compliance report for a building
    
    Creates a PDF report with 3-year trends, charts, and compliance analysis.
    """
    logger.info(f"Generating report for building {request.building_id} by user {current_user.user_id}")
    
    try:
        # Verify building exists
        from sqlalchemy import select
        building_query = select(Building).where(Building.id == request.building_id)
        building_result = await db.execute(building_query)
        building = building_result.scalar_one_or_none()
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {request.building_id} not found"
            )
        
        # Generate report
        report_generator = ReportGeneratorV2(db)
        report_bytes = await report_generator.generate_compliance_report(
            building_id=request.building_id,
            years_back=request.years_back,
            include_trends=request.include_trends,
            include_charts=request.include_charts
        )
        
        # Store report metadata in database
        report_id = UUID("550e8400-e29b-41d4-a716-446655440000")  # Generate actual UUID
        
        # Create report record
        report_data = {
            "report_type": request.report_type,
            "building_id": request.building_id,
            "generated_by": current_user.user_id,
            "report_metadata": {
                "years_back": request.years_back,
                "include_trends": request.include_trends,
                "include_charts": request.include_charts,
                "file_size_bytes": len(report_bytes)
            }
        }
        
        # In a real implementation, you would:
        # 1. Store the PDF bytes in cloud storage (S3, etc.)
        # 2. Save report metadata to database
        # 3. Generate a signed download URL
        
        return ReportGenerationResponse(
            report_id=report_id,
            building_id=request.building_id,
            report_type=request.report_type,
            generated_at=datetime.now(),
            file_size_bytes=len(report_bytes),
            download_url=f"/v1/reports/{report_id}/download"
        )
        
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Download a generated report
    
    Returns the PDF report file for download.
    """
    logger.info(f"Downloading report {report_id} by user {current_user.user_id}")
    
    try:
        # In a real implementation, you would:
        # 1. Look up the report in the database
        # 2. Retrieve the PDF from cloud storage
        # 3. Return the file as a streaming response
        
        # For now, return a placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Report download not yet implemented - requires cloud storage integration"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report {report_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download report: {str(e)}"
        )


@router.post("/trends", response_model=TrendAnalysisResponse)
async def analyze_trends(
    request: TrendAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Perform trend analysis on building data
    
    Analyzes trends in pressure differentials, air velocities, door forces, and defects
    over the specified time period.
    """
    logger.info(f"Analyzing trends for building {request.building_id} by user {current_user.user_id}")
    
    try:
        # Verify building exists
        from sqlalchemy import select
        building_query = select(Building).where(Building.id == request.building_id)
        building_result = await db.execute(building_query)
        building = building_result.scalar_one_or_none()
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {request.building_id} not found"
            )
        
        # Perform trend analysis
        trend_analyzer = TrendAnalyzer(db)
        trend_summary = await trend_analyzer.get_building_trend_summary(
            building_id=request.building_id,
            years_back=request.years_back
        )
        
        return TrendAnalysisResponse(
            building_id=request.building_id,
            analysis_period_years=request.years_back,
            analysis_date=datetime.now(),
            building_health_score=trend_summary.get("building_health_score", 0.0),
            critical_issues=trend_summary.get("critical_issues", []),
            recommendations=trend_summary.get("recommendations", []),
            trend_data=trend_summary
        )
        
    except Exception as e:
        logger.error(f"Failed to analyze trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze trends: {str(e)}"
        )


@router.get("/trends/{building_id}")
async def get_building_trends(
    building_id: UUID,
    years_back: int = Query(3, ge=1, le=10, description="Number of years to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get trend analysis for a specific building
    
    Returns trend analysis data for the specified building and time period.
    """
    logger.info(f"Getting trends for building {building_id} by user {current_user.user_id}")
    
    try:
        # Verify building exists
        from sqlalchemy import select
        building_query = select(Building).where(Building.id == building_id)
        building_result = await db.execute(building_query)
        building = building_result.scalar_one_or_none()
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {building_id} not found"
            )
        
        # Perform trend analysis
        trend_analyzer = TrendAnalyzer(db)
        trend_summary = await trend_analyzer.get_building_trend_summary(
            building_id=building_id,
            years_back=years_back
        )
        
        return trend_summary
        
    except Exception as e:
        logger.error(f"Failed to get trends for building {building_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trends: {str(e)}"
        )


@router.get("/trends/{building_id}/pressure-differentials")
async def get_pressure_differential_trends(
    building_id: UUID,
    years_back: int = Query(3, ge=1, le=10, description="Number of years to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get pressure differential trends for a building
    
    Returns detailed pressure differential trend analysis.
    """
    logger.info(f"Getting pressure differential trends for building {building_id}")
    
    try:
        # Verify building exists
        from sqlalchemy import select
        building_query = select(Building).where(Building.id == building_id)
        building_result = await db.execute(building_query)
        building = building_result.scalar_one_or_none()
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {building_id} not found"
            )
        
        # Get pressure differential trends
        trend_analyzer = TrendAnalyzer(db)
        trends = await trend_analyzer.analyze_pressure_differential_trends(
            building_id=building_id,
            years_back=years_back
        )
        
        return {
            "building_id": str(building_id),
            "analysis_period_years": years_back,
            "analysis_date": datetime.now().isoformat(),
            "pressure_differential_trends": trends
        }
        
    except Exception as e:
        logger.error(f"Failed to get pressure differential trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pressure differential trends: {str(e)}"
        )


@router.get("/trends/{building_id}/air-velocities")
async def get_air_velocity_trends(
    building_id: UUID,
    years_back: int = Query(3, ge=1, le=10, description="Number of years to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get air velocity trends for a building
    
    Returns detailed air velocity trend analysis.
    """
    logger.info(f"Getting air velocity trends for building {building_id}")
    
    try:
        # Verify building exists
        from sqlalchemy import select
        building_query = select(Building).where(Building.id == building_id)
        building_result = await db.execute(building_query)
        building = building_result.scalar_one_or_none()
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {building_id} not found"
            )
        
        # Get air velocity trends
        trend_analyzer = TrendAnalyzer(db)
        trends = await trend_analyzer.analyze_air_velocity_trends(
            building_id=building_id,
            years_back=years_back
        )
        
        return {
            "building_id": str(building_id),
            "analysis_period_years": years_back,
            "analysis_date": datetime.now().isoformat(),
            "air_velocity_trends": trends
        }
        
    except Exception as e:
        logger.error(f"Failed to get air velocity trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get air velocity trends: {str(e)}"
        )


@router.get("/trends/{building_id}/door-forces")
async def get_door_force_trends(
    building_id: UUID,
    years_back: int = Query(3, ge=1, le=10, description="Number of years to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get door force trends for a building
    
    Returns detailed door force trend analysis.
    """
    logger.info(f"Getting door force trends for building {building_id}")
    
    try:
        # Verify building exists
        from sqlalchemy import select
        building_query = select(Building).where(Building.id == building_id)
        building_result = await db.execute(building_query)
        building = building_result.scalar_one_or_none()
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {building_id} not found"
            )
        
        # Get door force trends
        trend_analyzer = TrendAnalyzer(db)
        trends = await trend_analyzer.analyze_door_force_trends(
            building_id=building_id,
            years_back=years_back
        )
        
        return {
            "building_id": str(building_id),
            "analysis_period_years": years_back,
            "analysis_date": datetime.now().isoformat(),
            "door_force_trends": trends
        }
        
    except Exception as e:
        logger.error(f"Failed to get door force trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get door force trends: {str(e)}"
        )


@router.get("/trends/{building_id}/defects")
async def get_defect_trends(
    building_id: UUID,
    years_back: int = Query(3, ge=1, le=10, description="Number of years to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get defect trends for a building
    
    Returns detailed defect trend analysis.
    """
    logger.info(f"Getting defect trends for building {building_id}")
    
    try:
        # Verify building exists
        from sqlalchemy import select
        building_query = select(Building).where(Building.id == building_id)
        building_result = await db.execute(building_query)
        building = building_result.scalar_one_or_none()
        
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {building_id} not found"
            )
        
        # Get defect trends
        trend_analyzer = TrendAnalyzer(db)
        trends = await trend_analyzer.analyze_defect_trends(
            building_id=building_id,
            years_back=years_back
        )
        
        return {
            "building_id": str(building_id),
            "analysis_period_years": years_back,
            "analysis_date": datetime.now().isoformat(),
            "defect_trends": trends
        }
        
    except Exception as e:
        logger.error(f"Failed to get defect trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get defect trends: {str(e)}"
        )


@router.post("/{report_id}/finalize", response_model=ReportFinalizeResponse)
async def finalize_report(
    report_id: UUID,
    finalize_data: ReportFinalizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Finalize report with engineer sign-off and WORM storage.
    
    Process:
    1. Validate engineer role
    2. Generate PDF with signature
    3. Upload to WORM storage (7-year retention)
    4. Mark report as finalized (immutable)
    5. Create audit log
    
    References:
    - AS 1851-2012: Engineer sign-off requirements
    - data_model.md: audit_log pattern
    """
    logger.info(f"Finalizing report {report_id} by user {current_user.user_id}")
    
    # Engineer role validation - RBAC check
    roles = getattr(current_user, "roles", [])
    if "engineer" not in roles:
        logger.warning(
            f"Non-engineer user {current_user.username} (roles: {roles}) "
            f"attempted to finalize report {report_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "FIRE-403",
                "message": "Engineer role required for report finalization"
            }
        )
    
    try:
        # Get report
        result = await db.execute(
            select(CETestReport).where(CETestReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        # Check if already finalized
        if report.finalized:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "FIRE-409",
                    "message": "Report already finalized",
                    "finalized_at": report.finalized_at.isoformat() if report.finalized_at else None,
                    "finalized_by": str(report.finalized_by) if report.finalized_by else None
                }
            )
        
        # Generate PDF with signature (placeholder implementation)
        pdf_content = await generate_report_pdf_with_signature(
            report=report,
            signature=finalize_data.engineer_signature,
            compliance_statement=finalize_data.compliance_statement,
            engineer_license=finalize_data.engineer_license
        )
        
        # Upload to WORM storage
        worm_bucket = os.getenv('WORM_REPORTS_BUCKET', 'firemode-reports-worm')
        worm_uploader = WormStorageUploader(bucket_name=worm_bucket, retention_years=7)
        
        # Generate S3 key
        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        s3_key = f"reports/{timestamp}/{report.test_session_id}/{report_id}_final.pdf"
        
        # Upload with WORM protection
        s3_uri = worm_uploader.upload_from_memory(
            data=pdf_content,
            s3_key=s3_key,
            metadata={
                "report_id": str(report_id),
                "test_session_id": str(report.test_session_id),
                "engineer": current_user.username,
                "engineer_license": finalize_data.engineer_license,
                "finalized_at": datetime.now(timezone.utc).isoformat()
            },
            content_type="application/pdf"
        )
        
        # Verify immutability
        immutability_check = worm_uploader.verify_immutability(s3_key)
        if not immutability_check.get('is_immutable', False):
            logger.error(f"WORM verification failed for report {report_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify WORM protection"
            )
        
        # Calculate retention date
        retention_date = datetime.now(timezone.utc) + timedelta(days=365 * 7)
        
        # Update report record
        old_values = {
            "finalized": report.finalized,
            "finalized_at": report.finalized_at.isoformat() if report.finalized_at else None
        }
        
        report.finalized = True
        report.finalized_at = datetime.now(timezone.utc)
        report.finalized_by = current_user.user_id
        report.engineer_signature_s3_uri = s3_uri
        report.engineer_license_number = finalize_data.engineer_license
        report.compliance_statement = finalize_data.compliance_statement
        
        await db.commit()
        await db.refresh(report)
        
        # Create audit log per data_model.md
        audit_entry = AuditLog(
            user_id=current_user.user_id,
            action="FINALIZE_REPORT_WORM",
            resource_type="ce_test_report",
            resource_id=report_id,
            old_values=old_values,
            new_values={
                "finalized": True,
                "finalized_at": report.finalized_at.isoformat(),
                "finalized_by": str(current_user.user_id),
                "worm_storage_uri": s3_uri,
                "retention_until": retention_date.isoformat(),
                "engineer_license": finalize_data.engineer_license,
                "immutability_verified": True
            }
        )
        db.add(audit_entry)
        await db.commit()
        
        logger.info(f"Report {report_id} finalized successfully by engineer {current_user.username}")
        
        return ReportFinalizeResponse(
            report_id=report_id,
            finalized=True,
            worm_storage_uri=s3_uri,
            retention_until=retention_date.isoformat(),
            finalized_at=report.finalized_at.isoformat(),
            finalized_by=current_user.user_id,
            engineer_license=finalize_data.engineer_license
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report finalization failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report finalization failed: {str(e)}"
        )


async def generate_report_pdf_with_signature(
    report: CETestReport,
    signature: str,
    compliance_statement: str,
    engineer_license: str
) -> bytes:
    """
    Generate PDF report with engineer signature.
    
    Placeholder implementation - generates mock PDF.
    
    TODO: Implement full PDF generation with:
    - Report content from report.report_data
    - Baseline comparison charts
    - C&E test results
    - Engineer signature image
    - Compliance statement
    - AS 1851-2012 compliance markers
    """
    # Mock PDF content for now
    pdf_header = b"%PDF-1.4\n"
    pdf_content = f"""
    Report ID: {report.id}
    Test Session: {report.test_session_id}
    Report Type: {report.report_type}
    
    Engineer License: {engineer_license}
    Compliance Statement: {compliance_statement}
    
    Signature: [Engineer signature would be embedded here]
    
    AS 1851-2012 Compliance Report
    Generated: {datetime.now(timezone.utc).isoformat()}
    """
    
    return pdf_header + pdf_content.encode('utf-8')


@router.get("/health-check")
async def health_check():
    """
    Health check endpoint for the reports service
    
    Returns service status and available features.
    """
    return {
        "service": "reports",
        "status": "healthy",
        "version": "2.0.0",
        "features": [
            "compliance_report_generation",
            "trend_analysis",
            "chart_generation",
            "pdf_export",
            "report_finalization_worm"
        ],
        "timestamp": datetime.now().isoformat()
    }
