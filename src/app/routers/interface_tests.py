"""
Interface Tests API Router

Provides endpoints for managing interface test definitions, execution sessions,
timeline events, and validator operations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database.core import get_db
from ..dependencies import get_current_active_user
from ..schemas.auth import TokenPayload
from ..models.buildings import Building
from ..models.test_sessions import TestSession
from ..models.interface_test import (
    InterfaceTestDefinition,
    InterfaceTestSession,
    InterfaceTestEvent,
)
from ..schemas.interface_test import (
    InterfaceTestDefinitionCreate,
    InterfaceTestDefinitionRead,
    InterfaceTestDefinitionUpdate,
    InterfaceTestSessionCreate,
    InterfaceTestSessionUpdate,
    InterfaceTestSessionRead,
    InterfaceTestSessionListResponse,
    InterfaceTestSessionWithEvents,
    InterfaceTestEventCreate,
    InterfaceTestEventRead,
    InterfaceTestValidationRequest,
    InterfaceTestValidationResponse,
)
from ..services.interface_test_validator import InterfaceTestValidator

router = APIRouter(prefix="/v1/interface-tests", tags=["Interface Tests"])


@router.post(
    "/definitions",
    response_model=InterfaceTestDefinitionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_interface_definition(
    definition_data: InterfaceTestDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Create an interface test definition for a building."""
    building = (
        db.query(Building)
        .filter(Building.id == definition_data.building_id)
        .first()
    )
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Building not found"
        )

    definition = InterfaceTestDefinition(
        building_id=definition_data.building_id,
        interface_type=definition_data.interface_type,
        location_id=definition_data.location_id,
        location_name=definition_data.location_name,
        test_action=definition_data.test_action,
        expected_result=definition_data.expected_result,
        expected_response_time_s=definition_data.expected_response_time_s,
        guidance=definition_data.guidance or {},
        is_active=definition_data.is_active,
        created_by=current_user.user_id,
    )
    db.add(definition)
    db.commit()
    db.refresh(definition)

    return definition


