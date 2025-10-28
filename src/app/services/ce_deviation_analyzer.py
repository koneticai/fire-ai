"""Service for analyzing C&E test session deviations and compliance score.

Enhanced with AS 1851-2012 baseline comparison:
- Compare measurements to baseline (10% warning, 20% critical)
- Trigger notifications for critical deviations
- Support first inspection baseline establishment
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import UUID
import logging

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.ce_test import CETestDeviation, CETestSession, CETestMeasurement
from ..schemas.ce_test import CETestAnalysisResponse, CETestSeverity
from .baseline_service import baseline_service
from .notification_service import notification_service

logger = logging.getLogger(__name__)

__all__ = ["CEDeviationAnalyzer"]


class CEDeviationAnalyzer:
    """Analyze deviations for a C&E test session and compute compliance score.
    
    AS 1851-2012 Requirements:
    - Compare to baseline measurements
    - 10% deviation = WARNING
    - 20% deviation = CRITICAL
    - Notify building owner of critical deviations
    """

    _SEVERITY_WEIGHTS: Dict[str, int] = {
        CETestSeverity.CRITICAL.value: 35,
        CETestSeverity.MAJOR.value: 15,
        CETestSeverity.MINOR.value: 5,
    }
    
    # AS 1851-2012 deviation thresholds
    WARNING_THRESHOLD = 10.0   # 10% deviation = warning
    CRITICAL_THRESHOLD = 20.0  # 20% deviation = critical

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def analyze_session(
        self,
        session_id: UUID,
        include_recommendations: bool = True,
        compare_baseline: bool = True,
    ) -> CETestAnalysisResponse:
        """Run deviation analysis for a given C&E test session.
        
        Args:
            session_id: C&E test session UUID
            include_recommendations: Include remediation recommendations
            compare_baseline: Compare measurements to baseline (AS 1851-2012)
        
        Returns:
            Analysis response with compliance score and deviations
        """
        
        if session_id is None:
            raise ValueError("session_id cannot be None")

        session = await self._fetch_session(session_id)
        
        # AS 1851-2012: Compare to baseline and detect deviations
        if compare_baseline:
            await self._compare_to_baseline(session)

        analysis_response, snapshot = self._build_analysis_payload(
            session,
            include_recommendations=include_recommendations,
        )

        session.compliance_score = analysis_response.compliance_score
        session.deviation_analysis = snapshot

        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)

        return analysis_response

    async def _fetch_session(self, session_id: UUID) -> CETestSession:
        """Fetch a session with related deviations, measurements, and reports."""

        stmt = (
            select(CETestSession)
            .options(
                selectinload(CETestSession.deviations),
                selectinload(CETestSession.measurements),
                selectinload(CETestSession.reports),
            )
            .where(CETestSession.id == session_id)
        )

        result = await self._db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise NoResultFound("C&E test session not found")

        return session

    def _build_analysis_payload(
        self,
        session: CETestSession,
        *,
        include_recommendations: bool,
    ) -> Tuple[CETestAnalysisResponse, Dict[str, object]]:
        """Build analysis response and JSON snapshot for persistence."""
        
        if session is None:
            raise ValueError("session cannot be None")

        deviations = list(session.deviations or [])
        counts = self._count_by_severity(deviations)
        total = sum(counts.values())

        base_score = 100
        deduction = sum(
            counts[severity] * weight
            for severity, weight in self._SEVERITY_WEIGHTS.items()
        )
        compliance_score = max(0, min(100, base_score - deduction))

        measurement_count = len(session.measurements or [])
        generated_at = datetime.now(timezone.utc)
        analysis_summary = self._build_summary(total, counts, compliance_score, measurement_count)
        recommendations: Optional[List[str]] = (
            self._recommendations(counts)
            if include_recommendations and total > 0
            else None
        )

        analysis_response = CETestAnalysisResponse(
            test_session_id=session.id,
            analysis_type="compliance_analysis",
            compliance_score=compliance_score,
            deviation_count=total,
            critical_deviations=counts[CETestSeverity.CRITICAL.value],
            major_deviations=counts[CETestSeverity.MAJOR.value],
            minor_deviations=counts[CETestSeverity.MINOR.value],
            analysis_summary=analysis_summary,
            recommendations=recommendations,
            generated_at=generated_at,
        )

        snapshot = {
            "analysis_type": analysis_response.analysis_type,
            "generated_at": generated_at.isoformat(),
            "summary": analysis_summary,
            "counts": counts,
            "total_deviations": total,
            "compliance_score": compliance_score,
            "measurements_evaluated": measurement_count,
        }
        if recommendations is not None:
            snapshot["recommendations"] = recommendations

        return analysis_response, snapshot

    @staticmethod
    def _count_by_severity(deviations: Iterable[CETestDeviation]) -> Dict[str, int]:
        counts = {
            CETestSeverity.CRITICAL.value: 0,
            CETestSeverity.MAJOR.value: 0,
            CETestSeverity.MINOR.value: 0,
        }
        for deviation in deviations:
            severity = getattr(deviation, "severity", None)
            if severity in counts:
                counts[severity] += 1
        return counts

    @staticmethod
    def _build_summary(
        total: int,
        counts: Dict[str, int],
        compliance_score: int,
        measurement_count: int,
    ) -> str:
        if total == 0:
            return (
                f"No deviations recorded across {measurement_count} measurement(s); "
                "compliance score remains 100."
            )

        return (
            "Detected {total} deviation(s) across {measurements} measurement(s) — "
            "critical: {critical}, major: {major}, minor: {minor}. "
            "Compliance score adjusted to {score}."
        ).format(
            total=total,
            measurements=measurement_count,
            critical=counts[CETestSeverity.CRITICAL.value],
            major=counts[CETestSeverity.MAJOR.value],
            minor=counts[CETestSeverity.MINOR.value],
            score=compliance_score,
        )

    @staticmethod
    def _recommendations(counts: Dict[str, int]) -> List[str]:
        recommendations: List[str] = []

        if counts[CETestSeverity.CRITICAL.value]:
            recommendations.append(
                "Resolve all critical deviations immediately and retest affected systems."
            )
        if counts[CETestSeverity.MAJOR.value]:
            recommendations.append(
                "Schedule remediation for major deviations and document mitigation steps."
            )
        if counts[CETestSeverity.MINOR.value]:
            recommendations.append(
                "Monitor minor deviations for trend analysis and include in the next maintenance cycle."
            )

        return recommendations
    
    async def _compare_to_baseline(
        self,
        session: CETestSession
    ) -> None:
        """Compare C&E measurements to baseline per AS 1851-2012.
        
        Detects deviations > 10% (warning) and > 20% (critical).
        Creates CETestDeviation records for violations.
        Triggers notifications for critical deviations.
        """
        building_id = str(session.building_id)
        
        # Get baseline measurements
        baseline = await baseline_service.get_baseline(building_id, self._db)
        
        if not baseline:
            logger.info(f"No baseline for building {building_id} - skipping comparison")
            return
        
        # Get current measurements from session
        measurements = session.measurements or []
        
        # Group measurements by type for comparison
        measurement_values = self._group_measurements_by_type(measurements)
        
        # Compare each parameter to baseline
        critical_deviations = []
        
        for param_type, current_value in measurement_values.items():
            baseline_param = baseline.get(param_type)
            if not baseline_param:
                continue
            
            baseline_value = baseline_param['value']
            
            # Calculate deviation percentage
            if baseline_value != 0:
                deviation_percent = ((current_value - baseline_value) / baseline_value) * 100
            else:
                deviation_percent = 0.0
            
            abs_deviation = abs(deviation_percent)
            
            # Determine severity per AS 1851-2012
            if abs_deviation >= self.CRITICAL_THRESHOLD:
                severity = CETestSeverity.CRITICAL.value
                critical_deviations.append(param_type)
            elif abs_deviation >= self.WARNING_THRESHOLD:
                severity = CETestSeverity.MAJOR.value  # Map WARNING to MAJOR
            else:
                continue  # No deviation to record
            
            # Create deviation record
            deviation = CETestDeviation(
                test_session_id=session.id,
                deviation_type=f"{param_type}_baseline_deviation",
                severity=severity,
                location_id="building_wide",
                expected_value=baseline_value,
                actual_value=current_value,
                tolerance_percentage=self.WARNING_THRESHOLD,
                deviation_percentage=round(deviation_percent, 2),
                description=(
                    f"{param_type.capitalize()} deviation: {round(abs_deviation, 1)}% from baseline. "
                    f"Expected: {baseline_value} {baseline_param['unit']}, "
                    f"Measured: {current_value} {baseline_param['unit']}"
                ),
                recommended_action=(
                    "Immediate remediation required per AS 1851-2012" 
                    if severity == CETestSeverity.CRITICAL.value 
                    else "Schedule maintenance and monitor"
                ),
                is_resolved=False
            )
            
            self._db.add(deviation)
            
            logger.info(
                f"Deviation detected: {param_type} = {round(abs_deviation, 1)}% "
                f"(severity: {severity})"
            )
        
        # Commit deviations before notification
        await self._db.commit()
        
        # Trigger notification for critical deviations
        if critical_deviations:
            await self._notify_critical_deviations(
                session=session,
                critical_params=critical_deviations,
                baseline=baseline,
                measurement_values=measurement_values
            )
    
    @staticmethod
    def _group_measurements_by_type(
        measurements: List[CETestMeasurement]
    ) -> Dict[str, float]:
        """Group measurements by type, taking the average if multiple."""
        from collections import defaultdict
        
        grouped = defaultdict(list)
        
        for measurement in measurements:
            measurement_type = measurement.measurement_type
            
            # Map measurement types to baseline parameters
            if 'pressure' in measurement_type.lower():
                grouped['pressure'].append(measurement.measurement_value)
            elif 'velocity' in measurement_type.lower():
                grouped['velocity'].append(measurement.measurement_value)
            elif 'force' in measurement_type.lower():
                grouped['force'].append(measurement.measurement_value)
        
        # Calculate average for each type
        return {
            param_type: sum(values) / len(values)
            for param_type, values in grouped.items()
            if values
        }
    
    async def _notify_critical_deviations(
        self,
        session: CETestSession,
        critical_params: List[str],
        baseline: Dict[str, Any],
        measurement_values: Dict[str, float]
    ) -> None:
        """Send notification for critical C&E deviations."""
        building_id = str(session.building_id)
        
        # Build defect details for notification
        defect_details = {
            "location": "C&E Testing - Building Wide",
            "severity": "CRITICAL",
            "technical_details": (
                f"Critical C&E deviations (>20%) detected in: {', '.join(critical_params)}. "
                "AS 1851-2012 requires immediate remediation."
            ),
            "remediation_timeline": "24 hours",
            "baseline_comparison": {
                param: {
                    "baseline": baseline.get(param, {}).get('value'),
                    "measured": measurement_values.get(param),
                    "unit": baseline.get(param, {}).get('unit')
                }
                for param in critical_params
            }
        }
        
        try:
            await notification_service.notify_critical_defect(
                building_id=building_id,
                defect_type="CE_BASELINE_DEVIATION_CRITICAL",
                defect_details=defect_details,
                db=self._db
            )
            
            logger.info(
                f"Critical C&E deviation notification sent for building {building_id}"
            )
        
        except Exception as e:
            logger.error(
                f"Failed to send C&E deviation notification: {e}",
                exc_info=True
            )
