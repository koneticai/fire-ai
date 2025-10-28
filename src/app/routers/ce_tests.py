"""FastAPI router for C&E (Containment & Efficiency) test management."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.core import get_db
from ..dependencies import get_current_active_user
from ..models.ce_test import CETestDeviation, CETestMeasurement, CETestSession
from ..schemas.auth import TokenPayload
from ..schemas.ce_test import (
    CETestAnalysisRequest,
    CETestAnalysisResponse,
    CETestDeviationCreate,
    CETestDeviationRead,
    CETestDeviationUpdate,
    CETestMeasurementCreate,
    CETestMeasurementRead,
    CETestSessionCreate,
    CETestSessionListResponse,
    CETestSessionRead,
    CETestSessionUpdate,
    CETestSessionWithDetails,
    CETestStatus,
)
from ..services.ce_deviation_analyzer import CEDeviationAnalyzer
from ..services.baseline_service import baseline_service

router = APIRouter(prefix="/v1/ce/tests", tags=["ce_tests"])


def _decode_cursor(cursor: str) -> uuid.UUID:
    try:
        data = json.loads(base64.b64decode(cursor).decode())
        return uuid.UUID(data["last_evaluated_id"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


def _encode_cursor(session_id: uuid.UUID) -> str:
    payload = {"last_evaluated_id": str(session_id)}
    return base64.b64encode(json.dumps(payload).encode()).decode()


@router.get("/sessions", response_model=CETestSessionListResponse)
async def list_ce_test_sessions(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = None,
    status: Optional[List[str]] = Query(None),
    building_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """List C&E test sessions owned by the current user with cursor pagination."""

    stmt = (
        select(CETestSession)
        .where(CETestSession.created_by == current_user.user_id)
        .order_by(CETestSession.id.desc())
    )

    if cursor:
        last_id = _decode_cursor(cursor)
        stmt = stmt.where(CETestSession.id < last_id)

    if status:
        try:
            status_values = [CETestStatus(value).value for value in status]
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid status filter"
            ) from exc
        stmt = stmt.where(CETestSession.status.in_(status_values))

    if building_id:
        stmt = stmt.where(CETestSession.building_id == building_id)

    stmt = stmt.limit(limit + 1)

    result = await db.execute(stmt)
    sessions = result.scalars().all()

    has_more = len(sessions) > limit
    if has_more:
        sessions = sessions[:limit]

    next_cursor = _encode_cursor(sessions[-1].id) if has_more else None

    payload = [
        CETestSessionRead.model_validate(session, from_attributes=True)
        for session in sessions
    ]

    return CETestSessionListResponse(
        sessions=payload,
        next_cursor=next_cursor,
        has_more=has_more,
        total_items=None,
    )


@router.post("/sessions", response_model=CETestSessionRead, status_code=201)
async def create_ce_test_session(
    payload: CETestSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Create a new C&E test session."""

    session = CETestSession(
        id=uuid.uuid4(),
        building_id=payload.building_id,
        created_by=current_user.user_id,
        session_name=payload.session_name,
        test_type=payload.test_type.value,
        compliance_standard=payload.compliance_standard,
        status=payload.status.value,
        test_configuration=dict(payload.test_configuration),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return CETestSessionRead.model_validate(session, from_attributes=True)


async def _get_session_for_user(
    session_id: uuid.UUID,
    current_user: TokenPayload,
    db: AsyncSession,
    *,
    eager: bool = False,
) -> CETestSession:
    options = []
    if eager:
        options.extend(
            [
                selectinload(CETestSession.measurements),
                selectinload(CETestSession.deviations),
                selectinload(CETestSession.reports),
            ]
        )

    stmt = (
        select(CETestSession)
        .options(*options)
        .where(
            and_(
                CETestSession.id == session_id,
                CETestSession.created_by == current_user.user_id,
            )
        )
    )

    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="C&E test session not found")

    return session