@router.get(
    "/definitions",
    response_model=List[InterfaceTestDefinitionRead],
)
async def list_interface_definitions(
    building_id: Optional[UUID] = Query(None, description="Filter by building ID"),
    interface_type: Optional[str] = Query(
        None, description="Filter by interface type"
    ),
    is_active: Optional[bool] = Query(
        None, description="Filter by active status"
    ),
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """List interface test definitions with optional filters."""
    query = db.query(InterfaceTestDefinition)

    if building_id:
        query = query.filter(InterfaceTestDefinition.building_id == building_id)
    if interface_type:
        query = query.filter(InterfaceTestDefinition.interface_type == interface_type)
    if is_active is not None:
        query = query.filter(InterfaceTestDefinition.is_active == is_active)

    definitions = query.order_by(
        desc(InterfaceTestDefinition.created_at)
    ).all()
    return definitions


@router.patch(
    "/definitions/{definition_id}",
    response_model=InterfaceTestDefinitionRead,
)
async def update_interface_definition(
    definition_id: UUID,
    update_data: InterfaceTestDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Update an interface test definition."""
    definition = (
        db.query(InterfaceTestDefinition)
        .filter(InterfaceTestDefinition.id == definition_id)
        .first()
    )
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found"
        )

    update_payload = update_data.model_dump(exclude_unset=True)
    for field, value in update_payload.items():
        setattr(definition, field, value)

    db.commit()
    db.refresh(definition)
    return definition


@router.post(
    "/sessions",
    response_model=InterfaceTestSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_interface_session(
    session_data: InterfaceTestSessionCreate,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Create an interface test execution session."""
    definition = (
        db.query(InterfaceTestDefinition)
        .filter(InterfaceTestDefinition.id == session_data.definition_id)
        .first()
    )
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Definition not found"
        )

    if session_data.test_session_id:
        test_session_exists = (
            db.query(TestSession)
            .filter(TestSession.id == session_data.test_session_id)
            .first()
        )
        if not test_session_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Linked test session not found",
            )

    expected_response_time = (
        session_data.expected_response_time_s or definition.expected_response_time_s
    )

    session = InterfaceTestSession(
        definition_id=session_data.definition_id,
        test_session_id=session_data.test_session_id,
        building_id=definition.building_id,
        interface_type=definition.interface_type,
        location_id=definition.location_id,
        status=session_data.status,
        expected_response_time_s=expected_response_time,
        observed_response_time_s=session_data.observed_response_time_s,
        observed_outcome=session_data.observed_outcome or None,
        failure_reasons=session_data.failure_reasons or [],
        validation_summary=session_data.validation_summary,
        started_at=session_data.started_at,
        completed_at=session_data.completed_at,
        created_by=current_user.user_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get(
    "/sessions",
    response_model=InterfaceTestSessionListResponse,
)
async def list_interface_sessions(
    building_id: Optional[UUID] = Query(None, description="Filter by building ID"),
    interface_type: Optional[str] = Query(
        None, description="Filter by interface type"
    ),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by session status"
    ),
    compliance_outcome: Optional[str] = Query(
        None, description="Filter by compliance outcome"
    ),
    limit: int = Query(50, ge=1, le=100, description="Number of sessions to return"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """List interface test sessions with optional filters and cursor pagination."""
    query = db.query(InterfaceTestSession)

    if building_id:
        query = query.filter(InterfaceTestSession.building_id == building_id)
    if interface_type:
        query = query.filter(InterfaceTestSession.interface_type == interface_type)
    if status_filter:
        query = query.filter(InterfaceTestSession.status == status_filter)
    if compliance_outcome:
        query = query.filter(
            InterfaceTestSession.compliance_outcome == compliance_outcome
        )

    if cursor:
        try:
            cursor_uuid = UUID(cursor)
            query = query.filter(InterfaceTestSession.id < cursor_uuid)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor format",
            ) from exc

    sessions = (
        query.order_by(desc(InterfaceTestSession.id)).limit(limit + 1).all()
    )

    has_more = len(sessions) > limit
    if has_more:
        sessions = sessions[:-1]

    next_cursor = str(sessions[-1].id) if sessions and has_more else None

    return InterfaceTestSessionListResponse(
        sessions=sessions,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=InterfaceTestSessionWithEvents,
)
async def get_interface_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Fetch an interface test session with its events."""
    session = (
        db.query(InterfaceTestSession)
        .filter(InterfaceTestSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Explicitly load events ordered chronologically
    session.events = (
        db.query(InterfaceTestEvent)
        .filter(InterfaceTestEvent.interface_test_session_id == session_id)
        .order_by(InterfaceTestEvent.event_at.asc())
        .all()
    )

    return session


@router.patch(
    "/sessions/{session_id}",
    response_model=InterfaceTestSessionRead,
)
async def update_interface_session(
    session_id: UUID,
    update_data: InterfaceTestSessionUpdate,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Update an interface test session."""
    session = (
        db.query(InterfaceTestSession)
        .filter(InterfaceTestSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    update_payload = update_data.model_dump(exclude_unset=True)
    failure_reasons = update_payload.pop("failure_reasons", None)
    observed_outcome = update_payload.pop("observed_outcome", None)

    for field, value in update_payload.items():
        setattr(session, field, value)

    if failure_reasons is not None:
        session.failure_reasons = failure_reasons
    if observed_outcome is not None:
        session.observed_outcome = observed_outcome

    db.commit()
    db.refresh(session)
    return session


@router.post(
    "/events",
    response_model=InterfaceTestEventRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_interface_event(
    event_data: InterfaceTestEventCreate,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Create an interface test timeline event."""
    session_exists = (
        db.query(InterfaceTestSession)
        .filter(InterfaceTestSession.id == event_data.interface_test_session_id)
        .first()
    )
    if not session_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    event = InterfaceTestEvent(
        interface_test_session_id=event_data.interface_test_session_id,
        event_type=event_data.event_type,
        event_at=event_data.event_at,
        notes=event_data.notes,
        event_metadata=event_data.event_metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return event


@router.get(
    "/sessions/{session_id}/events",
    response_model=List[InterfaceTestEventRead],
)
async def list_interface_events(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """List events for an interface test session."""
    session_exists = (
        db.query(InterfaceTestSession)
        .filter(InterfaceTestSession.id == session_id)
        .first()
    )
    if not session_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    events = (
        db.query(InterfaceTestEvent)
        .filter(InterfaceTestEvent.interface_test_session_id == session_id)
        .order_by(InterfaceTestEvent.event_at.asc())
        .all()
    )
    return events


@router.post(
    "/validate",
    response_model=InterfaceTestValidationResponse,
)
async def validate_interface_session(
    validation_request: InterfaceTestValidationRequest,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Validate an interface test session using the validator service."""
    validator = InterfaceTestValidator(db)
    try:
        result = validator.validate(
            validation_request, current_user_id=current_user.user_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return result
