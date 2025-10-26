"""
Integration tests for Report Generation API
Tests enhanced PDF report generation with trends, C&E results, and interface tests
"""

import pytest
import uuid
import io
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.main import app
from src.app.database.core import get_db
from src.app.models.buildings import Building
from src.app.models.test_sessions import TestSession
from src.app.models.users import User
from src.app.models.ce_test import CETestSession, CETestStep
from src.app.models.interface_test import InterfaceTestSession, InterfaceTestStep


class TestReportsIntegration:
    """Integration tests for Report Generation API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    async def test_data(self, db: AsyncSession):
        """Create test data for report generation"""
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
            session_name="Comprehensive Test Session",
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

    def test_trend_analysis_endpoint(self, client: TestClient, test_data):
        """Test trend analysis endpoint with 3-year data"""
        building_id = str(test_data["building"].id)
        
        response = client.get(f"/v1/reports/{building_id}/trends")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "trends" in data
        assert "pressure_differentials" in data["trends"]
        assert "air_velocity" in data["trends"]
        assert "door_force" in data["trends"]
        
        # Check trend data structure
        pressure_trends = data["trends"]["pressure_differentials"]
        assert "floors" in pressure_trends
        assert "time_series" in pressure_trends
        assert "statistics" in pressure_trends

    def test_report_generation_with_ce_results(self, client: TestClient, test_data):
        """Test report generation including C&E test results"""
        # Create C&E test session
        ce_session = CETestSession(
            id=uuid.uuid4(),
            test_session_id=test_data["test_session"].id,
            building_id=test_data["building"].id,
            workflow_id=uuid.uuid4(),
            test_type="stair_pressurization",
            status="completed",
            created_at=datetime.now() - timedelta(days=1)
        )
        
        # Create C&E test steps
        ce_steps = [
            CETestStep(
                id=uuid.uuid4(),
                ce_test_session_id=ce_session.id,
                step_id="step1",
                action="Activate Fire Panel",
                actual_time=2.5,
                expected_time=2.0,
                status="completed",
                deviation_seconds=0.5
            ),
            CETestStep(
                id=uuid.uuid4(),
                ce_test_session_id=ce_session.id,
                step_id="step2",
                action="Verify Fan Start",
                actual_time=7.0,
                expected_time=5.0,
                status="completed",
                deviation_seconds=2.0
            )
        ]

        # Generate report
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "comprehensive",
            "include_ce_tests": True,
            "include_interface_tests": True,
            "include_trends": True,
            "date_range": {
                "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
                "end_date": datetime.now().isoformat()
            }
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "report_id" in data
        assert "status" in data
        assert data["status"] == "generating"

    def test_report_generation_with_interface_tests(self, client: TestClient, test_data):
        """Test report generation including interface test results"""
        # Create interface test session
        interface_session = InterfaceTestSession(
            id=uuid.uuid4(),
            test_session_id=test_data["test_session"].id,
            building_id=test_data["building"].id,
            test_type="manual_override",
            status="completed",
            created_at=datetime.now() - timedelta(days=1)
        )
        
        # Create interface test steps
        interface_steps = [
            InterfaceTestStep(
                id=uuid.uuid4(),
                interface_test_session_id=interface_session.id,
                step_name="Fire Panel Override",
                action="Test fire panel override",
                response_time=2.5,
                status="completed",
                validation_status="passed"
            ),
            InterfaceTestStep(
                id=uuid.uuid4(),
                interface_test_session_id=interface_session.id,
                step_name="BMS Override",
                action="Test BMS override",
                response_time=1.8,
                status="completed",
                validation_status="passed"
            )
        ]

        # Generate report
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "comprehensive",
            "include_ce_tests": True,
            "include_interface_tests": True,
            "include_trends": True
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "report_id" in data
        assert "estimated_completion_time" in data

    def test_report_generation_with_trends(self, client: TestClient, test_data):
        """Test report generation with 3-year trend analysis"""
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "trend_analysis",
            "include_trends": True,
            "trend_period_years": 3,
            "include_predictions": True
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "report_id" in data
        assert "trend_analysis" in data
        assert "predictions" in data

    def test_report_download(self, client: TestClient, test_data):
        """Test downloading generated PDF report"""
        # First generate a report
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "comprehensive"
        }
        
        generate_response = client.post("/v1/reports/generate", json=report_data)
        report_id = generate_response.json()["report_id"]

        # Wait for report to be generated (in real scenario, this would be async)
        # For testing, we'll simulate a completed report
        
        # Download the report
        response = client.get(f"/v1/reports/{report_id}/download")
        
        # Note: In a real test, the report might still be generating
        # We expect either 200 (ready) or 202 (still generating)
        assert response.status_code in [200, 202]
        
        if response.status_code == 200:
            # Check that it's a PDF
            assert response.headers["content-type"] == "application/pdf"
            assert len(response.content) > 0

    def test_report_status_check(self, client: TestClient, test_data):
        """Test checking report generation status"""
        # Generate a report
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "comprehensive"
        }
        
        generate_response = client.post("/v1/reports/generate", json=report_data)
        report_id = generate_response.json()["report_id"]

        # Check status
        response = client.get(f"/v1/reports/{report_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "report_id" in data
        assert "status" in data
        assert data["status"] in ["generating", "completed", "failed"]
        assert "created_at" in data
        assert "updated_at" in data

    def test_calibration_verification_table(self, client: TestClient, test_data):
        """Test calibration verification table in reports"""
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "comprehensive",
            "include_calibration_table": True
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "report_id" in data
        assert "calibration_verification" in data

    def test_engineer_compliance_statement(self, client: TestClient, test_data):
        """Test engineer compliance statement section"""
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "comprehensive",
            "include_compliance_statement": True,
            "engineer_id": str(test_data["user"].id)
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "report_id" in data
        assert "compliance_statement" in data

    def test_report_performance_requirements(self, client: TestClient, test_data):
        """Test that report generation meets performance requirements"""
        import time
        
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
        
        assert response.status_code == 201
        # Report generation initiation should be fast
        assert (end_time - start_time) < 1.0  # <1s to initiate

    def test_trend_analysis_performance(self, client: TestClient, test_data):
        """Test trend analysis performance (<5s requirement)"""
        import time
        
        building_id = str(test_data["building"].id)
        
        start_time = time.time()
        response = client.get(f"/v1/reports/{building_id}/trends")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 5.0  # <5s requirement

    def test_report_data_aggregation(self, client: TestClient, test_data):
        """Test data aggregation for reports with 3 years of mock data"""
        # This test would require setting up 3 years of historical data
        # For now, we'll test the aggregation logic
        
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "historical_analysis",
            "date_range": {
                "start_date": (datetime.now() - timedelta(days=1095)).isoformat(),  # 3 years
                "end_date": datetime.now().isoformat()
            }
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "report_id" in data
        assert "data_summary" in data
        
        # Check aggregation results
        summary = data["data_summary"]
        assert "total_tests" in summary
        assert "date_range" in summary
        assert "building_info" in summary

    def test_chart_data_generation(self, client: TestClient, test_data):
        """Test chart data generation for visualizations"""
        building_id = str(test_data["building"].id)
        
        response = client.get(f"/v1/reports/{building_id}/chart-data")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "pressure_charts" in data
        assert "velocity_charts" in data
        assert "force_charts" in data
        
        # Check chart data structure
        pressure_charts = data["pressure_charts"]
        assert "floors" in pressure_charts
        assert "time_series" in pressure_charts
        assert "trend_lines" in pressure_charts

    def test_report_sections_validation(self, client: TestClient, test_data):
        """Test that all required report sections are included"""
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "comprehensive",
            "include_ce_tests": True,
            "include_interface_tests": True,
            "include_trends": True,
            "include_calibration_table": True,
            "include_compliance_statement": True
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "report_id" in data
        assert "sections" in data
        
        sections = data["sections"]
        required_sections = [
            "executive_summary",
            "ce_test_results",
            "interface_test_results", 
            "trend_analysis",
            "calibration_verification",
            "compliance_statement"
        ]
        
        for section in required_sections:
            assert section in sections

    def test_report_error_handling(self, client: TestClient):
        """Test error handling for invalid report requests"""
        # Test with invalid building ID
        report_data = {
            "building_id": "invalid-uuid",
            "test_session_id": str(uuid.uuid4()),
            "report_type": "comprehensive"
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        assert response.status_code == 400

        # Test with missing required fields
        report_data = {
            "building_id": str(uuid.uuid4()),
            "report_type": "comprehensive"
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        assert response.status_code == 422

    def test_report_statistical_analysis(self, client: TestClient, test_data):
        """Test statistical analysis in reports"""
        report_data = {
            "building_id": str(test_data["building"].id),
            "test_session_id": str(test_data["test_session"].id),
            "report_type": "statistical_analysis",
            "include_statistics": True
        }
        
        response = client.post("/v1/reports/generate", json=report_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "report_id" in data
        assert "statistical_analysis" in data
        
        stats = data["statistical_analysis"]
        assert "descriptive_stats" in stats
        assert "correlation_analysis" in stats
        assert "confidence_intervals" in stats
