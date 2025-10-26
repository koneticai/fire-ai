"""Unit tests for C&E backend components."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure models can import Base without real database
os.environ.setdefault("DATABASE_URL", "postgresql://test")

from src.app.models.ce_test import CETestDeviation, CETestSession
from src.app.schemas.ce_test import (
    CETestAnalysisRequest,
    CETestSessionCreate,
    CETestSessionUpdate,
)
from src.app.services.ce_deviation_analyzer import CEDeviationAnalyzer


def _build_session() -> CETestSession:
    session = CETestSession(
        id=uuid4(),
        building_id=uuid4(),
        created_by=uuid4(),
        session_name="Cause & effect",
        test_configuration={},
    )
    session.deviations = []  # type: ignore[attr-defined]
    session.measurements = []  # type: ignore[attr-defined]
    session.reports = []  # type: ignore[attr-defined]
    return session


def _build_deviation(severity: str) -> CETestDeviation:
    deviation = CETestDeviation(
        id=uuid4(),
        test_session_id=uuid4(),
        deviation_type="pressure_drop",
        severity=severity,
        location_id="zone-a",
        expected_value=10.0,
        actual_value=5.0,
        tolerance_percentage=10.0,
        deviation_percentage=50.0,
    )
    return deviation


def test_ce_test_session_defaults():
    session = CETestSession(
        session_name="Baseline",
        building_id=uuid4(),
        created_by=uuid4(),
        test_configuration={},
    )

    assert session.status is None
    assert session.test_type is None

    status_column = CETestSession.__table__.c.status
    assert status_column.default.arg == "active"
    assert str(status_column.server_default.arg) == "active"

    type_column = CETestSession.__table__.c.test_type
    assert type_column.default.arg == "containment_efficiency"
    assert str(type_column.server_default.arg) == "containment_efficiency"


def test_ce_test_session_schema_enforces_enum():
    payload = CETestSessionCreate(
        session_name="Inspection",
        building_id=uuid4(),
    )
    assert payload.status.value == "active"
    assert payload.test_type.value == "containment_efficiency"

    with pytest.raises(ValueError):
        CETestSessionUpdate(status="invalid")


def test_deviation_analyzer_no_deviations():
    session = _build_session()

    analyzer = CEDeviationAnalyzer(MagicMock())
    response, snapshot = analyzer._build_analysis_payload(session, include_recommendations=True)

    assert response.compliance_score == 100
    assert response.deviation_count == 0
    assert "No deviations" in response.analysis_summary
    assert snapshot["total_deviations"] == 0
    assert "recommendations" not in snapshot


def test_deviation_analyzer_mixed_severity():
    session = _build_session()
    session.deviations.extend(
        [
            _build_deviation("critical"),
            _build_deviation("major"),
            _build_deviation("minor"),
        ]
    )

    analyzer = CEDeviationAnalyzer(MagicMock())
    response, snapshot = analyzer._build_analysis_payload(session, include_recommendations=True)

    assert response.deviation_count == 3
    assert response.compliance_score == 45
    assert response.recommendations and len(response.recommendations) == 3
    assert snapshot["counts"]["critical"] == 1


@pytest.mark.asyncio
async def test_analyze_session_persists_updates(monkeypatch):
    session = _build_session()
    session.id = uuid4()
    session.deviations.extend([
        _build_deviation("critical"),
        _build_deviation("major"),
    ])

    db_mock = MagicMock()
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    analyzer = CEDeviationAnalyzer(db_mock)
    analyzer._fetch_session = AsyncMock(return_value=session)  # type: ignore[attr-defined]

    response = await analyzer.analyze_session(session.id, include_recommendations=False)

    db_mock.add.assert_called_once_with(session)
    db_mock.commit.assert_awaited()
    db_mock.refresh.assert_awaited_with(session)
    assert session.deviation_analysis["total_deviations"] == 2
    assert response.recommendations is None


def test_analysis_request_alignment():
    session_id = uuid4()
    payload = CETestAnalysisRequest(test_session_id=session_id)
    assert payload.test_session_id == session_id
    assert payload.include_recommendations is True
