"""
Integration tests for C&E (Cause-and-Effect) Test API
Tests the complete C&E test workflow from scenario download to deviation analysis
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.main import app
from src.app.database.core import get_db
from src.app.models.ce_test import CETestSession, CETestStep, CETestDeviation
from src.app.models.compliance_workflow import ComplianceWorkflow
from src.app.models.buildings import Building
from src.app.models.test_sessions import TestSession
from src.app.models.users import User


class TestCEIntegration:
    """Integration tests for C&E test API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    async def test_data(self, db: AsyncSession):
        """Create test data for C&E tests"""
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

        # Create compliance workflow (C&E scenario)
        workflow = ComplianceWorkflow(
            id=uuid.uuid4(),
            name="Stair Pressurization C&E Test",
            description="Cause-and-effect test for stair pressurization system",
            compliance_standard="AS1851-2012",
            workflow_definition={
                "nodes": [
                    {
                        "id": "step1",
                        "type": "action",
                        "data": {
                            "name": "Activate Fire Panel",
                            "expected_time": 2.0,
                            "description": "Press fire panel activation button"
                        }
                    },
                    {
                        "id": "step2", 
                        "type": "action",
                        "data": {
                            "name": "Verify Fan Start",
                            "expected_time": 5.0,
                            "description": "Confirm supply fan starts within 5 seconds"
                        }
                    }
                ],
                "edges": [
                    {
                        "id": "edge1",
                        "from": "step1",
                        "to": "step2",
                        "condition": "success"
                    }
                ]
            },
            status="active",
            is_template=True,
            created_by=user.id
        )
        db.add(workflow)
        await db.commit()

        # Create test session
        test_session = TestSession(
            id=uuid.uuid4(),
            building_id=building.id,
            session_name="C&E Test Session",
            status="active",
            created_by=user.id
        )
        db.add(test_session)
        await db.commit()

        return {
            "user": user,
            "building": building,
            "workflow": workflow,
            "test_session": test_session
        }

    def test_ce_scenario_download(self, client: TestClient, test_data):
        """Test downloading C&E scenario for offline use"""
        workflow_id = str(test_data["workflow"].id)
        
        response = client.get(f"/v1/ce-tests/scenarios/{workflow_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == workflow_id
        assert data["name"] == "Stair Pressurization C&E Test"
        assert "workflow_definition" in data
        assert len(data["workflow_definition"]["nodes"]) == 2
        assert len(data["workflow_definition"]["edges"]) == 1

    def test_ce_test_session_creation(self, client: TestClient, test_data):
        """Test creating C&E test session"""
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["test_session_id"] == str(test_data["test_session"].id)
        assert data["building_id"] == str(test_data["building"].id)
        assert data["workflow_id"] == str(test_data["workflow"].id)
        assert data["status"] == "active"

    def test_ce_test_step_recording(self, client: TestClient, test_data):
        """Test recording C&E test steps with timing"""
        # First create a test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Record test step
        step_data = {
            "step_id": "step1",
            "action": "Activate Fire Panel",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.5)).isoformat(),
            "actual_time": 2.5,
            "expected_time": 2.0,
            "status": "completed",
            "notes": "Panel activated successfully"
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["step_id"] == "step1"
        assert data["actual_time"] == 2.5
        assert data["expected_time"] == 2.0
        assert data["status"] == "completed"

    def test_ce_deviation_analysis(self, client: TestClient, test_data):
        """Test deviation analysis and fault generation"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Record steps with deviations
        steps = [
            {
                "step_id": "step1",
                "action": "Activate Fire Panel",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.5)).isoformat(),
                "actual_time": 2.5,
                "expected_time": 2.0,
                "status": "completed"
            },
            {
                "step_id": "step2",
                "action": "Verify Fan Start",
                "started_at": (datetime.now() + timedelta(seconds=2.5)).isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=12.0)).isoformat(),
                "actual_time": 9.5,  # 4.5 seconds late
                "expected_time": 5.0,
                "status": "completed"
            }
        ]

        for step in steps:
            client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step)

        # Complete test and analyze deviations
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "completed_with_deviations"
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/complete", json=completion_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "deviations" in data
        assert len(data["deviations"]) > 0
        
        # Check that critical deviation was detected
        critical_deviation = next(
            (d for d in data["deviations"] if d["severity"] == "high"), 
            None
        )
        assert critical_deviation is not None
        assert critical_deviation["deviation_seconds"] > 4.0

    def test_ce_test_session_details(self, client: TestClient, test_data):
        """Test retrieving C&E test session details"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Get session details
        response = client.get(f"/v1/ce-tests/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == session_id
        assert "steps" in data
        assert "deviations" in data
        assert "workflow" in data

    def test_ce_crdt_merge_simulation(self, client: TestClient, test_data):
        """Test CRDT merge for multiple technicians testing same system"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Simulate two technicians submitting results
        technician1_results = {
            "steps": [
                {
                    "step_id": "step1",
                    "actual_time": 2.0,
                    "expected_time": 2.0,
                    "status": "completed"
                }
            ],
            "crdt_data": {
                "vector_clock": {"tech1": 1},
                "changes": [{"type": "step_completed", "step_id": "step1"}]
            }
        }

        technician2_results = {
            "steps": [
                {
                    "step_id": "step2",
                    "actual_time": 5.5,
                    "expected_time": 5.0,
                    "status": "completed"
                }
            ],
            "crdt_data": {
                "vector_clock": {"tech2": 1},
                "changes": [{"type": "step_completed", "step_id": "step2"}]
            }
        }

        # Submit both results
        response1 = client.post(f"/v1/ce-tests/sessions/{session_id}/crdt-merge", json=technician1_results)
        response2 = client.post(f"/v1/ce-tests/sessions/{session_id}/crdt-merge", json=technician2_results)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify merged results
        session_response = client.get(f"/v1/ce-tests/sessions/{session_id}")
        session_data = session_response.json()
        
        assert len(session_data["steps"]) == 2
        assert any(step["step_id"] == "step1" for step in session_data["steps"])
        assert any(step["step_id"] == "step2" for step in session_data["steps"])

    def test_ce_automatic_fault_generation(self, client: TestClient, test_data):
        """Test automatic fault generation for critical deviations"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Record step with critical deviation (>10 seconds)
        step_data = {
            "step_id": "step1",
            "action": "Activate Fire Panel",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=15.0)).isoformat(),
            "actual_time": 15.0,
            "expected_time": 2.0,
            "status": "completed"
        }
        
        client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)

        # Complete test
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "completed_with_deviations"
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/complete", json=completion_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that fault was auto-generated
        assert "generated_faults" in data
        assert len(data["generated_faults"]) > 0
        
        fault = data["generated_faults"][0]
        assert fault["severity"] == "critical"
        assert fault["category"] == "ce_test_deviation"
        assert "C&E test deviation" in fault["description"]

    def test_ce_evidence_linking(self, client: TestClient, test_data):
        """Test linking evidence to C&E test steps"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Record step with evidence
        step_data = {
            "step_id": "step1",
            "action": "Activate Fire Panel",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
            "actual_time": 2.0,
            "expected_time": 2.0,
            "status": "completed",
            "evidence_ids": ["evidence-123", "evidence-456"]
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "evidence_ids" in data
        assert len(data["evidence_ids"]) == 2
        assert "evidence-123" in data["evidence_ids"]
        assert "evidence-456" in data["evidence_ids"]

    def test_ce_performance_requirements(self, client: TestClient, test_data):
        """Test that C&E API meets performance requirements"""
        import time
        
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        
        start_time = time.time()
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        end_time = time.time()
        
        assert response.status_code == 201
        assert (end_time - start_time) < 0.3  # <300ms requirement

        # Test deviation analysis performance
        session_id = response.json()["id"]
        
        step_data = {
            "step_id": "step1",
            "action": "Activate Fire Panel",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
            "actual_time": 2.0,
            "expected_time": 2.0,
            "status": "completed"
        }
        
        start_time = time.time()
        client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)
        end_time = time.time()
        
        assert (end_time - start_time) < 0.2  # <200ms requirement
