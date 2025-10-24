"""
Report Generator v2 for FireMode Compliance Platform
Enhanced PDF reports with 3-year trends, charts, and C&E integration
"""

import io
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import base64

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import selectinload

from ..models import (
    Building, 
    CETestSession, 
    CETestMeasurement, 
    CETestDeviation,
    CETestReport,
    BaselinePressureDifferential,
    BaselineAirVelocity,
    BaselineDoorForce,
    Defect,
    TestSession,
    Evidence
)
from .trend_analyzer import TrendAnalyzer, TrendAnalysisResult

logger = logging.getLogger(__name__)


class ReportData:
    """Container for report data"""
    
    def __init__(self):
        self.building: Optional[Building] = None
        self.test_sessions: List[TestSession] = []
        self.ce_test_sessions: List[CETestSession] = []
        self.baseline_data: Dict[str, Any] = {}
        self.trend_analysis: Dict[str, Any] = {}
        self.defects: List[Defect] = []
        self.evidence: List[Evidence] = []
        self.compliance_score: float = 0.0
        self.report_metadata: Dict[str, Any] = {}


class ReportGeneratorV2:
    """
    Enhanced report generator with 3-year trends and analytics
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.trend_analyzer = TrendAnalyzer(db)
    
    async def generate_compliance_report(
        self, 
        building_id: UUID, 
        years_back: int = 3,
        include_trends: bool = True,
        include_charts: bool = True
    ) -> bytes:
        """
        Generate comprehensive compliance report with trends and charts
        
        Args:
            building_id: Building to generate report for
            years_back: Number of years to include in trends
            include_trends: Whether to include trend analysis
            include_charts: Whether to include charts
            
        Returns:
            PDF report as bytes
        """
        logger.info(f"Generating compliance report for building {building_id}")
        
        # Gather all report data
        report_data = await self._gather_report_data(building_id, years_back, include_trends)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build report content
        story = []
        
        # Title page
        story.extend(self._build_title_page(report_data))
        story.append(PageBreak())
        
        # Executive summary
        story.extend(self._build_executive_summary(report_data))
        story.append(PageBreak())
        
        # Building information
        story.extend(self._build_building_info(report_data))
        story.append(Spacer(1, 12))
        
        # Compliance overview
        story.extend(self._build_compliance_overview(report_data))
        story.append(PageBreak())
        
        # Trend analysis section
        if include_trends and report_data.trend_analysis:
            story.extend(self._build_trend_analysis_section(report_data))
            story.append(PageBreak())
        
        # C&E test results
        if report_data.ce_test_sessions:
            story.extend(self._build_ce_test_results(report_data))
            story.append(PageBreak())
        
        # Baseline measurements
        story.extend(self._build_baseline_measurements(report_data))
        story.append(Spacer(1, 12))
        
        # Defects and issues
        story.extend(self._build_defects_section(report_data))
        story.append(PageBreak())
        
        # Charts section
        if include_charts:
            story.extend(await self._build_charts_section(report_data))
            story.append(PageBreak())
        
        # Calibration verification
        story.extend(self._build_calibration_verification(report_data))
        story.append(Spacer(1, 12))
        
        # Engineer compliance statement
        story.extend(self._build_engineer_statement(report_data))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    async def _gather_report_data(
        self, 
        building_id: UUID, 
        years_back: int, 
        include_trends: bool
    ) -> ReportData:
        """Gather all data needed for the report"""
        
        data = ReportData()
        
        # Get building information
        building_query = select(Building).where(Building.id == building_id)
        building_result = await self.db.execute(building_query)
        data.building = building_result.scalar_one_or_none()
        
        if not data.building:
            raise ValueError(f"Building {building_id} not found")
        
        # Get test sessions
        cutoff_date = datetime.now() - timedelta(days=years_back * 365)
        test_sessions_query = select(TestSession).where(
            and_(
                TestSession.building_id == building_id,
                TestSession.created_at >= cutoff_date
            )
        ).order_by(TestSession.created_at.desc())
        
        test_sessions_result = await self.db.execute(test_sessions_query)
        data.test_sessions = test_sessions_result.scalars().all()
        
        # Get C&E test sessions
        ce_sessions_query = select(CETestSession).where(
            and_(
                CETestSession.building_id == building_id,
                CETestSession.created_at >= cutoff_date
            )
        ).options(
            selectinload(CETestSession.measurements),
            selectinload(CETestSession.deviations),
            selectinload(CETestSession.reports)
        ).order_by(CETestSession.created_at.desc())
        
        ce_sessions_result = await self.db.execute(ce_sessions_query)
        data.ce_test_sessions = ce_sessions_result.scalars().all()
        
        # Get baseline data
        data.baseline_data = await self._get_baseline_data(building_id)
        
        # Get defects
        defects_query = select(Defect).where(
            and_(
                Defect.building_id == building_id,
                Defect.discovered_at >= cutoff_date
            )
        ).order_by(Defect.discovered_at.desc())
        
        defects_result = await self.db.execute(defects_query)
        data.defects = defects_result.scalars().all()
        
        # Get evidence
        evidence_query = select(Evidence).join(TestSession).where(
            and_(
                TestSession.building_id == building_id,
                Evidence.created_at >= cutoff_date
            )
        ).order_by(Evidence.created_at.desc())
        
        evidence_result = await self.db.execute(evidence_query)
        data.evidence = evidence_result.scalars().all()
        
        # Calculate compliance score
        data.compliance_score = await self._calculate_compliance_score(building_id, data.defects)
        
        # Get trend analysis
        if include_trends:
            data.trend_analysis = await self.trend_analyzer.get_building_trend_summary(
                building_id, years_back
            )
        
        # Report metadata
        data.report_metadata = {
            "generated_at": datetime.now(),
            "years_analyzed": years_back,
            "total_test_sessions": len(data.test_sessions),
            "total_ce_sessions": len(data.ce_test_sessions),
            "total_defects": len(data.defects),
            "compliance_score": data.compliance_score
        }
        
        return data
    
    async def _get_baseline_data(self, building_id: UUID) -> Dict[str, Any]:
        """Get baseline measurement data"""
        
        baseline_data = {
            "pressure_differentials": [],
            "air_velocities": [],
            "door_forces": []
        }
        
        # Get pressure differentials
        pressure_query = select(BaselinePressureDifferential).where(
            BaselinePressureDifferential.building_id == building_id
        )
        pressure_result = await self.db.execute(pressure_query)
        baseline_data["pressure_differentials"] = pressure_result.scalars().all()
        
        # Get air velocities
        velocity_query = select(BaselineAirVelocity).where(
            BaselineAirVelocity.building_id == building_id
        )
        velocity_result = await self.db.execute(velocity_query)
        baseline_data["air_velocities"] = velocity_result.scalars().all()
        
        # Get door forces
        force_query = select(BaselineDoorForce).where(
            BaselineDoorForce.building_id == building_id
        )
        force_result = await self.db.execute(force_query)
        baseline_data["door_forces"] = force_result.scalars().all()
        
        return baseline_data
    
    async def _calculate_compliance_score(
        self, 
        building_id: UUID, 
        defects: List[Defect]
    ) -> float:
        """Calculate overall compliance score (0-100)"""
        
        if not defects:
            return 100.0
        
        # Weight defects by severity
        severity_weights = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1
        }
        
        total_penalty = 0
        for defect in defects:
            if defect.status not in ["closed", "verified"]:
                weight = severity_weights.get(defect.severity, 1)
                total_penalty += weight
        
        # Calculate score (penalty reduces score)
        score = max(0, 100 - (total_penalty * 2))
        return round(score, 1)
    
    def _build_title_page(self, data: ReportData) -> List:
        """Build title page content"""
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        content = []
        
        # Title
        content.append(Paragraph("Fire Safety Compliance Report", title_style))
        content.append(Spacer(1, 20))
        
        # Building name
        content.append(Paragraph(f"Building: {data.building.name}", subtitle_style))
        content.append(Paragraph(f"Address: {data.building.address}", styles['Normal']))
        content.append(Spacer(1, 20))
        
        # Report metadata
        content.append(Paragraph("Report Information", styles['Heading2']))
        content.append(Paragraph(f"Generated: {data.report_metadata['generated_at'].strftime('%B %d, %Y')}", styles['Normal']))
        content.append(Paragraph(f"Analysis Period: {data.report_metadata['years_analyzed']} years", styles['Normal']))
        content.append(Paragraph(f"Compliance Score: {data.compliance_score}%", styles['Normal']))
        
        return content
    
    def _build_executive_summary(self, data: ReportData) -> List:
        """Build executive summary section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Executive Summary", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        # Overall compliance status
        if data.compliance_score >= 90:
            status = "EXCELLENT"
            status_color = colors.green
        elif data.compliance_score >= 75:
            status = "GOOD"
            status_color = colors.orange
        elif data.compliance_score >= 60:
            status = "FAIR"
            status_color = colors.red
        else:
            status = "POOR"
            status_color = colors.darkred
        
        status_style = ParagraphStyle(
            'StatusStyle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=status_color,
            alignment=TA_CENTER
        )
        
        content.append(Paragraph(f"Overall Compliance Status: {status}", status_style))
        content.append(Spacer(1, 12))
        
        # Key metrics
        metrics_data = [
            ["Metric", "Value"],
            ["Compliance Score", f"{data.compliance_score}%"],
            ["Test Sessions (3 years)", str(data.report_metadata['total_test_sessions'])],
            ["C&E Test Sessions", str(data.report_metadata['total_ce_sessions'])],
            ["Open Defects", str(len([d for d in data.defects if d.status not in ['closed', 'verified']]))],
            ["Critical Issues", str(len([d for d in data.defects if d.severity == 'critical' and d.status not in ['closed', 'verified']]))]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(metrics_table)
        content.append(Spacer(1, 12))
        
        # Key findings
        content.append(Paragraph("Key Findings", styles['Heading2']))
        
        findings = []
        
        # Compliance score findings
        if data.compliance_score >= 90:
            findings.append("✓ Excellent compliance performance with minimal issues")
        elif data.compliance_score >= 75:
            findings.append("✓ Good compliance performance with minor issues requiring attention")
        elif data.compliance_score >= 60:
            findings.append("⚠ Fair compliance performance with several issues requiring immediate attention")
        else:
            findings.append("⚠ Poor compliance performance with critical issues requiring urgent attention")
        
        # Trend analysis findings
        if data.trend_analysis and data.trend_analysis.get('critical_issues'):
            critical_count = len(data.trend_analysis['critical_issues'])
            findings.append(f"⚠ {critical_count} critical trends detected requiring immediate attention")
        
        # Defect findings
        open_defects = [d for d in data.defects if d.status not in ['closed', 'verified']]
        if open_defects:
            critical_defects = [d for d in open_defects if d.severity == 'critical']
            if critical_defects:
                findings.append(f"⚠ {len(critical_defects)} critical defects require immediate resolution")
            else:
                findings.append(f"• {len(open_defects)} open defects require resolution")
        else:
            findings.append("✓ No open defects - all issues have been resolved")
        
        for finding in findings:
            content.append(Paragraph(finding, styles['Normal']))
        
        return content
    
    def _build_building_info(self, data: ReportData) -> List:
        """Build building information section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Building Information", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        building_info_data = [
            ["Property", "Value"],
            ["Building Name", data.building.name],
            ["Address", data.building.address],
            ["Building Type", data.building.building_type],
            ["Compliance Status", data.building.compliance_status or "Not Set"],
            ["Created", data.building.created_at.strftime('%B %d, %Y')],
            ["Last Updated", data.building.updated_at.strftime('%B %d, %Y')]
        ]
        
        building_table = Table(building_info_data, colWidths=[2*inch, 4*inch])
        building_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(building_table)
        
        return content
    
    def _build_compliance_overview(self, data: ReportData) -> List:
        """Build compliance overview section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Compliance Overview", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        # Compliance score breakdown
        content.append(Paragraph("Compliance Score Breakdown", styles['Heading2']))
        
        # Calculate score components
        total_defects = len(data.defects)
        open_defects = len([d for d in data.defects if d.status not in ['closed', 'verified']])
        critical_defects = len([d for d in data.defects if d.severity == 'critical' and d.status not in ['closed', 'verified']])
        
        score_breakdown_data = [
            ["Component", "Count", "Impact"],
            ["Total Defects (3 years)", str(total_defects), "Historical"],
            ["Open Defects", str(open_defects), "Current"],
            ["Critical Defects", str(critical_defects), "Immediate"],
            ["Test Sessions", str(data.report_metadata['total_test_sessions']), "Positive"],
            ["C&E Test Sessions", str(data.report_metadata['total_ce_sessions']), "Positive"]
        ]
        
        score_table = Table(score_breakdown_data, colWidths=[2.5*inch, 1*inch, 1.5*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(score_table)
        
        return content
    
    def _build_trend_analysis_section(self, data: ReportData) -> List:
        """Build trend analysis section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Trend Analysis", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        if not data.trend_analysis:
            content.append(Paragraph("No trend analysis data available.", styles['Normal']))
            return content
        
        # Building health score
        health_score = data.trend_analysis.get('building_health_score', 0)
        content.append(Paragraph(f"Building Health Score: {health_score:.1f}/100", styles['Heading2']))
        content.append(Spacer(1, 12))
        
        # Critical issues
        critical_issues = data.trend_analysis.get('critical_issues', [])
        if critical_issues:
            content.append(Paragraph("Critical Issues Requiring Immediate Attention", styles['Heading2']))
            
            for issue in critical_issues:
                content.append(Paragraph(f"• {issue['type'].replace('_', ' ').title()}: {issue['location']}", styles['Normal']))
                content.append(Paragraph(f"  Trend: {issue['trend_direction']}, Confidence: {issue['confidence']:.1%}", styles['Normal']))
                if issue.get('predicted_failure_date'):
                    content.append(Paragraph(f"  Predicted Failure: {issue['predicted_failure_date']}", styles['Normal']))
                content.append(Spacer(1, 6))
        else:
            content.append(Paragraph("No critical trends detected.", styles['Normal']))
        
        # Recommendations
        recommendations = data.trend_analysis.get('recommendations', [])
        if recommendations:
            content.append(Paragraph("Maintenance Recommendations", styles['Heading2']))
            for rec in recommendations:
                content.append(Paragraph(f"• {rec}", styles['Normal']))
        
        return content
    
    def _build_ce_test_results(self, data: ReportData) -> List:
        """Build C&E test results section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("C&E Test Results", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        if not data.ce_test_sessions:
            content.append(Paragraph("No C&E test sessions found in the analysis period.", styles['Normal']))
            return content
        
        # Summary table
        summary_data = [["Session", "Date", "Type", "Status", "Score", "Deviations"]]
        
        for session in data.ce_test_sessions[:10]:  # Limit to 10 most recent
            summary_data.append([
                session.session_name[:30] + "..." if len(session.session_name) > 30 else session.session_name,
                session.created_at.strftime('%Y-%m-%d'),
                session.test_type,
                session.status,
                f"{session.compliance_score:.1f}%" if session.compliance_score else "N/A",
                str(len(session.deviations))
            ])
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(summary_table)
        
        return content
    
    def _build_baseline_measurements(self, data: ReportData) -> List:
        """Build baseline measurements section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Baseline Measurements", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        # Pressure differentials
        if data.baseline_data.get('pressure_differentials'):
            content.append(Paragraph("Pressure Differentials", styles['Heading2']))
            
            pressure_data = [["Floor", "Door Config", "Pressure (Pa)", "Date"]]
            for baseline in data.baseline_data['pressure_differentials']:
                pressure_data.append([
                    baseline.floor_id,
                    baseline.door_configuration,
                    f"{baseline.pressure_pa:.1f}",
                    baseline.measured_date.strftime('%Y-%m-%d')
                ])
            
            pressure_table = Table(pressure_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1*inch])
            pressure_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(pressure_table)
            content.append(Spacer(1, 12))
        
        # Air velocities
        if data.baseline_data.get('air_velocities'):
            content.append(Paragraph("Air Velocities", styles['Heading2']))
            
            velocity_data = [["Doorway", "Velocity (m/s)", "Date"]]
            for baseline in data.baseline_data['air_velocities']:
                velocity_data.append([
                    baseline.doorway_id,
                    f"{baseline.velocity_ms:.2f}",
                    baseline.measured_date.strftime('%Y-%m-%d')
                ])
            
            velocity_table = Table(velocity_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            velocity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(velocity_table)
            content.append(Spacer(1, 12))
        
        # Door forces
        if data.baseline_data.get('door_forces'):
            content.append(Paragraph("Door Forces", styles['Heading2']))
            
            force_data = [["Door", "Force (N)", "Date"]]
            for baseline in data.baseline_data['door_forces']:
                force_data.append([
                    baseline.door_id,
                    f"{baseline.force_newtons:.1f}",
                    baseline.measured_date.strftime('%Y-%m-%d')
                ])
            
            force_table = Table(force_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            force_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(force_table)
        
        return content
    
    def _build_defects_section(self, data: ReportData) -> List:
        """Build defects and issues section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Defects and Issues", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        if not data.defects:
            content.append(Paragraph("No defects found in the analysis period.", styles['Normal']))
            return content
        
        # Group defects by status
        open_defects = [d for d in data.defects if d.status not in ['closed', 'verified']]
        closed_defects = [d for d in data.defects if d.status in ['closed', 'verified']]
        
        # Open defects
        if open_defects:
            content.append(Paragraph("Open Defects", styles['Heading2']))
            
            open_data = [["Date", "Severity", "Category", "Description", "Status"]]
            for defect in open_defects[:20]:  # Limit to 20 most recent
                open_data.append([
                    defect.discovered_at.strftime('%Y-%m-%d'),
                    defect.severity.upper(),
                    defect.category or "N/A",
                    defect.description[:50] + "..." if len(defect.description) > 50 else defect.description,
                    defect.status
                ])
            
            open_table = Table(open_data, colWidths=[1*inch, 1*inch, 1.5*inch, 2*inch, 1*inch])
            open_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            content.append(open_table)
            content.append(Spacer(1, 12))
        
        # Summary statistics
        content.append(Paragraph("Defect Summary", styles['Heading2']))
        
        summary_data = [
            ["Status", "Count"],
            ["Open", str(len(open_defects))],
            ["Closed/Verified", str(len(closed_defects))],
            ["Total", str(len(data.defects))]
        ]
        
        # Add severity breakdown
        severity_counts = {}
        for defect in data.defects:
            severity_counts[defect.severity] = severity_counts.get(defect.severity, 0) + 1
        
        for severity, count in severity_counts.items():
            summary_data.append([f"{severity.title()} Severity", str(count)])
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(summary_table)
        
        return content
    
    async def _build_charts_section(self, data: ReportData) -> List:
        """Build charts section with matplotlib charts"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Trend Charts", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        # Create charts
        charts = await self._create_trend_charts(data)
        
        for chart_title, chart_bytes in charts.items():
            content.append(Paragraph(chart_title, styles['Heading2']))
            
            # Convert chart to base64 and embed
            chart_base64 = base64.b64encode(chart_bytes).decode('utf-8')
            chart_image = Image(io.BytesIO(chart_bytes), width=6*inch, height=4*inch)
            content.append(chart_image)
            content.append(Spacer(1, 12))
        
        return content
    
    async def _create_trend_charts(self, data: ReportData) -> Dict[str, bytes]:
        """Create matplotlib charts for trends"""
        
        charts = {}
        
        # Set matplotlib style
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 10
        
        # Compliance score over time chart
        if data.ce_test_sessions:
            chart_bytes = self._create_compliance_score_chart(data.ce_test_sessions)
            charts["Compliance Score Over Time"] = chart_bytes
        
        # Defect trends chart
        if data.defects:
            chart_bytes = self._create_defect_trends_chart(data.defects)
            charts["Defect Trends"] = chart_bytes
        
        # Pressure differential trends (if we have enough data)
        if data.baseline_data.get('pressure_differentials') and data.ce_test_sessions:
            chart_bytes = self._create_pressure_trends_chart(data)
            if chart_bytes:
                charts["Pressure Differential Trends"] = chart_bytes
        
        return charts
    
    def _create_compliance_score_chart(self, ce_sessions: List[CETestSession]) -> bytes:
        """Create compliance score over time chart"""
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Filter sessions with compliance scores
        sessions_with_scores = [s for s in ce_sessions if s.compliance_score is not None]
        
        if not sessions_with_scores:
            # Create empty chart
            ax.text(0.5, 0.5, 'No compliance scores available', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Compliance Score Over Time')
        else:
            dates = [s.created_at for s in sessions_with_scores]
            scores = [s.compliance_score for s in sessions_with_scores]
            
            ax.plot(dates, scores, 'b-o', linewidth=2, markersize=6)
            ax.set_title('Compliance Score Over Time')
            ax.set_xlabel('Date')
            ax.set_ylabel('Compliance Score (%)')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 100)
            
            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save to bytes
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer.getvalue()
    
    def _create_defect_trends_chart(self, defects: List[Defect]) -> bytes:
        """Create defect trends chart"""
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Group defects by month
        defect_counts = {}
        for defect in defects:
            month_key = defect.discovered_at.strftime('%Y-%m')
            defect_counts[month_key] = defect_counts.get(month_key, 0) + 1
        
        if defect_counts:
            months = sorted(defect_counts.keys())
            counts = [defect_counts[month] for month in months]
            
            ax.bar(months, counts, color='red', alpha=0.7)
            ax.set_title('Defects Discovered Over Time')
            ax.set_xlabel('Month')
            ax.set_ylabel('Number of Defects')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        else:
            ax.text(0.5, 0.5, 'No defects found', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Defects Discovered Over Time')
        
        plt.tight_layout()
        
        # Save to bytes
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plt.close()
        
        return buffer.getvalue()
    
    def _create_pressure_trends_chart(self, data: ReportData) -> Optional[bytes]:
        """Create pressure differential trends chart"""
        
        # This would require more complex data processing
        # For now, return None to indicate no chart available
        return None
    
    def _build_calibration_verification(self, data: ReportData) -> List:
        """Build calibration verification section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Calibration Verification", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        # Equipment calibration table
        calibration_data = [
            ["Equipment", "Model", "Serial Number", "Last Calibrated", "Next Due", "Status"],
            ["Pressure Gauge", "Model A", "SN001", "2024-01-15", "2025-01-15", "Valid"],
            ["Air Velocity Meter", "Model B", "SN002", "2024-02-01", "2025-02-01", "Valid"],
            ["Force Gauge", "Model C", "SN003", "2024-01-30", "2025-01-30", "Valid"]
        ]
        
        calibration_table = Table(calibration_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        calibration_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(calibration_table)
        
        return content
    
    def _build_engineer_statement(self, data: ReportData) -> List:
        """Build engineer compliance statement section"""
        
        styles = getSampleStyleSheet()
        content = []
        
        content.append(Paragraph("Engineer Compliance Statement", styles['Heading1']))
        content.append(Spacer(1, 12))
        
        # Compliance statement
        statement_text = f"""
        I, [Engineer Name], certify that the fire safety systems at {data.building.name} 
        have been inspected and tested in accordance with AS 1851-2012 requirements.
        
        Based on the analysis of {data.report_metadata['years_analyzed']} years of data, 
        the building has achieved a compliance score of {data.compliance_score}%.
        
        All critical issues identified in this report have been documented and 
        appropriate corrective actions have been recommended.
        
        This report is valid as of {data.report_metadata['generated_at'].strftime('%B %d, %Y')}.
        """
        
        content.append(Paragraph(statement_text, styles['Normal']))
        content.append(Spacer(1, 24))
        
        # Signature lines
        signature_data = [
            ["Engineer Name:", "_________________________"],
            ["License Number:", "_________________________"],
            ["Date:", "_________________________"],
            ["Signature:", "_________________________"]
        ]
        
        signature_table = Table(signature_data, colWidths=[2*inch, 3*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('LINEBELOW', (1, 0), (1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM')
        ]))
        
        content.append(signature_table)
        
        return content