@router.get("/sessions/{session_id}", response_model=CETestSessionWithDetails)
async def get_ce_test_session(
    session_id: uuid.UUID,
    include_details: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Retrieve a specific C&E test session."""

    session = await _get_session_for_user(
        session_id,
        current_user,
        db,
        eager=include_details,
    )

    if include_details:
        return CETestSessionWithDetails.model_validate(session, from_attributes=True)

    base = CETestSessionRead.model_validate(session, from_attributes=True)
    return CETestSessionWithDetails(
        **base.model_dump(),
        measurements=[],
        deviations=[],
        reports=[],
    )


@router.patch("/sessions/{session_id}", response_model=CETestSessionRead)
async def update_ce_test_session(
    session_id: uuid.UUID,
    payload: CETestSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Update mutable fields for a C&E test session."""

    session = await _get_session_for_user(session_id, current_user, db)
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        if field == "test_configuration" and value is None:
            continue
        if hasattr(value, "value"):
            value = value.value
        setattr(session, field, value)

    await db.commit()
    await db.refresh(session)

    return CETestSessionRead.model_validate(session, from_attributes=True)


@router.post(
    "/sessions/{session_id}/measurements",
    response_model=CETestMeasurementRead,
    status_code=201,
)
async def add_ce_test_measurement(
    session_id: uuid.UUID,
    payload: CETestMeasurementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Append a measurement to a C&E test session."""

    session = await _get_session_for_user(session_id, current_user, db)

    if payload.test_session_id != session.id:
        raise HTTPException(
            status_code=400, detail="Payload session does not match path parameter"
        )

    timestamp = payload.timestamp or datetime.now(timezone.utc)

    measurement = CETestMeasurement(
        id=uuid.uuid4(),
        test_session_id=session.id,
        measurement_type=payload.measurement_type,
        location_id=payload.location_id,
        measurement_value=payload.measurement_value,
        unit=payload.unit,
        timestamp=timestamp,
        measurement_metadata=payload.measurement_metadata or {},
    )

    db.add(measurement)
    await db.commit()
    await db.refresh(measurement)

    return CETestMeasurementRead.model_validate(measurement, from_attributes=True)


@router.get(
    "/sessions/{session_id}/measurements",
    response_model=List[CETestMeasurementRead],
)
async def list_ce_test_measurements(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """List measurements for a C&E test session."""

    await _get_session_for_user(session_id, current_user, db)

    stmt = (
        select(CETestMeasurement)
        .where(CETestMeasurement.test_session_id == session_id)
        .order_by(CETestMeasurement.timestamp.desc())
    )
    result = await db.execute(stmt)
    measurements = result.scalars().all()
    return [
        CETestMeasurementRead.model_validate(m, from_attributes=True)
        for m in measurements
    ]


@router.post(
    "/sessions/{session_id}/deviations",
    response_model=CETestDeviationRead,
    status_code=201,
)
async def add_ce_test_deviation(
    session_id: uuid.UUID,
    payload: CETestDeviationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Create a deviation for a C&E test session."""

    session = await _get_session_for_user(session_id, current_user, db)

    if payload.test_session_id != session.id:
        raise HTTPException(
            status_code=400, detail="Payload session does not match path parameter"
        )

    deviation = CETestDeviation(
        id=uuid.uuid4(),
        test_session_id=session.id,
        deviation_type=payload.deviation_type,
        severity=payload.severity.value,
        location_id=payload.location_id,
        expected_value=payload.expected_value,
        actual_value=payload.actual_value,
        tolerance_percentage=payload.tolerance_percentage,
        deviation_percentage=payload.deviation_percentage,
        description=payload.description,
        recommended_action=payload.recommended_action,
    )

    db.add(deviation)
    await db.commit()
    await db.refresh(deviation)

    return CETestDeviationRead.model_validate(deviation, from_attributes=True)


@router.patch("/deviations/{deviation_id}", response_model=CETestDeviationRead)
async def update_ce_test_deviation(
    deviation_id: uuid.UUID,
    payload: CETestDeviationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Update deviation metadata."""

    stmt = (
        select(CETestDeviation)
        .options(selectinload(CETestDeviation.test_session))
        .where(CETestDeviation.id == deviation_id)
    )
    result = await db.execute(stmt)
    deviation = result.scalar_one_or_none()
    if deviation is None:
        raise HTTPException(status_code=404, detail="C&E deviation not found")

    if deviation.test_session.created_by != current_user.user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this deviation"
        )

    updates = payload.model_dump(exclude_unset=True)
    if "resolved_by" in updates and updates["resolved_by"] is not None:
        if updates["resolved_by"] != current_user.user_id:
            raise HTTPException(
                status_code=400, detail="Resolved by must match current user"
            )
        deviation.resolved_at = datetime.now(timezone.utc)

    for field, value in updates.items():
        setattr(deviation, field, value)

    if updates.get("is_resolved") is True and deviation.resolved_at is None:
        deviation.resolved_at = datetime.now(timezone.utc)
    if updates.get("is_resolved") is False:
        deviation.resolved_at = None
        deviation.resolved_by = None

    await db.commit()
    await db.refresh(deviation)

    return CETestDeviationRead.model_validate(deviation, from_attributes=True)


@router.post(
    "/sessions/{session_id}/analysis",
    response_model=CETestAnalysisResponse,
)
async def analyze_ce_test_session(
    session_id: uuid.UUID,
    payload: CETestAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Trigger deviation analysis for a session and persist results.

    AS 1851-2012 Compliance:
    - First inspection: Establishes baseline from measurements
    - Subsequent inspections: Compare to baseline (10% warning, 20% critical)
    - Critical deviations trigger 24-hour notification
    """

    session = await _get_session_for_user(session_id, current_user, db, eager=True)

    if payload.test_session_id != session.id:
        raise HTTPException(
            status_code=400, detail="Payload session does not match path parameter"
        )

    # Check if baseline exists for this building
    building_id = str(session.building_id)
    baseline = await baseline_service.get_baseline(building_id, db)

    # If no baseline, establish from current measurements
    if not baseline and session.measurements:
        # Extract measurement values for baseline using helper
        measurement_values = baseline_service.extract_measurements_from_session(
            session.measurements
        )

        if measurement_values:
            baseline = await baseline_service.establish_baseline(
                building_id=building_id,
                measurements=measurement_values,
                created_by=str(current_user.user_id),
                db=db,
            )

    analyzer = CEDeviationAnalyzer(db)
    try:
        # Run analysis with baseline comparison if baseline exists
        return await analyzer.analyze_session(
            session.id,
            include_recommendations=payload.include_recommendations,
            compare_baseline=(baseline is not None),
        )
    except Exception as exc:  # pragma: no cover - unexpected errors bubbled as 500
        raise HTTPException(
            status_code=500, detail="Failed to analyze session"
        ) from exc
