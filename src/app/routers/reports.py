"""
Reports API Router for FireMode Compliance Platform
Handles report generation, trend analysis, and download endpoints
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..database.core import get_db
from ..dependencies import get_current_active_user
from ..schemas.auth import TokenPayload
from ..services.report_generator_v2 import ReportGeneratorV2
from ..services.trend_analyzer import TrendAnalyzer
from ..models import Building, CETestReport

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
            "pdf_export"
        ],
        "timestamp": datetime.now().isoformat()
    }
