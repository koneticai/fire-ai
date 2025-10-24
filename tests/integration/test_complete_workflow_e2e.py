"""
End-to-End Integration Test for Complete Workflow
Tests the complete workflow from building creation to report generation
"""

import pytest
import uuid
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.main import app
from src.app.database.core import get_db
from src.app.models.buildings import Building
from src.app.models.test_sessions import TestSession
from src.app.models.users import User
from src.app.models.compliance_workflow import ComplianceWorkflow


class TestCompleteWorkflowE2E:
    """End-to-end integration tests for complete workflow"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    async def test_data(self, db: AsyncSession):
        """Create test data for complete workflow"""
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
            name="Test Building E2E",
            address="123 E2E Test Street",
            is_active=True
        )
        db.add(building)
        await db.commit()

        # Create compliance workflow (C&E scenario)
        workflow = ComplianceWorkflow(
            id=uuid.uuid4(),
            name="E2E Stair Pressurization C&E Test",
            description="End-to-end test workflow",
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
                    },
                    {
                        "id": "step3",
                        "type": "action", 
                        "data": {
                            "name": "Check Pressure",
                            "expected_time": 10.0,
                            "description": "Verify pressure differential achieved"
                        }
                    }
                ],
                "edges": [
                    {
                        "id": "edge1",
                        "from": "step1",
                        "to": "step2",
                        "condition": "success"
                    },
                    {
                        "id": "edge2",
                        "from": "step2",
                        "to": "step3",
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

        return {
            "user": user,
            "building": building,
            "workflow": workflow
        }

    def test_complete_workflow_e2e(self, client: TestClient, test_data):
        """Test complete workflow from building to report generation"""
        
        # Step 1: Create test session
        test_session_data = {
            "building_id": str(test_data["building"].id),
            "session_name": "E2E Test Session",
            "description": "Complete end-to-end test",
            "status": "active"
        }
        
        response = client.post("/v1/tests/sessions", json=test_session_data)
        assert response.status_code == 201
        test_session_id = response.json()["id"]
        
        # Step 2: Download C&E scenario for mobile
        workflow_id = str(test_data["workflow"].id)
        response = client.get(f"/v1/ce-tests/scenarios/{workflow_id}")
        assert response.status_code == 200
        scenario_data = response.json()
        assert scenario_data["id"] == workflow_id
        
        # Step 3: Create C&E test session
        ce_session_data = {
            "test_session_id": test_session_id,
            "building_id": str(test_data["building"].id),
            "workflow_id": workflow_id,
            "test_type": "stair_pressurization"
        }
        
        response = client.post("/v1/ce-tests/sessions", json=ce_session_data)
        assert response.status_code == 201
        ce_session_id = response.json()["id"]
        
        # Step 4: Execute C&E test (mobile simulation)
        ce_steps = [
            {
                "step_id": "step1",
                "action": "Activate Fire Panel",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.5)).isoformat(),
                "actual_time": 2.5,
                "expected_time": 2.0,
                "status": "completed",
                "notes": "Panel activated with slight delay"
            },
            {
                "step_id": "step2",
                "action": "Verify Fan Start",
                "started_at": (datetime.now() + timedelta(seconds=2.5)).isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=8.0)).isoformat(),
                "actual_time": 5.5,
                "expected_time": 5.0,
                "status": "completed",
                "notes": "Fan started within acceptable range"
            },
            {
                "step_id": "step3",
                "action": "Check Pressure",
                "started_at": (datetime.now() + timedelta(seconds=8.0)).isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=18.5)).isoformat(),
                "actual_time": 10.5,
                "expected_time": 10.0,
                "status": "completed",
                "notes": "Pressure achieved with minor delay"
            }
        ]
        
        for step in ce_steps:
            response = client.post(f"/v1/ce-tests/sessions/{ce_session_id}/steps", json=step)
            assert response.status_code == 201
        
        # Step 5: Complete C&E test and analyze deviations
        ce_completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "completed_with_deviations"
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{ce_session_id}/complete", json=ce_completion_data)
        assert response.status_code == 200
        ce_results = response.json()
        assert "deviations" in ce_results
        assert len(ce_results["deviations"]) > 0
        
        # Step 6: Execute interface tests (4 types)
        interface_tests = [
            {
                "test_type": "manual_override",
                "description": "Test manual override functionality"
            },
            {
                "test_type": "alarm_coordination", 
                "description": "Test alarm coordination sequence"
            },
            {
                "test_type": "shutdown_sequence",
                "description": "Test orderly shutdown sequence"
            },
            {
                "test_type": "sprinkler_interface",
                "description": "Test sprinkler interface activation"
            }
        ]
        
        interface_results = []
        for interface_test in interface_tests:
            # Create interface test session
            interface_session_data = {
                "test_session_id": test_session_id,
                "building_id": str(test_data["building"].id),
                "test_type": interface_test["test_type"],
                "description": interface_test["description"]
            }
            
            response = client.post("/v1/interface-tests/sessions", json=interface_session_data)
            assert response.status_code == 201
            interface_session_id = response.json()["id"]
            
            # Execute interface test steps
            interface_steps = [
                {
                    "step_name": f"{interface_test['test_type']}_step1",
                    "action": f"Test {interface_test['test_type']} step 1",
                    "started_at": datetime.now().isoformat(),
                    "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
                    "response_time": 2.0,
                    "status": "completed"
                },
                {
                    "step_name": f"{interface_test['test_type']}_step2",
                    "action": f"Test {interface_test['test_type']} step 2",
                    "started_at": datetime.now().isoformat(),
                    "completed_at": (datetime.now() + timedelta(seconds=3.0)).isoformat(),
                    "response_time": 3.0,
                    "status": "completed"
                }
            ]
            
            for step in interface_steps:
                response = client.post(f"/v1/interface-tests/sessions/{interface_session_id}/steps", json=step)
                assert response.status_code == 201
            
            # Complete interface test
            interface_completion_data = {
                "completed_at": datetime.now().isoformat(),
                "overall_status": "passed"
            }
            
            response = client.post(f"/v1/interface-tests/sessions/{interface_session_id}/complete", json=interface_completion_data)
            assert response.status_code == 200
            interface_results.append(response.json())
        
        # Step 7: Generate comprehensive report
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": test_session_id,
            "report_type": "comprehensive",
            "include_ce_tests": True,
            "include_interface_tests": True,
            "include_trends": True,
            "include_calibration_table": True,
            "include_compliance_statement": True,
            "engineer_id": str(test_data["user"].id)
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        assert response.status_code == 201
        report_data_response = response.json()
        report_id = report_data_response["report_id"]
        
        # Step 8: Verify report includes all data
        # Check report status
        response = client.get(f"/v1/reports/{report_id}/status")
        assert response.status_code == 200
        report_status = response.json()
        assert "status" in report_status
        
        # Step 9: Verify data flows correctly between components
        # Check C&E test session details
        response = client.get(f"/v1/ce-tests/sessions/{ce_session_id}")
        assert response.status_code == 200
        ce_session_details = response.json()
        assert len(ce_session_details["steps"]) == 3
        assert len(ce_session_details["deviations"]) > 0
        
        # Check interface test sessions
        for i, interface_test in enumerate(interface_tests):
            # Get interface test session details
            response = client.get(f"/v1/interface-tests/sessions")
            assert response.status_code == 200
            interface_sessions = response.json()
            assert len(interface_sessions) >= 4
        
        # Step 10: Verify performance within acceptable limits
        # Test API response times
        start_time = time.time()
        response = client.get(f"/v1/ce-tests/sessions/{ce_session_id}")
        end_time = time.time()
        assert (end_time - start_time) < 0.3  # <300ms
        
        start_time = time.time()
        response = client.get(f"/v1/interface-tests/sessions")
        end_time = time.time()
        assert (end_time - start_time) < 0.3  # <300ms
        
        # Test trend analysis performance
        start_time = time.time()
        response = client.get(f"/v1/reports/{test_data['building'].id}/trends")
        end_time = time.time()
        assert (end_time - start_time) < 5.0  # <5s

    def test_workflow_with_critical_deviations(self, client: TestClient, test_data):
        """Test workflow with critical deviations that generate faults"""
        
        # Create test session
        test_session_data = {
            "building_id": str(test_data["building"].id),
            "session_name": "Critical Deviation Test",
            "description": "Test with critical deviations",
            "status": "active"
        }
        
        response = client.post("/v1/tests/sessions", json=test_session_data)
        test_session_id = response.json()["id"]
        
        # Create C&E test session
        ce_session_data = {
            "test_session_id": test_session_id,
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        
        response = client.post("/v1/ce-tests/sessions", json=ce_session_data)
        ce_session_id = response.json()["id"]
        
        # Execute C&E test with critical deviation (>10 seconds)
        critical_step = {
            "step_id": "step1",
            "action": "Activate Fire Panel",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=15.0)).isoformat(),
            "actual_time": 15.0,
            "expected_time": 2.0,
            "status": "completed",
            "notes": "Critical delay - panel took 15 seconds to activate"
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{ce_session_id}/steps", json=critical_step)
        assert response.status_code == 201
        
        # Complete C&E test
        ce_completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "completed_with_critical_deviations"
        }
        
        response = client.post(f"/v1/ce-tests/sessions/{ce_session_id}/complete", json=ce_completion_data)
        assert response.status_code == 200
        ce_results = response.json()
        
        # Verify critical deviation was detected and fault generated
        assert "deviations" in ce_results
        critical_deviation = next(
            (d for d in ce_results["deviations"] if d["severity"] == "critical"), 
            None
        )
        assert critical_deviation is not None
        assert critical_deviation["deviation_seconds"] > 10.0
        
        # Verify fault was auto-generated
        assert "generated_faults" in ce_results
        assert len(ce_results["generated_faults"]) > 0
        
        fault = ce_results["generated_faults"][0]
        assert fault["severity"] == "critical"
        assert fault["category"] == "ce_test_deviation"

    def test_workflow_with_interface_test_failures(self, client: TestClient, test_data):
        """Test workflow with interface test failures"""
        
        # Create test session
        test_session_data = {
            "building_id": str(test_data["building"].id),
            "session_name": "Interface Failure Test",
            "description": "Test with interface failures",
            "status": "active"
        }
        
        response = client.post("/v1/tests/sessions", json=test_session_data)
        test_session_id = response.json()["id"]
        
        # Create interface test session with failure
        interface_session_data = {
            "test_session_id": test_session_id,
            "building_id": str(test_data["building"].id),
            "test_type": "manual_override",
            "description": "Test with timing failure"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=interface_session_data)
        interface_session_id = response.json()["id"]
        
        # Execute interface test step that fails timing (>3s for manual override)
        failed_step = {
            "step_name": "Failed Override",
            "action": "Test override that fails",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=5.0)).isoformat(),
            "response_time": 5.0,  # >3s threshold
            "status": "completed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{interface_session_id}/steps", json=failed_step)
        assert response.status_code == 201
        step_result = response.json()
        assert step_result["validation_status"] == "failed"
        
        # Complete interface test
        interface_completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "failed"
        }
        
        response = client.post(f"/v1/interface-tests/sessions/{interface_session_id}/complete", json=interface_completion_data)
        assert response.status_code == 200
        interface_results = response.json()
        
        # Verify fault was generated for interface failure
        assert "generated_faults" in interface_results
        assert len(interface_results["generated_faults"]) > 0
        
        fault = interface_results["generated_faults"][0]
        assert fault["severity"] in ["medium", "high"]
        assert fault["category"] == "interface_test_failure"

    def test_workflow_data_consistency(self, client: TestClient, test_data):
        """Test data consistency across the complete workflow"""
        
        # Create test session
        test_session_data = {
            "building_id": str(test_data["building"].id),
            "session_name": "Data Consistency Test",
            "description": "Test data consistency",
            "status": "active"
        }
        
        response = client.post("/v1/tests/sessions", json=test_session_data)
        test_session_id = response.json()["id"]
        
        # Create C&E test session
        ce_session_data = {
            "test_session_id": test_session_id,
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        
        response = client.post("/v1/ce-tests/sessions", json=ce_session_data)
        ce_session_id = response.json()["id"]
        
        # Execute C&E test
        ce_step = {
            "step_id": "step1",
            "action": "Activate Fire Panel",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
            "actual_time": 2.0,
            "expected_time": 2.0,
            "status": "completed"
        }
        
        client.post(f"/v1/ce-tests/sessions/{ce_session_id}/steps", json=ce_step)
        
        # Create interface test session
        interface_session_data = {
            "test_session_id": test_session_id,
            "building_id": str(test_data["building"].id),
            "test_type": "manual_override",
            "description": "Data consistency test"
        }
        
        response = client.post("/v1/interface-tests/sessions", json=interface_session_data)
        interface_session_id = response.json()["id"]
        
        # Execute interface test
        interface_step = {
            "step_name": "Consistency Test",
            "action": "Test data consistency",
            "started_at": datetime.now().isoformat(),
            "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
            "response_time": 2.0,
            "status": "completed"
        }
        
        client.post(f"/v1/interface-tests/sessions/{interface_session_id}/steps", json=interface_step)
        
        # Generate report
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": test_session_id,
            "report_type": "comprehensive",
            "include_ce_tests": True,
            "include_interface_tests": True
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        report_id = response.json()["report_id"]
        
        # Verify data consistency
        # Check that all test sessions are linked to the same building
        response = client.get(f"/v1/buildings/{test_data['building'].id}")
        building_data = response.json()
        assert building_data["id"] == str(test_data["building"].id")
        
        # Check that C&E and interface tests are linked to the same test session
        response = client.get(f"/v1/ce-tests/sessions/{ce_session_id}")
        ce_data = response.json()
        assert ce_data["test_session_id"] == test_session_id
        
        response = client.get(f"/v1/interface-tests/sessions/{interface_session_id}")
        interface_data = response.json()
        assert interface_data["test_session_id"] == test_session_id
        
        # Check that report references all components
        response = client.get(f"/v1/reports/{report_id}/status")
        report_status = response.json()
        assert report_status["report_id"] == report_id
