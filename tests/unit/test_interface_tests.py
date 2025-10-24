"""
Unit tests for interface test validator service.
"""

import os
import uuid
from datetime import datetime

import pytest

# Ensure database module can initialize without real connection
os.environ.setdefault("DATABASE_URL", "postgresql://test")

from src.app.models.interface_test import (  # noqa: E402  pylint: disable=wrong-import-position
    InterfaceTestDefinition,
    InterfaceTestSession,
    InterfaceTestEvent,
)
from src.app.services.interface_test_validator import (  # noqa: E402  pylint: disable=wrong-import-position
    InterfaceTestValidator,
    InterfaceTestValidationRequest,
)


class FakeQuery:
    """Minimal SQLAlchemy query stub for validator tests."""

    def __init__(self, data):
        self._data = list(data)

    def filter(self, criterion):
        from sqlalchemy.sql.elements import BinaryExpression

        if not isinstance(criterion, BinaryExpression):
            raise NotImplementedError("Unsupported filter criterion")

        column = criterion.left
        attr_name = getattr(column, "key", getattr(column, "name", None))
        if attr_name is None:
            raise ValueError("Unable to determine attribute name from column")

        target_value = getattr(criterion.right, "value", None)
        filtered = [
            obj for obj in self._data if getattr(obj, attr_name) == target_value
        ]
        return FakeQuery(filtered)

    def first(self):
        return self._data[0] if self._data else None

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._data)


class FakeSession:
    """Session stub providing SQLAlchemy-like behaviour for validator tests."""

    def __init__(self, sessions=None, definitions=None):
        self.sessions = sessions or []
        self.definitions = definitions or []
        self.events = []
        self.added = []

    def query(self, model):
        if model is InterfaceTestSession:
            return FakeQuery(self.sessions)
        if model is InterfaceTestDefinition:
            return FakeQuery(self.definitions)
        if model is InterfaceTestEvent:
            return FakeQuery(self.events)
        return FakeQuery([])

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, InterfaceTestEvent):
            self.events.append(obj)

    def commit(self):
        return None

    def refresh(self, obj):
        return None


def build_definition(expected_time=None):
    """Helper to construct interface test definition."""
    return InterfaceTestDefinition(
        id=uuid.uuid4(),
        building_id=uuid.uuid4(),
        interface_type="manual_override",
        location_id="control-panel-1",
        location_name="Fire Control Panel",
        expected_result="System switches to manual override",
        expected_response_time_s=expected_time,
        guidance={"steps": ["Press override", "Observe panel status"]},
        is_active=True,
    )


def build_session(definition, observed_time=None):
    """Helper to construct interface test session."""
    session = InterfaceTestSession(
        id=uuid.uuid4(),
        definition_id=definition.id,
        building_id=definition.building_id,
        interface_type=definition.interface_type,
        location_id=definition.location_id,
        status="completed",
        compliance_outcome="pending",
        expected_response_time_s=definition.expected_response_time_s,
        observed_response_time_s=observed_time,
        failure_reasons=[],
        observed_outcome={"notes": "Initial observation"},
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    session.definition = definition
    session.events = []
    return session


def test_interface_validator_pass_within_tolerance():
    """Validator should mark session as pass when within tolerance."""
    definition = build_definition(expected_time=6)
    session = build_session(definition, observed_time=7.5)
    fake_db = FakeSession(sessions=[session], definitions=[definition])

    validator = InterfaceTestValidator(fake_db)
    request = InterfaceTestValidationRequest(session_id=session.id, tolerance_seconds=2.0)

    response = validator.validate(request)

    assert response.compliance_outcome == "pass"
    assert pytest.approx(response.response_time_delta_s, rel=1e-3) == 1.5
    assert response.failure_reasons == []
    assert "passed" in response.validation_summary.lower()
    assert len(fake_db.events) == 1
    event = fake_db.events[0]
    assert event.event_type == "validation"
    assert event.event_metadata["outcome"] == "pass"


def test_interface_validator_fail_missing_observed_time():
    """Validator should fail when observed response time is missing."""
    definition = build_definition(expected_time=5)
    session = build_session(definition, observed_time=None)
    fake_db = FakeSession(sessions=[session], definitions=[definition])

    validator = InterfaceTestValidator(fake_db)
    request = InterfaceTestValidationRequest(session_id=session.id, tolerance_seconds=2.0)

    response = validator.validate(request)

    assert response.compliance_outcome == "fail"
    assert response.observed_response_time_s is None
    assert "missing" in response.validation_summary.lower()
    assert response.failure_reasons == ["Observed response time not recorded."]
    assert len(fake_db.events) == 1
    assert fake_db.events[0].event_metadata["outcome"] == "fail"


def test_interface_validator_pending_without_expected_time():
    """Validator should keep session pending when expected time is undefined."""
    definition = build_definition(expected_time=None)
    session = build_session(definition, observed_time=4.2)
    fake_db = FakeSession(sessions=[session], definitions=[definition])

    validator = InterfaceTestValidator(fake_db)
    request = InterfaceTestValidationRequest(session_id=session.id, tolerance_seconds=2.0)

    response = validator.validate(request)

    assert response.compliance_outcome == "pending"
    assert response.expected_response_time_s is None
    assert response.failure_reasons == []
    assert "pending" in response.validation_summary.lower()
    assert len(fake_db.events) == 1
    assert fake_db.events[0].event_metadata["outcome"] == "pending"
