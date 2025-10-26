"""
Integration tests for Mobile API endpoints
Tests the API endpoints that the mobile app would use for C&E test execution
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.main import app
from src.app.database.core import get_db
from src.app.models.buildings import Building
from src.app.models.test_sessions import TestSession
from src.app.models.users import User
from src.app.models.compliance_workflow import ComplianceWorkflow


class TestMobileAPIIntegration:
    """Integration tests for Mobile API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    async def test_data(self, db: AsyncSession):
        """Create test data for mobile API tests"""
        # Create test user
        user = User(
            id=uuid.uuid4(),
            username="mobile_engineer@example.com",
            email="mobile_engineer@example.com",
            full_name="Mobile Engineer",
            is_active=True
        )
        db.add(user)
        await db.commit()

        # Create test building
        building = Building(
            id=uuid.uuid4(),
            name="Mobile Test Building",
            address="123 Mobile Test Street",
            is_active=True
        )
        db.add(building)
        await db.commit()

        # Create compliance workflow (C&E scenario)
        workflow = ComplianceWorkflow(
            id=uuid.uuid4(),
            name="Mobile C&E Test Scenario",
            description="C&E scenario for mobile testing",
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
            session_name="Mobile Test Session",
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

    def test_mobile_scenario_download(self, client: TestClient, test_data):
        """Test mobile app downloading C&E scenario for offline use"""
        workflow_id = str(test_data["workflow"].id)
        
        response = client.get(f"/v1/ce-tests/scenarios/{workflow_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify scenario structure for mobile consumption
        assert data["id"] == workflow_id
        assert data["name"] == "Mobile C&E Test Scenario"
        assert "workflow_definition" in data
        
        # Check workflow definition structure
        workflow_def = data["workflow_definition"]
        assert "nodes" in workflow_def
        assert "edges" in workflow_def
        assert len(workflow_def["nodes"]) == 2
        assert len(workflow_def["edges"]) == 1
        
        # Verify node structure for mobile
        for node in workflow_def["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "data" in node
            assert "name" in node["data"]
            assert "expected_time" in node["data"]
            assert "description" in node["data"]

    def test_mobile_test_session_creation(self, client: TestClient, test_data):
        """Test mobile app creating C&E test session"""
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization",
            "device_info": {
                "device_id": "mobile-device-123",
                "platform": "ios",
                "app_version": "1.0.0"
            }
        }
        
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["test_session_id"] == str(test_data["test_session"].id)
        assert data["building_id"] == str(test_data["building"].id)
        assert data["workflow_id"] == str(test_data["workflow"].id)
        assert data["status"] == "active"
        assert "created_at" in data

    def test_mobile_step_recording(self, client: TestClient, test_data):
        """Test mobile app recording C&E test steps with timing"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Record test step with mobile-specific data
        step_data = {
            "step_id": "step1",
            "action": "Activate Fire Panel",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.5)).isoformat(),
            "actual_time": 2.5,
            "expected_time": 2.0,
            "status": "completed",
            "notes": "Panel activated successfully",
            "device_timestamp": datetime.now().isoformat(),
            "location": {
                "latitude": -33.8688,
                "longitude": 151.2093,
                "accuracy": 5.0
            },
            "evidence_ids": ["photo-123", "video-456"]
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["step_id"] == "step1"
        assert data["actual_time"] == 2.5
        assert data["expected_time"] == 2.0
        assert data["status"] == "completed"
        assert "deviation_seconds" in data
        assert data["deviation_seconds"] == 0.5

    def test_mobile_offline_sync(self, client: TestClient, test_data):
        """Test mobile app syncing offline test results"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Simulate offline test execution with multiple steps
        offline_steps = [
            {
                "step_id": "step1",
                "action": "Activate Fire Panel",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
                "actual_time": 2.0,
                "expected_time": 2.0,
                "status": "completed",
                "offline_timestamp": datetime.now().isoformat()
            },
            {
                "step_id": "step2",
                "action": "Verify Fan Start",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=5.5)).isoformat(),
                "actual_time": 5.5,
                "expected_time": 5.0,
                "status": "completed",
                "offline_timestamp": datetime.now().isoformat()
            }
        ]

        # Sync offline steps
        sync_data = {
            "steps": offline_steps,
            "sync_timestamp": datetime.now().isoformat(),
            "device_id": "mobile-device-123"
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/sync", json=sync_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "synced_steps" in data
        assert len(data["synced_steps"]) == 2
        assert "conflicts" in data
        assert len(data["conflicts"]) == 0  # No conflicts in this test

    def test_mobile_crdt_merge(self, client: TestClient, test_data):
        """Test mobile app CRDT merge for conflict resolution"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Simulate CRDT document from mobile
        crdt_data = {
            "document_id": f"mobile-doc-{session_id}",
            "vector_clock": {
                "mobile-device-123": 1,
                "server": 0
            },
            "changes": [
                {
                    "type": "step_completed",
                    "step_id": "step1",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "actual_time": 2.0,
                        "status": "completed"
                    }
                }
            ],
            "device_info": {
                "device_id": "mobile-device-123",
                "platform": "ios",
                "app_version": "1.0.0"
            }
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/crdt-merge", json=crdt_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "merged_document" in data
        assert "conflicts_resolved" in data
        assert "vector_clock" in data["merged_document"]
        assert "mobile-device-123" in data["merged_document"]["vector_clock"]

    def test_mobile_evidence_upload(self, client: TestClient, test_data):
        """Test mobile app uploading evidence with device attestation"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Upload evidence with device attestation
        evidence_data = {
            "step_id": "step1",
            "evidence_type": "photo",
            "filename": "fire_panel_activation.jpg",
            "mime_type": "image/jpeg",
            "file_size": 1024000,
            "device_attestation": {
                "device_id": "mobile-device-123",
                "platform": "ios",
                "attestation_token": "device-attestation-token-123",
                "timestamp": datetime.now().isoformat()
            },
            "location": {
                "latitude": -33.8688,
                "longitude": 151.2093,
                "accuracy": 5.0
            }
        }
        
        # Simulate file upload (in real scenario, this would be multipart/form-data)
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/evidence", json=evidence_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "evidence_id" in data
        assert data["step_id"] == "step1"
        assert data["evidence_type"] == "photo"
        assert "device_attestation" in data
        assert data["device_attestation"]["device_id"] == "mobile-device-123"

    def test_mobile_test_completion(self, client: TestClient, test_data):
        """Test mobile app completing C&E test and getting results"""
        # Create test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        session_response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = session_response.json()["id"]

        # Record some steps
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
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=7.0)).isoformat(),
                "actual_time": 7.0,
                "expected_time": 5.0,
                "status": "completed"
            }
        ]

        for step in steps:
            client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step)

        # Complete test
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "completed_with_deviations",
            "device_info": {
                "device_id": "mobile-device-123",
                "platform": "ios",
                "app_version": "1.0.0"
            }
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/complete", json=completion_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "deviations" in data
        assert "generated_faults" in data
        assert "summary" in data
        
        # Check summary for mobile display
        summary = data["summary"]
        assert "total_steps" in summary
        assert "completed_steps" in summary
        assert "deviations_count" in summary
        assert "overall_status" in summary

    def test_mobile_api_performance(self, client: TestClient, test_data):
        """Test mobile API performance requirements"""
        import time
        
        # Test scenario download performance
        workflow_id = str(test_data["workflow"].id)
        
        start_time = time.time()
        response = client.get(f"/v1/ce-tests/scenarios/{workflow_id}")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 0.5  # <500ms for scenario download

        # Test session creation performance
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": workflow_id,
            "test_type": "stair_pressurization"
        }
        
        start_time = time.time()
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        end_time = time.time()
        
        assert response.status_code == 201
        assert (end_time - start_time) < 0.3  # <300ms for session creation

        # Test step recording performance
        session_id = response.json()["id"]
        step_data = {
            "step_id": "step1",
            "action": "Test Action",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
            "actual_time": 2.0,
            "expected_time": 2.0,
            "status": "completed"
        }
        
        start_time = time.time()
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)
        end_time = time.time()
        
        assert response.status_code == 201
        assert (end_time - start_time) < 0.2  # <200ms for step recording

    def test_mobile_error_handling(self, client: TestClient):
        """Test mobile API error handling"""
        # Test invalid scenario ID
        response = client.get("/v1/ce-tests/scenarios/invalid-uuid")
        assert response.status_code == 400

        # Test invalid session creation
        invalid_session_data = {
            "test_session_id": "invalid-uuid",
            "building_id": "invalid-uuid",
            "workflow_id": "invalid-uuid",
            "test_type": "stair_pressurization"
        }
        
        response = client.post("/v1/ce-tests/sessions", json=invalid_session_data)
        assert response.status_code == 400

        # Test invalid step recording
        response = client.post("/v1/ce-tests/sessions/invalid-uuid/steps", json={})
        assert response.status_code == 400

    def test_mobile_connectivity_simulation(self, client: TestClient, test_data):
        """Test mobile app connectivity scenarios"""
        # Test scenario download when offline (simulated)
        workflow_id = str(test_data["workflow"].id)
        
        # First download scenario (online)
        response = client.get(f"/v1/ce-tests/scenarios/{workflow_id}")
        assert response.status_code == 200
        scenario = response.json()
        
        # Verify scenario is suitable for offline use
        assert "workflow_definition" in scenario
        assert "nodes" in scenario["workflow_definition"]
        assert "edges" in scenario["workflow_definition"]
        
        # Test session creation with device info
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": workflow_id,
            "test_type": "stair_pressurization",
            "device_info": {
                "device_id": "mobile-device-123",
                "platform": "ios",
                "app_version": "1.0.0",
                "offline_capable": True
            }
        }
        
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        assert response.status_code == 201
        session_data_response = response.json()
        
        # Verify session is ready for offline execution
        assert session_data_response["status"] == "active"
        assert "offline_sync_ready" in session_data_response
