"""
Unit tests for trend analysis service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from src.app.services.trend_analyzer import TrendAnalyzer, TrendAnalysisResult


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock()


@pytest.fixture
def trend_analyzer(mock_db):
    """Trend analyzer instance with mocked database"""
    return TrendAnalyzer(mock_db)


@pytest.fixture
def sample_data_points():
    """Sample data points for trend analysis"""
    return [
        {'date': datetime.now() - timedelta(days=365), 'value': 50.0, 'type': 'baseline'},
        {'date': datetime.now() - timedelta(days=300), 'value': 52.0, 'type': 'ce_test'},
        {'date': datetime.now() - timedelta(days=200), 'value': 55.0, 'type': 'ce_test'},
        {'date': datetime.now() - timedelta(days=100), 'value': 58.0, 'type': 'ce_test'},
        {'date': datetime.now() - timedelta(days=30), 'value': 60.0, 'type': 'ce_test'},
    ]


class TestTrendAnalyzer:
    """Test cases for TrendAnalyzer"""
    
    def test_trend_analysis_result_initialization(self):
        """Test TrendAnalysisResult initialization"""
        result = TrendAnalysisResult()
        
        assert result.trend_direction == "stable"
        assert result.trend_strength == 0.0
        assert result.degradation_rate is None
        assert result.predicted_failure_date is None
        assert result.confidence_level == 0.0
        assert result.statistical_significance == 0.0
        assert result.recommendations == []
        assert result.anomalies == []
        assert result.data_points == 0
        assert result.analysis_period_days == 0
    
    def test_analyze_time_series_trend_increasing(self, trend_analyzer, sample_data_points):
        """Test trend analysis with increasing trend"""
        result = trend_analyzer._analyze_time_series_trend(sample_data_points, 'pressure_differential')
        
        assert result.trend_direction == "increasing"
        assert result.trend_strength > 0.5  # Strong positive correlation
        assert result.degradation_rate is not None
        assert result.degradation_rate > 0  # Positive degradation rate
        assert result.data_points == len(sample_data_points)
        assert result.analysis_period_days > 0
        assert len(result.recommendations) > 0
    
    def test_analyze_time_series_trend_decreasing(self, trend_analyzer):
        """Test trend analysis with decreasing trend"""
        decreasing_data = [
            {'date': datetime.now() - timedelta(days=365), 'value': 60.0, 'type': 'baseline'},
            {'date': datetime.now() - timedelta(days=300), 'value': 58.0, 'type': 'ce_test'},
            {'date': datetime.now() - timedelta(days=200), 'value': 55.0, 'type': 'ce_test'},
            {'date': datetime.now() - timedelta(days=100), 'value': 52.0, 'type': 'ce_test'},
            {'date': datetime.now() - timedelta(days=30), 'value': 50.0, 'type': 'ce_test'},
        ]
        
        result = trend_analyzer._analyze_time_series_trend(decreasing_data, 'pressure_differential')
        
        assert result.trend_direction == "decreasing"
        assert result.trend_strength > 0.5  # Strong negative correlation
        assert result.degradation_rate is not None
        assert result.degradation_rate < 0  # Negative degradation rate
    
    def test_analyze_time_series_trend_stable(self, trend_analyzer):
        """Test trend analysis with stable trend"""
        stable_data = [
            {'date': datetime.now() - timedelta(days=365), 'value': 50.0, 'type': 'baseline'},
            {'date': datetime.now() - timedelta(days=300), 'value': 51.0, 'type': 'ce_test'},
            {'date': datetime.now() - timedelta(days=200), 'value': 49.0, 'type': 'ce_test'},
            {'date': datetime.now() - timedelta(days=100), 'value': 50.5, 'type': 'ce_test'},
            {'date': datetime.now() - timedelta(days=30), 'value': 49.5, 'type': 'ce_test'},
        ]
        
        result = trend_analyzer._analyze_time_series_trend(stable_data, 'pressure_differential')
        
        assert result.trend_direction == "stable"
        assert result.trend_strength < 0.3  # Weak correlation
    
    def test_analyze_time_series_trend_insufficient_data(self, trend_analyzer):
        """Test trend analysis with insufficient data"""
        insufficient_data = [
            {'date': datetime.now() - timedelta(days=100), 'value': 50.0, 'type': 'baseline'},
            {'date': datetime.now() - timedelta(days=50), 'value': 52.0, 'type': 'ce_test'},
        ]
        
        result = trend_analyzer._analyze_time_series_trend(insufficient_data, 'pressure_differential')
        
        assert result.trend_direction == "stable"
        assert result.trend_strength == 0.0
        assert result.data_points == 0
    
    def test_generate_recommendations_pressure_differential(self, trend_analyzer):
        """Test recommendation generation for pressure differential"""
        recommendations = trend_analyzer._generate_recommendations(
            "pressure_differential", 
            "decreasing", 
            0.8, 
            -10.0, 
            []
        )
        
        assert len(recommendations) > 0
        assert any("pressure differential declining" in rec.lower() for rec in recommendations)
        assert any("maintenance inspection" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_air_velocity(self, trend_analyzer):
        """Test recommendation generation for air velocity"""
        recommendations = trend_analyzer._generate_recommendations(
            "air_velocity", 
            "decreasing", 
            0.7, 
            -0.2, 
            []
        )
        
        assert len(recommendations) > 0
        assert any("air velocity declining" in rec.lower() for rec in recommendations)
        assert any("fan performance" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_door_force(self, trend_analyzer):
        """Test recommendation generation for door force"""
        recommendations = trend_analyzer._generate_recommendations(
            "door_force", 
            "increasing", 
            0.6, 
            15.0, 
            []
        )
        
        assert len(recommendations) > 0
        assert any("door opening force increasing" in rec.lower() for rec in recommendations)
        assert any("door hardware" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_defect_count(self, trend_analyzer):
        """Test recommendation generation for defect count"""
        recommendations = trend_analyzer._generate_recommendations(
            "defect_count", 
            "increasing", 
            0.5, 
            2.0, 
            []
        )
        
        assert len(recommendations) > 0
        assert any("defect frequency increasing" in rec.lower() for rec in recommendations)
        assert any("maintenance procedures" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_weak_trend(self, trend_analyzer):
        """Test recommendation generation for weak trend"""
        recommendations = trend_analyzer._generate_recommendations(
            "pressure_differential", 
            "stable", 
            0.2, 
            None, 
            []
        )
        
        assert len(recommendations) == 1
        assert "not statistically significant" in recommendations[0].lower()
    
    def test_predict_failure_date_pressure_differential(self, trend_analyzer):
        """Test failure date prediction for pressure differential"""
        # Test increasing trend approaching maximum threshold
        failure_date = trend_analyzer._predict_failure_date(
            "pressure_differential", 
            75.0,  # Current value
            5.0    # 5 Pa per year increase
        )
        
        assert failure_date is not None
        assert failure_date > datetime.now()
        assert failure_date < datetime.now() + timedelta(days=365 * 2)  # Within 2 years
    
    def test_predict_failure_date_air_velocity(self, trend_analyzer):
        """Test failure date prediction for air velocity"""
        # Test decreasing trend approaching minimum threshold
        failure_date = trend_analyzer._predict_failure_date(
            "air_velocity", 
            1.2,   # Current value
            -0.1   # 0.1 m/s per year decrease
        )
        
        assert failure_date is not None
        assert failure_date > datetime.now()
        assert failure_date < datetime.now() + timedelta(days=365 * 3)  # Within 3 years
    
    def test_predict_failure_date_door_force(self, trend_analyzer):
        """Test failure date prediction for door force"""
        # Test increasing trend approaching maximum threshold
        failure_date = trend_analyzer._predict_failure_date(
            "door_force", 
            100.0,  # Current value
            5.0     # 5 N per year increase
        )
        
        assert failure_date is not None
        assert failure_date > datetime.now()
        assert failure_date < datetime.now() + timedelta(days=365 * 2)  # Within 2 years
    
    def test_predict_failure_date_no_failure_expected(self, trend_analyzer):
        """Test failure date prediction when no failure expected"""
        # Test stable values well within thresholds
        failure_date = trend_analyzer._predict_failure_date(
            "pressure_differential", 
            50.0,   # Well within 20-80 Pa range
            0.5     # Small increase
        )
        
        assert failure_date is None  # No failure expected
    
    def test_calculate_building_health_score(self, trend_analyzer):
        """Test building health score calculation"""
        # Create mock trend results
        pressure_trends = {
            "floor1_all_doors": TrendAnalysisResult(),
            "floor2_all_doors": TrendAnalysisResult()
        }
        pressure_trends["floor1_all_doors"].trend_direction = "stable"
        pressure_trends["floor1_all_doors"].trend_strength = 0.2
        pressure_trends["floor1_all_doors"].confidence_level = 0.8
        
        pressure_trends["floor2_all_doors"].trend_direction = "stable"
        pressure_trends["floor2_all_doors"].trend_strength = 0.3
        pressure_trends["floor2_all_doors"].confidence_level = 0.9
        
        velocity_trends = {
            "doorway1": TrendAnalysisResult()
        }
        velocity_trends["doorway1"].trend_direction = "stable"
        velocity_trends["doorway1"].trend_strength = 0.1
        velocity_trends["doorway1"].confidence_level = 0.7
        
        force_trends = {}
        defect_trends = {}
        
        health_score = trend_analyzer._calculate_building_health_score(
            pressure_trends, velocity_trends, force_trends, defect_trends
        )
        
        assert 0 <= health_score <= 100
        assert health_score > 50  # Should be good with stable trends
    
    def test_identify_critical_issues(self, trend_analyzer):
        """Test critical issue identification"""
        # Create mock trend results with critical issues
        pressure_trends = {
            "floor1_all_doors": TrendAnalysisResult()
        }
        pressure_trends["floor1_all_doors"].trend_direction = "increasing"
        pressure_trends["floor1_all_doors"].trend_strength = 0.8
        pressure_trends["floor1_all_doors"].confidence_level = 0.9
        pressure_trends["floor1_all_doors"].predicted_failure_date = datetime.now() + timedelta(days=30)
        
        velocity_trends = {}
        force_trends = {}
        defect_trends = {}
        
        critical_issues = trend_analyzer._identify_critical_issues(
            pressure_trends, velocity_trends, force_trends, defect_trends
        )
        
        assert len(critical_issues) == 1
        assert critical_issues[0]["type"] == "pressure_differential"
        assert critical_issues[0]["location"] == "floor1_all_doors"
        assert critical_issues[0]["severity"] == "critical"
        assert critical_issues[0]["trend_direction"] == "increasing"
    
    def test_serialize_trends(self, trend_analyzer):
        """Test trend serialization"""
        trends = {
            "location1": TrendAnalysisResult()
        }
        trends["location1"].trend_direction = "increasing"
        trends["location1"].trend_strength = 0.7
        trends["location1"].confidence_level = 0.8
        trends["location1"].data_points = 10
        trends["location1"].analysis_period_days = 365
        trends["location1"].recommendations = ["Test recommendation"]
        
        serialized = trend_analyzer._serialize_trends(trends)
        
        assert "location1" in serialized
        assert serialized["location1"]["trend_direction"] == "increasing"
        assert serialized["location1"]["trend_strength"] == 0.7
        assert serialized["location1"]["confidence_level"] == 0.8
        assert serialized["location1"]["data_points"] == 10
        assert serialized["location1"]["analysis_period_days"] == 365
        assert serialized["location1"]["recommendations"] == ["Test recommendation"]
