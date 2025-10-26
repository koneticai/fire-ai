"""
Load tests for C&E (Cause-and-Effect) Test API
Tests performance requirements: 100 concurrent submissions, p95 < 300ms
"""

import pytest
import uuid
import time
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.main import app
from src.app.database.core import get_db
from src.app.models.buildings import Building
from src.app.models.test_sessions import TestSession
from src.app.models.users import User
from src.app.models.compliance_workflow import ComplianceWorkflow


class TestCEPerformance:
    """Load tests for C&E Test API performance"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    async def test_data(self, db: AsyncSession):
        """Create test data for performance tests"""
        # Create test user
        user = User(
            id=uuid.uuid4(),
            username="perf_engineer@example.com",
            email="perf_engineer@example.com",
            full_name="Performance Engineer",
            is_active=True
        )
        db.add(user)
        await db.commit()

        # Create test building
        building = Building(
            id=uuid.uuid4(),
            name="Performance Test Building",
            address="123 Performance Test Street",
            is_active=True
        )
        db.add(building)
        await db.commit()

        # Create compliance workflow
        workflow = ComplianceWorkflow(
            id=uuid.uuid4(),
            name="Performance C&E Test",
            description="C&E scenario for performance testing",
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
                    }
                ],
                "edges": []
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
            session_name="Performance Test Session",
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

    def test_ce_session_creation_performance(self, client: TestClient, test_data):
        """Test C&E session creation performance with 100 concurrent requests"""
        def create_session():
            session_data = {
                "test_session_id": str(test_data["test_session"].id),
                "building_id": str(test_data["building"].id),
                "workflow_id": str(test_data["workflow"].id),
                "test_type": "stair_pressurization"
            }
            
            start_time = time.time()
            response = client.post("/v1/ce-tests/sessions", json=session_data)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "session_id": response.json().get("id") if response.status_code == 201 else None
            }

        # Run 100 concurrent session creations
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(create_session) for _ in range(100)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Analyze results
        successful_requests = [r for r in results if r["status_code"] == 201]
        response_times = [r["response_time"] for r in successful_requests]
        
        # Performance requirements
        assert len(successful_requests) >= 95  # At least 95% success rate
        assert max(response_times) < 0.3  # p100 < 300ms
        assert sorted(response_times)[int(len(response_times) * 0.95)] < 0.3  # p95 < 300ms
        assert sum(response_times) / len(response_times) < 0.2  # Average < 200ms

    def test_ce_step_recording_performance(self, client: TestClient, test_data):
        """Test C&E step recording performance with concurrent submissions"""
        # Create a test session first
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = response.json()["id"]

        def record_step(step_number):
            step_data = {
                "step_id": f"step{step_number}",
                "action": f"Test Action {step_number}",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
                "actual_time": 2.0,
                "expected_time": 2.0,
                "status": "completed"
            }
            
            start_time = time.time()
            response = client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "step_id": step_data["step_id"]
            }

        # Run 50 concurrent step recordings
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(record_step, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Analyze results
        successful_requests = [r for r in results if r["status_code"] == 201]
        response_times = [r["response_time"] for r in successful_requests]
        
        # Performance requirements
        assert len(successful_requests) >= 48  # At least 96% success rate
        assert max(response_times) < 0.2  # p100 < 200ms
        assert sorted(response_times)[int(len(response_times) * 0.95)] < 0.2  # p95 < 200ms

    def test_ce_deviation_analysis_performance(self, client: TestClient, test_data):
        """Test C&E deviation analysis performance"""
        # Create a test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = response.json()["id"]

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
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=7.0)).isoformat(),
                "actual_time": 7.0,
                "expected_time": 5.0,
                "status": "completed"
            }
        ]

        for step in steps:
            client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step)

        # Test deviation analysis performance
        completion_data = {
            "completed_at": datetime.now().isoformat(),
            "overall_status": "completed_with_deviations"
        }
        
        start_time = time.time()
        response = client.post(f"/v1/ce-tests/sessions/{session_id}/complete", json=completion_data)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 0.2  # <200ms for deviation analysis

    def test_ce_crdt_merge_performance(self, client: TestClient, test_data):
        """Test CRDT merge performance with concurrent submissions"""
        # Create a test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = response.json()["id"]

        def crdt_merge(device_id):
            crdt_data = {
                "document_id": f"mobile-doc-{device_id}",
                "vector_clock": {
                    f"device-{device_id}": 1,
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
                    "device_id": f"device-{device_id}",
                    "platform": "ios",
                    "app_version": "1.0.0"
                }
            }
            
            start_time = time.time()
            response = client.post(f"/v1/ce-tests/sessions/{session_id}/crdt-merge", json=crdt_data)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "device_id": device_id
            }

        # Run 20 concurrent CRDT merges
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(crdt_merge, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Analyze results
        successful_requests = [r for r in results if r["status_code"] == 200]
        response_times = [r["response_time"] for r in successful_requests]
        
        # Performance requirements
        assert len(successful_requests) >= 19  # At least 95% success rate
        assert max(response_times) < 0.5  # p100 < 500ms
        assert sorted(response_times)[int(len(response_times) * 0.95)] < 0.5  # p95 < 500ms

    def test_ce_api_memory_usage(self, client: TestClient, test_data):
        """Test C&E API memory usage under load"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create multiple sessions and steps
        session_ids = []
        for i in range(50):
            session_data = {
                "test_session_id": str(test_data["test_session"].id),
                "building_id": str(test_data["building"].id),
                "workflow_id": str(test_data["workflow"].id),
                "test_type": "stair_pressurization"
            }
            response = client.post("/v1/ce-tests/sessions", json=session_data)
            session_id = response.json()["id"]
            session_ids.append(session_id)

            # Add steps to each session
            for j in range(5):
                step_data = {
                    "step_id": f"step{j}",
                    "action": f"Test Action {j}",
                    "started_at": datetime.now().isoformat(),
                    "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
                    "actual_time": 2.0,
                    "expected_time": 2.0,
                    "status": "completed"
                }
                client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)

        # Check memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB for 250 operations)
        assert memory_increase < 100

    def test_ce_api_database_performance(self, client: TestClient, test_data):
        """Test database performance under C&E API load"""
        # Create multiple sessions and measure database response times
        session_creation_times = []
        step_recording_times = []
        
        for i in range(20):
            # Session creation
            session_data = {
                "test_session_id": str(test_data["test_session"].id),
                "building_id": str(test_data["building"].id),
                "workflow_id": str(test_data["workflow"].id),
                "test_type": "stair_pressurization"
            }
            
            start_time = time.time()
            response = client.post("/v1/ce-tests/sessions", json=session_data)
            end_time = time.time()
            session_creation_times.append(end_time - start_time)
            
            session_id = response.json()["id"]
            
            # Step recording
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
            step_recording_times.append(end_time - start_time)

        # Analyze database performance
        avg_session_creation = sum(session_creation_times) / len(session_creation_times)
        avg_step_recording = sum(step_recording_times) / len(step_recording_times)
        
        # Database operations should be fast
        assert avg_session_creation < 0.1  # <100ms average
        assert avg_step_recording < 0.05  # <50ms average

    def test_ce_api_concurrent_read_write(self, client: TestClient, test_data):
        """Test concurrent read/write operations on C&E API"""
        # Create a test session
        session_data = {
            "test_session_id": str(test_data["test_session"].id),
            "building_id": str(test_data["building"].id),
            "workflow_id": str(test_data["workflow"].id),
            "test_type": "stair_pressurization"
        }
        response = client.post("/v1/ce-tests/sessions", json=session_data)
        session_id = response.json()["id"]

        def write_operation(step_number):
            step_data = {
                "step_id": f"step{step_number}",
                "action": f"Test Action {step_number}",
                "started_at": datetime.now().isoformat(),
                "completed_at": (datetime.now() + timedelta(seconds=2.0)).isoformat(),
                "actual_time": 2.0,
                "expected_time": 2.0,
                "status": "completed"
            }
            
            start_time = time.time()
            response = client.post(f"/v1/ce-tests/sessions/{session_id}/steps", json=step_data)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }

        def read_operation():
            start_time = time.time()
            response = client.get(f"/v1/ce-tests/sessions/{session_id}")
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }

        # Run concurrent read/write operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            # 20 write operations
            write_futures = [executor.submit(write_operation, i) for i in range(20)]
            # 10 read operations
            read_futures = [executor.submit(read_operation) for _ in range(10)]
            
            write_results = [future.result() for future in concurrent.futures.as_completed(write_futures)]
            read_results = [future.result() for future in concurrent.futures.as_completed(read_futures)]

        # Analyze results
        successful_writes = [r for r in write_results if r["status_code"] == 201]
        successful_reads = [r for r in read_results if r["status_code"] == 200]
        
        write_times = [r["response_time"] for r in successful_writes]
        read_times = [r["response_time"] for r in successful_reads]
        
        # Performance requirements
        assert len(successful_writes) >= 19  # At least 95% success rate
        assert len(successful_reads) >= 9   # At least 90% success rate
        assert max(write_times) < 0.2  # p100 < 200ms for writes
        assert max(read_times) < 0.1   # p100 < 100ms for reads

    def test_ce_api_error_handling_under_load(self, client: TestClient, test_data):
        """Test error handling under load conditions"""
        def invalid_request():
            # Send invalid data
            invalid_data = {
                "test_session_id": "invalid-uuid",
                "building_id": "invalid-uuid",
                "workflow_id": "invalid-uuid",
                "test_type": "stair_pressurization"
            }
            
            start_time = time.time()
            response = client.post("/v1/ce-tests/sessions", json=invalid_data)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }

        # Run 50 concurrent invalid requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(invalid_request) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Analyze error handling
        error_responses = [r for r in results if r["status_code"] == 400]
        response_times = [r["response_time"] for r in results]
        
        # Error handling should be fast and consistent
        assert len(error_responses) == 50  # All should return 400
        assert max(response_times) < 0.1  # Error responses should be fast
        assert sum(response_times) / len(response_times) < 0.05  # Average < 50ms
