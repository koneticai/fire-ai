"""
Integration tests for Interface Tests API
Tests full API workflow including definition creation, session execution, and validation.
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.buildings import Building
from src.app.models.interface_test import (
    InterfaceTestDefinition,
    InterfaceTestSession,
    InterfaceTestEvent,
)


@pytest.fixture
async def test_building(db_session: AsyncSession, test_user):
    """Create a test building for interface tests."""
    building = Building(
        id=uuid4(),
        name="Test Fire Safety Building",
        building_type="commercial",
        address="123 Test Street",
        city="Melbourne",
        state="VIC",
        postal_code="3000",
        created_by=test_user.id,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def test_interface_definition(
    db_session: AsyncSession, test_building, test_user
):
    """Create a test interface test definition."""
    definition = InterfaceTestDefinition(
        building_id=test_building.id,
        interface_type="manual_override",
        location_id="fire-panel-1",
        location_name="Main Fire Control Panel",
        test_action="Press manual override button and observe system response",
        expected_result="System switches to manual mode within expected time",
        expected_response_time_s=3,
        guidance={
            "prerequisites": ["Notify building occupants", "Verify system operational"],
            "steps": ["Press override button", "Observe indicator lights", "Verify alarm status"],
        },
        is_active=True,
        created_by=test_user.id,
    )
    db_session.add(definition)
    await db_session.commit()
    await db_session.refresh(definition)
    return definition


class TestInterfaceDefinitionsAPI:
    """Test suite for interface test definitions endpoints."""

    async def test_create_interface_definition(
        self, async_client: AsyncClient, test_building, auth_headers
    ):
        """Test creating a new interface test definition."""
        payload = {
            "building_id": str(test_building.id),
            "interface_type": "alarm_coordination",
            "location_id": "zone-a-panel",
            "location_name": "Zone A Fire Alarm Panel",
            "test_action": "Activate alarm and verify coordination",
            "expected_result": "All zones respond in sequence",
            "expected_response_time_s": 10,
            "guidance": {
                "steps": ["Activate alarm", "Monitor zones", "Verify sequence"]
            },
            "is_active": True,
        }

        response = await async_client.post(
            "/v1/interface-tests/definitions",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["interface_type"] == "alarm_coordination"
        assert data["location_id"] == "zone-a-panel"
        assert data["expected_response_time_s"] == 10
        assert "id" in data
        assert "created_at" in data

    async def test_create_definition_missing_building(
        self, async_client: AsyncClient, auth_headers
    ):
        """Test creating definition with non-existent building."""
        payload = {
            "building_id": str(uuid4()),
            "interface_type": "manual_override",
            "location_id": "test-panel",
            "is_active": True,
        }

        response = await async_client.post(
            "/v1/interface-tests/definitions",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Building not found" in response.json()["detail"]

    async def test_list_interface_definitions(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test listing interface test definitions."""
        response = await async_client.get(
            "/v1/interface-tests/definitions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(d["id"] == str(test_interface_definition.id) for d in data)

    async def test_list_definitions_filtered_by_building(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test filtering definitions by building."""
        response = await async_client.get(
            f"/v1/interface-tests/definitions?building_id={test_interface_definition.building_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert all(d["building_id"] == str(test_interface_definition.building_id) for d in data)

    async def test_update_interface_definition(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test updating an interface test definition."""
        update_payload = {
            "expected_response_time_s": 5,
            "is_active": False,
        }

        response = await async_client.patch(
            f"/v1/interface-tests/definitions/{test_interface_definition.id}",
            json=update_payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expected_response_time_s"] == 5
        assert data["is_active"] is False


class TestInterfaceSessionsAPI:
    """Test suite for interface test sessions endpoints."""

    async def test_create_interface_session(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test creating an interface test session."""
        payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "scheduled",
            "expected_response_time_s": 3,
        }

        response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["definition_id"] == str(test_interface_definition.id)
        assert data["building_id"] == str(test_interface_definition.building_id)
        assert data["interface_type"] == test_interface_definition.interface_type
        assert data["status"] == "scheduled"
        assert data["compliance_outcome"] == "pending"

    async def test_create_session_with_observations(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test creating session with observed data."""
        payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "completed",
            "observed_response_time_s": 2.8,
            "observed_outcome": {
                "indicator_lights": "green",
                "alarm_status": "silenced",
                "system_mode": "manual",
            },
        }

        response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["observed_response_time_s"] == 2.8
        assert data["observed_outcome"]["system_mode"] == "manual"

    async def test_list_interface_sessions_with_filters(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test listing sessions with various filters."""
        # Create a session first
        session_payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "in_progress",
        }
        create_response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=session_payload,
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        # List with status filter
        response = await async_client.get(
            "/v1/interface-tests/sessions?status=in_progress",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "has_more" in data
        assert all(s["status"] == "in_progress" for s in data["sessions"])

    async def test_get_session_with_events(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test fetching session with its events."""
        # Create session
        session_payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "in_progress",
        }
        create_response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=session_payload,
            headers=auth_headers,
        )
        session_id = create_response.json()["id"]

        # Create an event
        event_payload = {
            "interface_test_session_id": session_id,
            "event_type": "start",
            "notes": "Test started",
            "metadata": {"technician": "John Doe"},
        }
        await async_client.post(
            "/v1/interface-tests/events",
            json=event_payload,
            headers=auth_headers,
        )

        # Fetch session with events
        response = await async_client.get(
            f"/v1/interface-tests/sessions/{session_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert "events" in data
        assert len(data["events"]) >= 1
        assert data["events"][0]["event_type"] == "start"

    async def test_update_interface_session(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test updating a session with observations."""
        # Create session
        session_payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "in_progress",
        }
        create_response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=session_payload,
            headers=auth_headers,
        )
        session_id = create_response.json()["id"]

        # Update session
        update_payload = {
            "status": "completed",
            "observed_response_time_s": 3.2,
            "failure_reasons": ["Response time slightly over tolerance"],
        }
        response = await async_client.patch(
            f"/v1/interface-tests/sessions/{session_id}",
            json=update_payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["observed_response_time_s"] == 3.2
        assert len(data["failure_reasons"]) == 1


class TestInterfaceEventsAPI:
    """Test suite for interface test events endpoints."""

    async def test_create_interface_event(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test creating timeline events for a session."""
        # Create session first
        session_payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "in_progress",
        }
        session_response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=session_payload,
            headers=auth_headers,
        )
        session_id = session_response.json()["id"]

        # Create event
        event_payload = {
            "interface_test_session_id": session_id,
            "event_type": "observation",
            "notes": "System indicator light activated",
            "metadata": {"light_color": "green", "response_delay_ms": 150},
        }

        response = await async_client.post(
            "/v1/interface-tests/events",
            json=event_payload,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["interface_test_session_id"] == session_id
        assert data["event_type"] == "observation"
        assert data["metadata"]["light_color"] == "green"

    async def test_list_session_events_chronologically(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test listing events in chronological order."""
        # Create session
        session_payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "in_progress",
        }
        session_response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=session_payload,
            headers=auth_headers,
        )
        session_id = session_response.json()["id"]

        # Create multiple events
        event_types = ["start", "observation", "response_detected", "completion"]
        for event_type in event_types:
            event_payload = {
                "interface_test_session_id": session_id,
                "event_type": event_type,
                "notes": f"Event: {event_type}",
            }
            await async_client.post(
                "/v1/interface-tests/events",
                json=event_payload,
                headers=auth_headers,
            )

        # List events
        response = await async_client.get(
            f"/v1/interface-tests/sessions/{session_id}/events",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        # Verify chronological order
        event_timestamps = [datetime.fromisoformat(e["event_at"].replace("Z", "+00:00")) for e in data]
        assert event_timestamps == sorted(event_timestamps)


class TestInterfaceValidationAPI:
    """Test suite for interface test validation endpoint."""

    async def test_validate_session_pass(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test validation with passing outcome."""
        # Create session with observed time within tolerance
        session_payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "completed",
            "observed_response_time_s": 2.8,  # Expected 3s, within ±2s tolerance
        }
        session_response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=session_payload,
            headers=auth_headers,
        )
        session_id = session_response.json()["id"]

        # Validate session
        validation_payload = {
            "session_id": session_id,
            "tolerance_seconds": 2.0,
        }
        response = await async_client.post(
            "/v1/interface-tests/validate",
            json=validation_payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["compliance_outcome"] == "pass"
        assert data["expected_response_time_s"] == 3
        assert data["observed_response_time_s"] == 2.8
        assert abs(data["response_time_delta_s"] - (-0.2)) < 0.01
        assert len(data["failure_reasons"]) == 0
        assert "passed" in data["validation_summary"].lower()

    async def test_validate_session_fail(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test validation with failing outcome."""
        # Create session with observed time outside tolerance
        session_payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "completed",
            "observed_response_time_s": 6.5,  # Expected 3s, exceeds ±2s tolerance
        }
        session_response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=session_payload,
            headers=auth_headers,
        )
        session_id = session_response.json()["id"]

        # Validate session
        validation_payload = {
            "session_id": session_id,
            "tolerance_seconds": 2.0,
        }
        response = await async_client.post(
            "/v1/interface-tests/validate",
            json=validation_payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["compliance_outcome"] == "fail"
        assert data["response_time_delta_s"] == 3.5
        assert len(data["failure_reasons"]) > 0
        assert "exceeded" in data["failure_reasons"][0].lower()
        assert "failed" in data["validation_summary"].lower()

    async def test_validate_session_missing_observed_time(
        self, async_client: AsyncClient, test_interface_definition, auth_headers
    ):
        """Test validation when observed time is missing."""
        # Create session without observed time
        session_payload = {
            "definition_id": str(test_interface_definition.id),
            "status": "completed",
        }
        session_response = await async_client.post(
            "/v1/interface-tests/sessions",
            json=session_payload,
            headers=auth_headers,
        )
        session_id = session_response.json()["id"]

        # Validate session
        validation_payload = {
            "session_id": session_id,
            "tolerance_seconds": 2.0,
        }
        response = await async_client.post(
            "/v1/interface-tests/validate",
            json=validation_payload,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["compliance_outcome"] == "fail"
        assert "missing" in data["validation_summary"].lower()

    async def test_validate_nonexistent_session(
        self, async_client: AsyncClient, auth_headers
    ):
        """Test validation with non-existent session."""
        validation_payload = {
            "session_id": str(uuid4()),
            "tolerance_seconds": 2.0,
        }
        response = await async_client.post(
            "/v1/interface-tests/validate",
            json=validation_payload,
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
