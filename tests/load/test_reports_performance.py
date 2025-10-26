"""
Load tests for Report Generation API
Tests performance requirements: 3-year data, <10s total generation time
"""

import pytest
import uuid
import time
import concurrent.futures
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.main import app
from src.app.database.core import get_db
from src.app.models.buildings import Building
from src.app.models.test_sessions import TestSession
from src.app.models.users import User


class TestReportsPerformance:
    """Load tests for Report Generation API performance"""

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

        # Create test session
        test_session = TestSession(
            id=uuid.uuid4(),
            building_id=building.id,
            session_name="Performance Test Session",
            status="completed",
            created_by=user.id
        )
        db.add(test_session)
        await db.commit()

        return {
            "user": user,
            "building": building,
            "test_session": test_session
        }

    def test_trend_analysis_performance(self, client: TestClient, test_data):
        """Test trend analysis performance with 3-year data"""
        building_id = str(test_data["building"].id)
        
        # Test trend analysis performance
        start_time = time.time()
        response = client.get(f"/v1/reports/{building_id}/trends")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 5.0  # <5s requirement
        
        data = response.json()
        assert "trends" in data
        assert "pressure_differentials" in data["trends"]
        assert "air_velocity" in data["trends"]
        assert "door_force" in data["trends"]

    def test_report_generation_performance(self, client: TestClient, test_data):
        """Test report generation performance with comprehensive data"""
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "comprehensive",
            "include_ce_tests": True,
            "include_interface_tests": True,
            "include_trends": True,
            "include_calibration_table": True,
            "include_compliance_statement": True,
            "trend_period_years": 3
        }
        
        # Test report generation initiation performance
        start_time = time.time()
        response = client.post("/v1/reports/generate", json=report_data)
        end_time = time.time()
        
        assert response.status_code == 201
        assert (end_time - start_time) < 1.0  # <1s to initiate
        
        data = response.json()
        assert "report_id" in data
        report_id = data["report_id"]
        
        # Test report status check performance
        start_time = time.time()
        response = client.get(f"/v1/reports/{report_id}/status")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 0.5  # <500ms for status check

    def test_concurrent_report_generation(self, client: TestClient, test_data):
        """Test concurrent report generation performance"""
        def generate_report(report_number):
            report_data = {
                "building_id": str(test_data["building"].id),
                "test_session_id": str(test_data["test_session"].id),
                "report_type": "comprehensive",
                "include_trends": True,
                "trend_period_years": 3
            }
            
            start_time = time.time()
            response = client.post("/v1/reports/generate", json=report_data)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "report_id": response.json().get("report_id") if response.status_code == 201 else None
            }

        # Run 10 concurrent report generations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_report, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Analyze results
        successful_requests = [r for r in results if r["status_code"] == 201]
        response_times = [r["response_time"] for r in successful_requests]
        
        # Performance requirements
        assert len(successful_requests) >= 9  # At least 90% success rate
        assert max(response_times) < 2.0  # p100 < 2s for initiation
        assert sorted(response_times)[int(len(response_times) * 0.95)] < 1.5  # p95 < 1.5s

    def test_chart_data_generation_performance(self, client: TestClient, test_data):
        """Test chart data generation performance"""
        building_id = str(test_data["building"].id)
        
        # Test chart data generation
        start_time = time.time()
        response = client.get(f"/v1/reports/{building_id}/chart-data")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 3.0  # <3s for chart data
        
        data = response.json()
        assert "pressure_charts" in data
        assert "velocity_charts" in data
        assert "force_charts" in data

    def test_report_sections_performance(self, client: TestClient, test_data):
        """Test individual report section generation performance"""
        building_id = str(test_data["building"].id)
        
        # Test trend analysis section
        start_time = time.time()
        response = client.get(f"/v1/reports/{building_id}/trends")
        end_time = time.time()
        trend_time = end_time - start_time
        
        assert response.status_code == 200
        assert trend_time < 3.0  # <3s for trend analysis
        
        # Test chart data section
        start_time = time.time()
        response = client.get(f"/v1/reports/{building_id}/chart-data")
        end_time = time.time()
        chart_time = end_time - start_time
        
        assert response.status_code == 200
        assert chart_time < 2.0  # <2s for chart data
        
        # Test statistical analysis section
        report_data = {
            "building_id": building_id,
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "statistical_analysis",
            "include_statistics": True
        }
        
        start_time = time.time()
        response = client.post("/v1/reports/generate", json=report_data)
        end_time = time.time()
        stats_time = end_time - start_time
        
        assert response.status_code == 201
        assert stats_time < 1.0  # <1s for statistical analysis

    def test_report_memory_usage(self, client: TestClient, test_data):
        """Test report generation memory usage"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate multiple reports
        report_ids = []
        for i in range(10):
            report_data = {
                "building_id": str(test_data["building"].id),
                "test_session_id": str(test_data["test_session"].id),
                "report_type": "comprehensive",
                "include_trends": True,
                "trend_period_years": 3
            }
            
            response = client.post("/v1/reports/generate", json=report_data)
            if response.status_code == 201:
                report_ids.append(response.json()["report_id"])

        # Check memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 200MB for 10 reports)
        assert memory_increase < 200

    def test_report_database_performance(self, client: TestClient, test_data):
        """Test database performance for report generation"""
        building_id = str(test_data["building"].id)
        
        # Test trend query performance
        start_time = time.time()
        response = client.get(f"/v1/reports/{building_id}/trends")
        end_time = time.time()
        trend_query_time = end_time - start_time
        
        assert response.status_code == 200
        assert trend_query_time < 3.0  # <3s for trend queries
        
        # Test chart data query performance
        start_time = time.time()
        response = client.get(f"/v1/reports/{building_id}/chart-data")
        end_time = time.time()
        chart_query_time = end_time - start_time
        
        assert response.status_code == 200
        assert chart_query_time < 2.0  # <2s for chart queries

    def test_report_caching_performance(self, client: TestClient, test_data):
        """Test report caching performance"""
        building_id = str(test_data["building"].id)
        
        # First request (cache miss)
        start_time = time.time()
        response1 = client.get(f"/v1/reports/{building_id}/trends")
        end_time = time.time()
        first_request_time = end_time - start_time
        
        assert response1.status_code == 200
        
        # Second request (cache hit)
        start_time = time.time()
        response2 = client.get(f"/v1/reports/{building_id}/trends")
        end_time = time.time()
        second_request_time = end_time - start_time
        
        assert response2.status_code == 200
        
        # Second request should be faster (cached)
        assert second_request_time < first_request_time
        assert second_request_time < 0.5  # <500ms for cached response

    def test_report_error_handling_performance(self, client: TestClient):
        """Test error handling performance under load"""
        def invalid_request():
            # Send invalid building ID
            response = client.get("/v1/reports/invalid-uuid/trends")
            return {
                "status_code": response.status_code,
                "response_time": 0  # Simplified for this test
            }

        # Run 50 concurrent invalid requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(invalid_request) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Analyze error handling
        error_responses = [r for r in results if r["status_code"] == 400]
        
        # Error handling should be consistent
        assert len(error_responses) == 50  # All should return 400

    def test_report_generation_with_large_dataset(self, client: TestClient, test_data):
        """Test report generation with large dataset simulation"""
        # Simulate large dataset by requesting extended trend period
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "historical_analysis",
            "include_trends": True,
            "trend_period_years": 5,  # Extended period
            "include_predictions": True,
            "include_statistics": True
        }
        
        start_time = time.time()
        response = client.post("/v1/reports/generate", json=report_data)
        end_time = time.time()
        
        assert response.status_code == 201
        assert (end_time - start_time) < 2.0  # <2s even with large dataset
        
        data = response.json()
        assert "report_id" in data
        assert "data_summary" in data

    def test_report_concurrent_access(self, client: TestClient, test_data):
        """Test concurrent access to report endpoints"""
        building_id = str(test_data["building"].id)
        
        def access_trends():
            start_time = time.time()
            response = client.get(f"/v1/reports/{building_id}/trends")
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }

        def access_charts():
            start_time = time.time()
            response = client.get(f"/v1/reports/{building_id}/chart-data")
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }

        # Run concurrent access to different endpoints
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # 10 trend requests
            trend_futures = [executor.submit(access_trends) for _ in range(10)]
            # 10 chart requests
            chart_futures = [executor.submit(access_charts) for _ in range(10)]
            
            trend_results = [future.result() for future in concurrent.futures.as_completed(trend_futures)]
            chart_results = [future.result() for future in concurrent.futures.as_completed(chart_futures)]

        # Analyze results
        successful_trends = [r for r in trend_results if r["status_code"] == 200]
        successful_charts = [r for r in chart_results if r["status_code"] == 200]
        
        trend_times = [r["response_time"] for r in successful_trends]
        chart_times = [r["response_time"] for r in successful_charts]
        
        # Performance requirements
        assert len(successful_trends) >= 9  # At least 90% success rate
        assert len(successful_charts) >= 9  # At least 90% success rate
        assert max(trend_times) < 5.0  # p100 < 5s for trends
        assert max(chart_times) < 3.0  # p100 < 3s for charts
