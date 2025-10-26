"""Service for analyzing C&E test session deviations and compliance score."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.ce_test import CETestDeviation, CETestSession
from ..schemas.ce_test import CETestAnalysisResponse, CETestSeverity

__all__ = ["CEDeviationAnalyzer"]


class CEDeviationAnalyzer:
    """Analyze deviations for a C&E test session and compute compliance score."""

    _SEVERITY_WEIGHTS: Dict[str, int] = {
        CETestSeverity.CRITICAL.value: 35,
        CETestSeverity.MAJOR.value: 15,
        CETestSeverity.MINOR.value: 5,
    }

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def analyze_session(
        self,
        session_id: UUID,
        include_recommendations: bool = True,
    ) -> CETestAnalysisResponse:
        """Run deviation analysis for a given C&E test session."""
        
        if session_id is None:
            raise ValueError("session_id cannot be None")

        session = await self._fetch_session(session_id)

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
