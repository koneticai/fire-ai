"""
Trend Analysis Service for FireMode Compliance Platform
Implements time series analysis, degradation pattern detection, and predictive maintenance
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import selectinload

from ..models import (
    Building, 
    CETestSession, 
    CETestMeasurement, 
    CETestDeviation,
    BaselinePressureDifferential,
    BaselineAirVelocity,
    BaselineDoorForce,
    Defect
)

logger = logging.getLogger(__name__)


class TrendAnalysisResult:
    """Container for trend analysis results"""
    
    def __init__(self):
        self.trend_direction: str = "stable"  # increasing, decreasing, stable
        self.trend_strength: float = 0.0  # 0-1, correlation coefficient
        self.degradation_rate: Optional[float] = None  # per year
        self.predicted_failure_date: Optional[datetime] = None
        self.confidence_level: float = 0.0  # 0-1
        self.statistical_significance: float = 0.0  # p-value
        self.recommendations: List[str] = []
        self.anomalies: List[Dict[str, Any]] = []
        self.data_points: int = 0
        self.analysis_period_days: int = 0


class TrendAnalyzer:
    """
    Service for analyzing trends in fire safety compliance data
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def analyze_pressure_differential_trends(
        self, 
        building_id: UUID, 
        years_back: int = 3
    ) -> Dict[str, TrendAnalysisResult]:
        """
        Analyze pressure differential trends for all floors and door configurations
        
        Args:
            building_id: Building to analyze
            years_back: Number of years to look back (default 3)
            
        Returns:
            Dict mapping floor_config to TrendAnalysisResult
        """
        logger.info(f"Analyzing pressure differential trends for building {building_id}")
        
        # Get baseline data
        baseline_query = select(BaselinePressureDifferential).where(
            BaselinePressureDifferential.building_id == building_id
        )
        baseline_result = await self.db.execute(baseline_query)
        baseline_data = baseline_result.scalars().all()
        
        # Get C&E test measurements
        cutoff_date = datetime.now() - timedelta(days=years_back * 365)
        ce_query = select(CETestMeasurement).join(CETestSession).where(
            and_(
                CETestSession.building_id == building_id,
                CETestMeasurement.measurement_type == 'pressure_differential',
                CETestMeasurement.timestamp >= cutoff_date
            )
        ).order_by(CETestMeasurement.timestamp)
        
        ce_result = await self.db.execute(ce_query)
        ce_data = ce_result.scalars().all()
        
        # Group data by floor and door configuration
        trends = {}
        
        # Process baseline data
        baseline_by_config = {}
        for baseline in baseline_data:
            config_key = f"{baseline.floor_id}_{baseline.door_configuration}"
            if config_key not in baseline_by_config:
                baseline_by_config[config_key] = []
            baseline_by_config[config_key].append({
                'date': baseline.measured_date,
                'value': baseline.pressure_pa,
                'type': 'baseline'
            })
        
        # Process C&E test data
        ce_by_config = {}
        for measurement in ce_data:
            # Extract location info from measurement metadata
            metadata = measurement.measurement_metadata or {}
            floor_id = metadata.get('floor_id', 'unknown')
            door_config = metadata.get('door_configuration', 'unknown')
            config_key = f"{floor_id}_{door_config}"
            
            if config_key not in ce_by_config:
                ce_by_config[config_key] = []
            ce_by_config[config_key].append({
                'date': measurement.timestamp.date(),
                'value': measurement.measurement_value,
                'type': 'ce_test'
            })
        
        # Analyze trends for each configuration
        all_configs = set(baseline_by_config.keys()) | set(ce_by_config.keys())
        
        for config_key in all_configs:
            baseline_points = baseline_by_config.get(config_key, [])
            ce_points = ce_by_config.get(config_key, [])
            
            # Combine and sort all data points
            all_points = baseline_points + ce_points
            all_points.sort(key=lambda x: x['date'])
            
            if len(all_points) < 3:  # Need at least 3 points for trend analysis
                continue
            
            # Perform trend analysis
            trend_result = self._analyze_time_series_trend(all_points, 'pressure_differential')
            trends[config_key] = trend_result
        
        return trends
    
    async def analyze_air_velocity_trends(
        self, 
        building_id: UUID, 
        years_back: int = 3
    ) -> Dict[str, TrendAnalysisResult]:
        """
        Analyze air velocity trends for all doorways
        
        Args:
            building_id: Building to analyze
            years_back: Number of years to look back (default 3)
            
        Returns:
            Dict mapping doorway_id to TrendAnalysisResult
        """
        logger.info(f"Analyzing air velocity trends for building {building_id}")
        
        # Get baseline data
        baseline_query = select(BaselineAirVelocity).where(
            BaselineAirVelocity.building_id == building_id
        )
        baseline_result = await self.db.execute(baseline_query)
        baseline_data = baseline_result.scalars().all()
        
        # Get C&E test measurements
        cutoff_date = datetime.now() - timedelta(days=years_back * 365)
        ce_query = select(CETestMeasurement).join(CETestSession).where(
            and_(
                CETestSession.building_id == building_id,
                CETestMeasurement.measurement_type == 'air_velocity',
                CETestMeasurement.timestamp >= cutoff_date
            )
        ).order_by(CETestMeasurement.timestamp)
        
        ce_result = await self.db.execute(ce_query)
        ce_data = ce_result.scalars().all()
        
        # Group data by doorway
        trends = {}
        
        # Process baseline data
        baseline_by_doorway = {}
        for baseline in baseline_data:
            doorway_id = baseline.doorway_id
            if doorway_id not in baseline_by_doorway:
                baseline_by_doorway[doorway_id] = []
            baseline_by_doorway[doorway_id].append({
                'date': baseline.measured_date,
                'value': baseline.velocity_ms,
                'type': 'baseline'
            })
        
        # Process C&E test data
        ce_by_doorway = {}
        for measurement in ce_data:
            doorway_id = measurement.location_id
            if doorway_id not in ce_by_doorway:
                ce_by_doorway[doorway_id] = []
            ce_by_doorway[doorway_id].append({
                'date': measurement.timestamp.date(),
                'value': measurement.measurement_value,
                'type': 'ce_test'
            })
        
        # Analyze trends for each doorway
        all_doorways = set(baseline_by_doorway.keys()) | set(ce_by_doorway.keys())
        
        for doorway_id in all_doorways:
            baseline_points = baseline_by_doorway.get(doorway_id, [])
            ce_points = ce_by_doorway.get(doorway_id, [])
            
            # Combine and sort all data points
            all_points = baseline_points + ce_points
            all_points.sort(key=lambda x: x['date'])
            
            if len(all_points) < 3:
                continue
            
            # Perform trend analysis
            trend_result = self._analyze_time_series_trend(all_points, 'air_velocity')
            trends[doorway_id] = trend_result
        
        return trends
    
    async def analyze_door_force_trends(
        self, 
        building_id: UUID, 
        years_back: int = 3
    ) -> Dict[str, TrendAnalysisResult]:
        """
        Analyze door force trends for all doors
        
        Args:
            building_id: Building to analyze
            years_back: Number of years to look back (default 3)
            
        Returns:
            Dict mapping door_id to TrendAnalysisResult
        """
        logger.info(f"Analyzing door force trends for building {building_id}")
        
        # Get baseline data
        baseline_query = select(BaselineDoorForce).where(
            BaselineDoorForce.building_id == building_id
        )
        baseline_result = await self.db.execute(baseline_query)
        baseline_data = baseline_result.scalars().all()
        
        # Get C&E test measurements
        cutoff_date = datetime.now() - timedelta(days=years_back * 365)
        ce_query = select(CETestMeasurement).join(CETestSession).where(
            and_(
                CETestSession.building_id == building_id,
                CETestMeasurement.measurement_type == 'door_force',
                CETestMeasurement.timestamp >= cutoff_date
            )
        ).order_by(CETestMeasurement.timestamp)
        
        ce_result = await self.db.execute(ce_query)
        ce_data = ce_result.scalars().all()
        
        # Group data by door
        trends = {}
        
        # Process baseline data
        baseline_by_door = {}
        for baseline in baseline_data:
            door_id = baseline.door_id
            if door_id not in baseline_by_door:
                baseline_by_door[door_id] = []
            baseline_by_door[door_id].append({
                'date': baseline.measured_date,
                'value': baseline.force_newtons,
                'type': 'baseline'
            })
        
        # Process C&E test data
        ce_by_door = {}
        for measurement in ce_data:
            door_id = measurement.location_id
            if door_id not in ce_by_door:
                ce_by_door[door_id] = []
            ce_by_door[door_id].append({
                'date': measurement.timestamp.date(),
                'value': measurement.measurement_value,
                'type': 'ce_test'
            })
        
        # Analyze trends for each door
        all_doors = set(baseline_by_door.keys()) | set(ce_by_door.keys())
        
        for door_id in all_doors:
            baseline_points = baseline_by_door.get(door_id, [])
            ce_points = ce_by_door.get(door_id, [])
            
            # Combine and sort all data points
            all_points = baseline_points + ce_points
            all_points.sort(key=lambda x: x['date'])
            
            if len(all_points) < 3:
                continue
            
            # Perform trend analysis
            trend_result = self._analyze_time_series_trend(all_points, 'door_force')
            trends[door_id] = trend_result
        
        return trends
    
    async def analyze_defect_trends(
        self, 
        building_id: UUID, 
        years_back: int = 3
    ) -> Dict[str, TrendAnalysisResult]:
        """
        Analyze defect trends by category and severity
        
        Args:
            building_id: Building to analyze
            years_back: Number of years to look back (default 3)
            
        Returns:
            Dict mapping category to TrendAnalysisResult
        """
        logger.info(f"Analyzing defect trends for building {building_id}")
        
        cutoff_date = datetime.now() - timedelta(days=years_back * 365)
        defects_query = select(Defect).where(
            and_(
                Defect.building_id == building_id,
                Defect.discovered_at >= cutoff_date
            )
        ).order_by(Defect.discovered_at)
        
        defects_result = await self.db.execute(defects_query)
        defects_data = defects_result.scalars().all()
        
        # Group defects by category
        defects_by_category = {}
        for defect in defects_data:
            category = defect.category or 'uncategorized'
            if category not in defects_by_category:
                defects_by_category[category] = []
            defects_by_category[category].append({
                'date': defect.discovered_at.date(),
                'value': 1,  # Count of defects
                'severity': defect.severity,
                'type': 'defect'
            })
        
        # Analyze trends for each category
        trends = {}
        for category, defect_points in defects_by_category.items():
            if len(defect_points) < 3:
                continue
            
            # Perform trend analysis
            trend_result = self._analyze_time_series_trend(defect_points, 'defect_count')
            trends[category] = trend_result
        
        return trends
    
    def _analyze_time_series_trend(
        self, 
        data_points: List[Dict[str, Any]], 
        measurement_type: str
    ) -> TrendAnalysisResult:
        """
        Perform statistical trend analysis on time series data
        
        Args:
            data_points: List of data points with 'date', 'value', 'type'
            measurement_type: Type of measurement for context
            
        Returns:
            TrendAnalysisResult with analysis
        """
        result = TrendAnalysisResult()
        
        if len(data_points) < 3:
            return result
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data_points)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate days since first measurement
        df['days_since_start'] = (df['date'] - df['date'].min()).dt.days
        
        # Perform linear regression
        x = df['days_since_start'].values
        y = df['value'].values
        
        # Calculate correlation coefficient
        correlation = np.corrcoef(x, y)[0, 1]
        result.trend_strength = abs(correlation) if not np.isnan(correlation) else 0.0
        
        # Determine trend direction
        if correlation > 0.3:
            result.trend_direction = "increasing"
        elif correlation < -0.3:
            result.trend_direction = "decreasing"
        else:
            result.trend_direction = "stable"
        
        # Calculate degradation rate (per year)
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            result.degradation_rate = slope * 365  # Convert to per year
        
        # Statistical significance (simplified p-value calculation)
        n = len(x)
        if n > 2:
            # Calculate t-statistic for correlation
            t_stat = correlation * np.sqrt((n - 2) / (1 - correlation**2)) if correlation != 1 else 0
            # Approximate p-value (simplified)
            result.statistical_significance = max(0, 1 - abs(t_stat) / 3)  # Rough approximation
        
        # Confidence level based on data points and correlation
        result.confidence_level = min(1.0, (n / 10) * result.trend_strength)
        
        # Detect anomalies (values more than 2 standard deviations from trend)
        if len(y) > 3:
            residuals = y - np.polyval(np.polyfit(x, y, 1), x)
            std_residuals = np.std(residuals)
            mean_residuals = np.mean(residuals)
            
            for i, (idx, row) in enumerate(df.iterrows()):
                if abs(residuals[i]) > 2 * std_residuals:
                    result.anomalies.append({
                        'date': row['date'].isoformat(),
                        'value': row['value'],
                        'expected': np.polyval(np.polyfit(x, y, 1), x[i]),
                        'deviation': residuals[i],
                        'type': row.get('type', 'unknown')
                    })
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(
            measurement_type, 
            result.trend_direction, 
            result.trend_strength,
            result.degradation_rate,
            result.anomalies
        )
        
        # Predict failure date if degradation is significant
        if (result.trend_direction in ["increasing", "decreasing"] and 
            result.trend_strength > 0.5 and 
            result.degradation_rate is not None):
            
            result.predicted_failure_date = self._predict_failure_date(
                measurement_type, 
                df['value'].iloc[-1], 
                result.degradation_rate
            )
        
        result.data_points = len(data_points)
        result.analysis_period_days = (df['date'].max() - df['date'].min()).days
        
        return result
    
    def _generate_recommendations(
        self, 
        measurement_type: str, 
        trend_direction: str, 
        trend_strength: float,
        degradation_rate: Optional[float],
        anomalies: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate maintenance recommendations based on trend analysis"""
        recommendations = []
        
        if trend_strength < 0.3:
            recommendations.append("Trend is not statistically significant - continue regular monitoring")
            return recommendations
        
        if measurement_type == "pressure_differential":
            if trend_direction == "decreasing" and degradation_rate and degradation_rate < -5:
                recommendations.append("Pressure differential declining - check for air leakage or system degradation")
                recommendations.append("Schedule maintenance inspection within 30 days")
            elif trend_direction == "increasing" and degradation_rate and degradation_rate > 5:
                recommendations.append("Pressure differential increasing - check for system over-pressurization")
        
        elif measurement_type == "air_velocity":
            if trend_direction == "decreasing" and degradation_rate and degradation_rate < -0.1:
                recommendations.append("Air velocity declining - check fan performance and ductwork")
                recommendations.append("Verify fan motor and belt condition")
            elif trend_direction == "increasing" and degradation_rate and degradation_rate > 0.1:
                recommendations.append("Air velocity increasing - check for system modifications or blockages")
        
        elif measurement_type == "door_force":
            if trend_direction == "increasing" and degradation_rate and degradation_rate > 10:
                recommendations.append("Door opening force increasing - check door hardware and alignment")
                recommendations.append("Lubricate hinges and check for binding")
            elif trend_direction == "decreasing" and degradation_rate and degradation_rate < -10:
                recommendations.append("Door opening force decreasing - check for hardware wear or damage")
        
        elif measurement_type == "defect_count":
            if trend_direction == "increasing":
                recommendations.append("Defect frequency increasing - review maintenance procedures")
                recommendations.append("Consider increasing inspection frequency")
        
        # Add anomaly-based recommendations
        if len(anomalies) > 0:
            recommendations.append(f"Found {len(anomalies)} anomalous measurements - investigate root causes")
        
        return recommendations
    
    def _predict_failure_date(
        self, 
        measurement_type: str, 
        current_value: float, 
        degradation_rate: float
    ) -> Optional[datetime]:
        """Predict when system might fail based on degradation rate"""
        
        # Define failure thresholds based on AS 1851-2012
        thresholds = {
            "pressure_differential": {"min": 20, "max": 80},  # Pa
            "air_velocity": {"min": 1.0, "max": float('inf')},  # m/s
            "door_force": {"min": 0, "max": 110},  # N
            "defect_count": {"min": 0, "max": 5}  # per year
        }
        
        if measurement_type not in thresholds:
            return None
        
        threshold = thresholds[measurement_type]
        
        # Calculate days to failure
        if degradation_rate > 0:  # Increasing trend
            if "max" in threshold and threshold["max"] != float('inf'):
                days_to_failure = (threshold["max"] - current_value) / (degradation_rate / 365)
            else:
                return None
        else:  # Decreasing trend
            if "min" in threshold:
                days_to_failure = (current_value - threshold["min"]) / (abs(degradation_rate) / 365)
            else:
                return None
        
        if days_to_failure > 0 and days_to_failure < 365 * 5:  # Within 5 years
            return datetime.now() + timedelta(days=days_to_failure)
        
        return None
    
    async def get_building_trend_summary(
        self, 
        building_id: UUID, 
        years_back: int = 3
    ) -> Dict[str, Any]:
        """
        Get comprehensive trend analysis summary for a building
        
        Args:
            building_id: Building to analyze
            years_back: Number of years to look back
            
        Returns:
            Comprehensive trend analysis summary
        """
        logger.info(f"Generating trend summary for building {building_id}")
        
        # Run all trend analyses
        pressure_trends = await self.analyze_pressure_differential_trends(building_id, years_back)
        velocity_trends = await self.analyze_air_velocity_trends(building_id, years_back)
        force_trends = await self.analyze_door_force_trends(building_id, years_back)
        defect_trends = await self.analyze_defect_trends(building_id, years_back)
        
        # Calculate overall building health score
        health_score = self._calculate_building_health_score(
            pressure_trends, velocity_trends, force_trends, defect_trends
        )
        
        # Identify critical issues
        critical_issues = self._identify_critical_issues(
            pressure_trends, velocity_trends, force_trends, defect_trends
        )
        
        return {
            "building_id": str(building_id),
            "analysis_period_years": years_back,
            "analysis_date": datetime.now().isoformat(),
            "building_health_score": health_score,
            "critical_issues": critical_issues,
            "pressure_differential_trends": self._serialize_trends(pressure_trends),
            "air_velocity_trends": self._serialize_trends(velocity_trends),
            "door_force_trends": self._serialize_trends(force_trends),
            "defect_trends": self._serialize_trends(defect_trends),
            "recommendations": self._generate_building_recommendations(
                pressure_trends, velocity_trends, force_trends, defect_trends
            )
        }
    
    def _calculate_building_health_score(
        self, 
        pressure_trends: Dict[str, TrendAnalysisResult],
        velocity_trends: Dict[str, TrendAnalysisResult],
        force_trends: Dict[str, TrendAnalysisResult],
        defect_trends: Dict[str, TrendAnalysisResult]
    ) -> float:
        """Calculate overall building health score (0-100)"""
        
        all_trends = list(pressure_trends.values()) + list(velocity_trends.values()) + \
                    list(force_trends.values()) + list(defect_trends.values())
        
        if not all_trends:
            return 50.0  # Neutral score if no data
        
        # Weight different factors
        trend_scores = []
        for trend in all_trends:
            # Base score from trend strength and direction
            if trend.trend_direction == "stable":
                score = 80
            elif trend.trend_direction in ["increasing", "decreasing"]:
                # Penalize strong trends (potential issues)
                score = max(20, 80 - (trend.trend_strength * 60))
            else:
                score = 50
            
            # Adjust for confidence level
            score = score * trend.confidence_level + 50 * (1 - trend.confidence_level)
            
            # Penalize for anomalies
            if len(trend.anomalies) > 0:
                score -= min(20, len(trend.anomalies) * 5)
            
            trend_scores.append(max(0, min(100, score)))
        
        return sum(trend_scores) / len(trend_scores)
    
    def _identify_critical_issues(
        self, 
        pressure_trends: Dict[str, TrendAnalysisResult],
        velocity_trends: Dict[str, TrendAnalysisResult],
        force_trends: Dict[str, TrendAnalysisResult],
        defect_trends: Dict[str, TrendAnalysisResult]
    ) -> List[Dict[str, Any]]:
        """Identify critical issues requiring immediate attention"""
        
        critical_issues = []
        
        # Check for critical trends
        for trend_type, trends in [
            ("pressure_differential", pressure_trends),
            ("air_velocity", velocity_trends),
            ("door_force", force_trends),
            ("defects", defect_trends)
        ]:
            for location, trend in trends.items():
                if (trend.trend_strength > 0.7 and 
                    trend.confidence_level > 0.6 and
                    trend.predicted_failure_date and
                    trend.predicted_failure_date < datetime.now() + timedelta(days=90)):
                    
                    critical_issues.append({
                        "type": trend_type,
                        "location": location,
                        "severity": "critical",
                        "trend_direction": trend.trend_direction,
                        "predicted_failure_date": trend.predicted_failure_date.isoformat(),
                        "confidence": trend.confidence_level,
                        "recommendations": trend.recommendations
                    })
        
        return critical_issues
    
    def _serialize_trends(self, trends: Dict[str, TrendAnalysisResult]) -> Dict[str, Dict[str, Any]]:
        """Serialize trend results for JSON response"""
        serialized = {}
        for location, trend in trends.items():
            serialized[location] = {
                "trend_direction": trend.trend_direction,
                "trend_strength": trend.trend_strength,
                "degradation_rate": trend.degradation_rate,
                "predicted_failure_date": trend.predicted_failure_date.isoformat() if trend.predicted_failure_date else None,
                "confidence_level": trend.confidence_level,
                "statistical_significance": trend.statistical_significance,
                "data_points": trend.data_points,
                "analysis_period_days": trend.analysis_period_days,
                "anomalies": trend.anomalies,
                "recommendations": trend.recommendations
            }
        return serialized
    
    def _generate_building_recommendations(
        self, 
        pressure_trends: Dict[str, TrendAnalysisResult],
        velocity_trends: Dict[str, TrendAnalysisResult],
        force_trends: Dict[str, TrendAnalysisResult],
        defect_trends: Dict[str, TrendAnalysisResult]
    ) -> List[str]:
        """Generate high-level building maintenance recommendations"""
        
        recommendations = []
        
        # Count critical trends
        critical_count = 0
        for trends in [pressure_trends, velocity_trends, force_trends, defect_trends]:
            for trend in trends.values():
                if trend.trend_strength > 0.7 and trend.confidence_level > 0.6:
                    critical_count += 1
        
        if critical_count > 0:
            recommendations.append(f"Immediate attention required: {critical_count} critical trends detected")
            recommendations.append("Schedule comprehensive system inspection within 7 days")
        
        # Check for increasing defect trends
        if any(trend.trend_direction == "increasing" for trend in defect_trends.values()):
            recommendations.append("Defect frequency increasing - review maintenance procedures and training")
        
        # Check for system-wide issues
        if len(pressure_trends) > 0 and len(velocity_trends) > 0:
            avg_pressure_health = sum(t.confidence_level for t in pressure_trends.values()) / len(pressure_trends)
            avg_velocity_health = sum(t.confidence_level for t in velocity_trends.values()) / len(velocity_trends)
            
            if avg_pressure_health < 0.5 or avg_velocity_health < 0.5:
                recommendations.append("System-wide performance degradation detected - consider major maintenance")
        
        if not recommendations:
            recommendations.append("All systems operating within normal parameters - continue regular maintenance schedule")
        
        return recommendations
