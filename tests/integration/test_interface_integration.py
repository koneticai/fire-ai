"""
Integration tests for Interface Test API
Tests the 4 interface test types per AS 1851-2012 requirements
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.main import app
from src.app.database.core import get_db
from src.app.models.interface_test import (
    InterfaceTestSession, 
    InterfaceTestStep, 
    InterfaceTestResult
)
from src.app.models.buildings import Building
from src.app.models.test_sessions import TestSession
from src.app.models.users import User


class TestInterfaceIntegration:
    """Integration tests for Interface Test API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    async def test_data(self, db: AsyncSession):
        """Create test data for interface tests"""
        # Create test user
        user = User(
            id=uuid.uuid4(),
            username="test_engineer@example.com",
            email="test_engineer@example.com",
            full_name="Test Engineer",
            is_active=True
        )
        db.add(user)
        await db.commit()

        # Create test building
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            address="123 Test Street",
            is_active=True
        )
        db.add(building)
        await db.commit()

        # Create test session
        test_session = TestSession(
            id=uuid.uuid4(),
            building_id=building.id,
            session_name="Interface Test Session",
            status="active",
            created_by=user.id
        )
        db.add(test_session)
        await db.commit()

        return {
            "user": user,
            "building": building,
            "test_session": test_session
        }

    def test_interface_test_templates(self, client: TestClient):
        """Test retrieving interface test templates"""
        response = client.get("/v1/interface-tests/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 4  # 4 test types
        test_types = [template["test_type"] for template in data]
        assert "manual_override" in test_types
        assert "alarm_coordination" in test_types
        assert "shutdown_sequence" in test_types
        assert "sprinkler_interface" in test_types

    def test_manual_override_test(self, client: TestClient, test_data):
        """Test manual override interface test (fire panel, BMS, local switches)"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "manual_override",
            "description": "Test manual override functionality"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        assert response.status_code == 201
        session_id = response.json()["id"]

        # Test manual override steps
        steps = [
            {
                "step_name": "Fire Panel Override",
                "action": "Activate fire panel manual override",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
                "response_time": 2.0,
                "status": "completed",
                "notes": "Panel responded within 2 seconds"
            },
            {
                "step_name": "BMS Override",
                "action": "Test BMS manual override",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=1.5)).isoformat(),
                "response_time": 1.5,
                "status": "completed",
                "notes": "BMS override working correctly"
            },
            {
                "step_name": "Local Switch Override",
                "action": "Test local switch override",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.5)).isoformat(),
                "response_time": 2.5,
                "status": "completed",
                "notes": "Local switch functional"
            }
        ]

        for step in steps:
            response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step)
            assert response.status_code == 201

        # Complete test
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "passed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/complete", json=completion_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["overall_status"] == "passed"
        assert data["test_type"] == "manual_override"
        assert len(data["steps"]) == 3

    def test_alarm_coordination_test(self, client: TestClient, test_data):
        """Test alarm coordination interface (detection to pressurization)"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "alarm_coordination",
            "description": "Test alarm coordination sequence"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        assert response.status_code == 201
        session_id = response.json()["id"]

        # Test alarm coordination steps
        steps = [
            {
                "step_name": "Smoke Detection",
                "action": "Activate smoke detector",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=1.0)).isoformat(),
                "response_time": 1.0,
                "status": "completed"
            },
            {
                "step_name": "Alarm Activation",
                "action": "Verify alarm activation",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
                "response_time": 2.0,
                "status": "completed"
            },
            {
                "step_name": "Pressurization Start",
                "action": "Verify pressurization system starts",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=8.0)).isoformat(),
                "response_time": 8.0,
                "status": "completed"
            }
        ]

        for step in steps:
            response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step)
            assert response.status_code == 201

        # Complete test
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "passed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/complete", json=completion_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["overall_status"] == "passed"
        assert data["test_type"] == "alarm_coordination"

    def test_shutdown_sequence_test(self, client: TestClient, test_data):
        """Test shutdown sequence (orderly system stop)"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "shutdown_sequence",
            "description": "Test orderly shutdown sequence"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        assert response.status_code == 201
        session_id = response.json()["id"]

        # Test shutdown sequence steps
        steps = [
            {
                "step_name": "Shutdown Initiation",
                "action": "Initiate system shutdown",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=1.0)).isoformat(),
                "response_time": 1.0,
                "status": "completed"
            },
            {
                "step_name": "Fan Shutdown",
                "action": "Verify fan shutdown sequence",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=5.0)).isoformat(),
                "response_time": 5.0,
                "status": "completed"
            },
            {
                "step_name": "System Isolation",
                "action": "Verify system isolation",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=3.0)).isoformat(),
                "response_time": 3.0,
                "status": "completed"
            }
        ]

        for step in steps:
            response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step)
            assert response.status_code == 201

        # Complete test
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "passed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/complete", json=completion_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["overall_status"] == "passed"
        assert data["test_type"] == "shutdown_sequence"

    def test_sprinkler_interface_test(self, client: TestClient, test_data):
        """Test sprinkler interface (activation response)"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "sprinkler_interface",
            "description": "Test sprinkler interface activation"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        assert response.status_code == 201
        session_id = response.json()["id"]

        # Test sprinkler interface steps
        steps = [
            {
                "step_name": "Sprinkler Activation",
                "action": "Simulate sprinkler activation",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=1.0)).isoformat(),
                "response_time": 1.0,
                "status": "completed"
            },
            {
                "step_name": "Interface Response",
                "action": "Verify interface response",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
                "response_time": 2.0,
                "status": "completed"
            },
            {
                "step_name": "System Coordination",
                "action": "Verify system coordination",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=3.0)).isoformat(),
                "response_time": 3.0,
                "status": "completed"
            }
        ]

        for step in steps:
            response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step)
            assert response.status_code == 201

        # Complete test
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "passed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/complete", json=completion_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["overall_status"] == "passed"
        assert data["test_type"] == "sprinkler_interface"

    def test_timing_validation_manual_override(self, client: TestClient, test_data):
        """Test timing validation for manual override (<3s requirement)"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "manual_override",
            "description": "Test timing validation"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        session_id = response.json()["id"]

        # Test step that passes (<3s)
        step_pass = {
            "step_name": "Fast Response",
            "action": "Test fast response",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.5)).isoformat(),
            "response_time": 2.5,
            "status": "completed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step_pass)
        assert response.status_code == 201
        assert response.json()["validation_status"] == "passed"

        # Test step that fails (>3s)
        step_fail = {
            "step_name": "Slow Response",
            "action": "Test slow response",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=4.0)).isoformat(),
            "response_time": 4.0,
            "status": "completed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step_fail)
        assert response.status_code == 201
        assert response.json()["validation_status"] == "failed"

    def test_timing_validation_alarm_coordination(self, client: TestClient, test_data):
        """Test timing validation for alarm coordination (<10s requirement)"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "alarm_coordination",
            "description": "Test timing validation"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        session_id = response.json()["id"]

        # Test step that passes (<10s)
        step_pass = {
            "step_name": "Fast Coordination",
            "action": "Test fast coordination",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=8.0)).isoformat(),
            "response_time": 8.0,
            "status": "completed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step_pass)
        assert response.status_code == 201
        assert response.json()["validation_status"] == "passed"

        # Test step that fails (>10s)
        step_fail = {
            "step_name": "Slow Coordination",
            "action": "Test slow coordination",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=12.0)).isoformat(),
            "response_time": 12.0,
            "status": "completed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step_fail)
        assert response.status_code == 201
        assert response.json()["validation_status"] == "failed"

    def test_evidence_association(self, client: TestClient, test_data):
        """Test linking evidence to interface test steps"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "manual_override",
            "description": "Test evidence association"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        session_id = response.json()["id"]

        # Test step with evidence
        step_data = {
            "step_name": "Evidence Test",
            "action": "Test with evidence",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
            "response_time": 2.0,
            "status": "completed",
            "evidence_ids": ["evidence-123", "evidence-456"]
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step_data)
        assert response.status_code == 201
        
        data = response.json()
        assert "evidence_ids" in data
        assert len(data["evidence_ids"]) == 2
        assert "evidence-123" in data["evidence_ids"]
        assert "evidence-456" in data["evidence_ids"]

    def test_fault_generation_for_failures(self, client: TestClient, test_data):
        """Test automatic fault generation for failed interface tests"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "manual_override",
            "description": "Test fault generation"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        session_id = response.json()["id"]

        # Test step that fails timing
        step_data = {
            "step_name": "Failed Test",
            "action": "Test that fails",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=5.0)).isoformat(),
            "response_time": 5.0,  # >3s threshold
            "status": "completed"
        }
        
        client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step_data)

        # Complete test with failures
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "failed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/complete", json=completion_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "generated_faults" in data
        assert len(data["generated_faults"]) > 0
        
        fault = data["generated_faults"][0]
        assert fault["severity"] in ["medium", "high"]
        assert fault["category"] == "interface_test_failure"
        assert "Interface test failure" in fault["description"]

    def test_interface_test_session_details(self, client: TestClient, test_data):
        """Test retrieving interface test session details"""
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "manual_override",
            "description": "Test session details"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        session_id = response.json()["id"]

        # Add some steps
        step_data = {
            "step_name": "Test Step",
            "action": "Test action",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
            "response_time": 2.0,
            "status": "completed"
        }
        client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step_data)

        # Get session details
        response = client.get(f"/v1/interface-tests/sessions/{session_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == session_id
        assert data["test_type"] == "manual_override"
        assert "steps" in data
        assert len(data["steps"]) == 1
        assert "results" in data

    def test_interface_test_performance(self, client: TestClient, test_data):
        """Test interface test API performance requirements"""
        import time
        
        # Create interface test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "test_type": "manual_override",
            "description": "Performance test"
        }
        
        start_time = time.time()
        response = client.post("/v1/interface-tests/sessions", json=session_data)
        end_time = time.time()
        
        assert response.status_code == 201
        assert (end_time - start_time) < 0.3  # <300ms requirement

        # Test step recording performance
        session_id = response.json()["id"]
        
        step_data = {
            "step_name": "Performance Step",
            "action": "Test performance",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
            "response_time": 2.0,
            "status": "completed"
        }
        
        start_time = time.time()
        response = client.post(f"/v1/interface-tests/sessions/{session_id}/steps", json=step_data)
        end_time = time.time()
        
        assert response.status_code == 201
        assert (end_time - start_time) < 0.2  # <200ms requirement
