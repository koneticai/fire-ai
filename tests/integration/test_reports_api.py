"""
Integration tests for reports API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from src.app.main import app
from src.app.models import Building


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def mock_building():
    """Mock building data"""
    return Building(
        id=uuid4(),
        name="Test Building",
        address="123 Test Street",
        building_type="Commercial",
        compliance_status="active",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def mock_user_token():
    """Mock user authentication token"""
    return {
        "user_id": str(uuid4()),
        "username": "testuser",
        "is_active": True
    }


class TestReportsAPI:
    """Test cases for reports API endpoints"""
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    def test_health_check(self, mock_get_db, mock_get_user, client):
        """Test health check endpoint"""
        response = client.get("/v1/reports/health-check")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "reports"
        assert data["status"] == "healthy"
        assert "version" in data
        assert "features" in data
        assert "timestamp" in data
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    @patch('src.app.services.report_generator_v2.ReportGeneratorV2.generate_compliance_report')
    def test_generate_report_success(
        self, 
        mock_generate_report, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_building,
        mock_user_token
    ):
        """Test successful report generation"""
        # Mock dependencies
        mock_get_user.return_value = mock_user_token
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session
        
        # Mock building query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_building
        
        # Mock report generation
        mock_generate_report.return_value = b"fake_pdf_content"
        
        # Test request
        request_data = {
            "building_id": str(mock_building.id),
            "years_back": 3,
            "include_trends": True,
            "include_charts": True,
            "report_type": "compliance"
        }
        
        response = client.post("/v1/reports/generate", json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "report_id" in data
        assert data["building_id"] == str(mock_building.id)
        assert data["report_type"] == "compliance"
        assert "generated_at" in data
        assert "file_size_bytes" in data
        assert "download_url" in data
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    def test_generate_report_building_not_found(
        self, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_user_token
    ):
        """Test report generation with non-existent building"""
        # Mock dependencies
        mock_get_user.return_value = mock_user_token
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session
        
        # Mock building not found
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Test request
        request_data = {
            "building_id": str(uuid4()),
            "years_back": 3,
            "include_trends": True,
            "include_charts": True,
            "report_type": "compliance"
        }
        
        response = client.post("/v1/reports/generate", json=request_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    @patch('src.app.services.trend_analyzer.TrendAnalyzer.get_building_trend_summary')
    def test_analyze_trends_success(
        self, 
        mock_get_trend_summary, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_building,
        mock_user_token
    ):
        """Test successful trend analysis"""
        # Mock dependencies
        mock_get_user.return_value = mock_user_token
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session
        
        # Mock building query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_building
        
        # Mock trend analysis result
        mock_trend_summary = {
            "building_id": str(mock_building.id),
            "analysis_period_years": 3,
            "analysis_date": datetime.now().isoformat(),
            "building_health_score": 85.5,
            "critical_issues": [],
            "recommendations": ["Continue regular maintenance"],
            "pressure_differential_trends": {},
            "air_velocity_trends": {},
            "door_force_trends": {},
            "defect_trends": {}
        }
        mock_get_trend_summary.return_value = mock_trend_summary
        
        # Test request
        request_data = {
            "building_id": str(mock_building.id),
            "years_back": 3,
            "analysis_types": ["pressure_differential", "air_velocity", "door_force", "defects"]
        }
        
        response = client.post("/v1/reports/trends", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(mock_building.id)
        assert data["analysis_period_years"] == 3
        assert data["building_health_score"] == 85.5
        assert "critical_issues" in data
        assert "recommendations" in data
        assert "trend_data" in data
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    @patch('src.app.services.trend_analyzer.TrendAnalyzer.get_building_trend_summary')
    def test_get_building_trends_success(
        self, 
        mock_get_trend_summary, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_building,
        mock_user_token
    ):
        """Test successful building trends retrieval"""
        # Mock dependencies
        mock_get_user.return_value = mock_user_token
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session
        
        # Mock building query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_building
        
        # Mock trend analysis result
        mock_trend_summary = {
            "building_id": str(mock_building.id),
            "analysis_period_years": 3,
            "analysis_date": datetime.now().isoformat(),
            "building_health_score": 90.0,
            "critical_issues": [],
            "recommendations": ["All systems operating normally"],
            "pressure_differential_trends": {},
            "air_velocity_trends": {},
            "door_force_trends": {},
            "defect_trends": {}
        }
        mock_get_trend_summary.return_value = mock_trend_summary
        
        # Test request
        response = client.get(f"/v1/reports/trends/{mock_building.id}?years_back=3")
        
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(mock_building.id)
        assert data["analysis_period_years"] == 3
        assert data["building_health_score"] == 90.0
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    @patch('src.app.services.trend_analyzer.TrendAnalyzer.analyze_pressure_differential_trends')
    def test_get_pressure_differential_trends_success(
        self, 
        mock_analyze_pressure, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_building,
        mock_user_token
    ):
        """Test successful pressure differential trends retrieval"""
        # Mock dependencies
        mock_get_user.return_value = mock_user_token
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session
        
        # Mock building query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_building
        
        # Mock pressure differential trends
        mock_pressure_trends = {
            "floor1_all_doors": {
                "trend_direction": "stable",
                "trend_strength": 0.3,
                "confidence_level": 0.8,
                "data_points": 10,
                "recommendations": ["Continue monitoring"]
            }
        }
        mock_analyze_pressure.return_value = mock_pressure_trends
        
        # Test request
        response = client.get(f"/v1/reports/trends/{mock_building.id}/pressure-differentials?years_back=3")
        
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(mock_building.id)
        assert data["analysis_period_years"] == 3
        assert "pressure_differential_trends" in data
        assert "floor1_all_doors" in data["pressure_differential_trends"]
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    @patch('src.app.services.trend_analyzer.TrendAnalyzer.analyze_air_velocity_trends')
    def test_get_air_velocity_trends_success(
        self, 
        mock_analyze_velocity, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_building,
        mock_user_token
    ):
        """Test successful air velocity trends retrieval"""
        # Mock dependencies
        mock_get_user.return_value = mock_user_token
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session
        
        # Mock building query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_building
        
        # Mock air velocity trends
        mock_velocity_trends = {
            "doorway1": {
                "trend_direction": "stable",
                "trend_strength": 0.2,
                "confidence_level": 0.7,
                "data_points": 8,
                "recommendations": ["System operating normally"]
            }
        }
        mock_analyze_velocity.return_value = mock_velocity_trends
        
        # Test request
        response = client.get(f"/v1/reports/trends/{mock_building.id}/air-velocities?years_back=3")
        
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(mock_building.id)
        assert data["analysis_period_years"] == 3
        assert "air_velocity_trends" in data
        assert "doorway1" in data["air_velocity_trends"]
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    @patch('src.app.services.trend_analyzer.TrendAnalyzer.analyze_door_force_trends')
    def test_get_door_force_trends_success(
        self, 
        mock_analyze_force, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_building,
        mock_user_token
    ):
        """Test successful door force trends retrieval"""
        # Mock dependencies
        mock_get_user.return_value = mock_user_token
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session
        
        # Mock building query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_building
        
        # Mock door force trends
        mock_force_trends = {
            "door1": {
                "trend_direction": "increasing",
                "trend_strength": 0.6,
                "confidence_level": 0.8,
                "data_points": 12,
                "recommendations": ["Check door hardware"]
            }
        }
        mock_analyze_force.return_value = mock_force_trends
        
        # Test request
        response = client.get(f"/v1/reports/trends/{mock_building.id}/door-forces?years_back=3")
        
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(mock_building.id)
        assert data["analysis_period_years"] == 3
        assert "door_force_trends" in data
        assert "door1" in data["door_force_trends"]
    
    @patch('src.app.routers.reports.get_current_active_user')
    @patch('src.app.routers.reports.get_db')
    @patch('src.app.services.trend_analyzer.TrendAnalyzer.analyze_defect_trends')
    def test_get_defect_trends_success(
        self, 
        mock_analyze_defects, 
        mock_get_db, 
        mock_get_user, 
        client, 
        mock_building,
        mock_user_token
    ):
        """Test successful defect trends retrieval"""
        # Mock dependencies
        mock_get_user.return_value = mock_user_token
        mock_db_session = AsyncMock()
        mock_get_db.return_value = mock_db_session
        
        # Mock building query result
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_building
        
        # Mock defect trends
        mock_defect_trends = {
            "extinguisher_pressure": {
                "trend_direction": "decreasing",
                "trend_strength": 0.4,
                "confidence_level": 0.6,
                "data_points": 15,
                "recommendations": ["Defect frequency decreasing"]
            }
        }
        mock_analyze_defects.return_value = mock_defect_trends
        
        # Test request
        response = client.get(f"/v1/reports/trends/{mock_building.id}/defects?years_back=3")
        
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(mock_building.id)
        assert data["analysis_period_years"] == 3
        assert "defect_trends" in data
        assert "extinguisher_pressure" in data["defect_trends"]
    
    def test_generate_report_invalid_request(self, client):
        """Test report generation with invalid request data"""
        # Test with missing required fields
        request_data = {
            "years_back": 3,
            "include_trends": True
        }
        
        response = client.post("/v1/reports/generate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_generate_report_invalid_years_back(self, client):
        """Test report generation with invalid years_back parameter"""
        request_data = {
            "building_id": str(uuid4()),
            "years_back": 15,  # Exceeds maximum of 10
            "include_trends": True,
            "include_charts": True,
            "report_type": "compliance"
        }
        
        response = client.post("/v1/reports/generate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_analyze_trends_invalid_request(self, client):
        """Test trend analysis with invalid request data"""
        # Test with missing required fields
        request_data = {
            "years_back": 3,
            "analysis_types": ["pressure_differential"]
        }
        
        response = client.post("/v1/reports/trends", json=request_data)
        
        assert response.status_code == 422  # Validation error
