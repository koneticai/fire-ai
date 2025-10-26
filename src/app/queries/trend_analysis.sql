-- Trend Analysis SQL Queries for FireMode Compliance Platform
-- Optimized queries for 3-year trend analysis and data aggregation

-- =============================================================================
-- PRESSURE DIFFERENTIAL TRENDS
-- =============================================================================

-- Get 3-year pressure differential trends by floor and door configuration
-- Combines baseline measurements with C&E test measurements
WITH pressure_trends AS (
    -- Baseline pressure differentials
    SELECT 
        bpd.building_id,
        bpd.floor_id,
        bpd.door_configuration,
        bpd.pressure_pa as measurement_value,
        bpd.measured_date as measurement_date,
        'baseline' as measurement_type,
        bpd.created_at as recorded_at
    FROM baseline_pressure_differentials bpd
    WHERE bpd.building_id = :building_id
      AND bpd.measured_date >= CURRENT_DATE - INTERVAL '3 years'
    
    UNION ALL
    
    -- C&E test pressure differential measurements
    SELECT 
        cts.building_id,
        COALESCE(ctm.measurement_metadata->>'floor_id', 'unknown') as floor_id,
        COALESCE(ctm.measurement_metadata->>'door_configuration', 'unknown') as door_configuration,
        ctm.measurement_value,
        ctm.timestamp::date as measurement_date,
        'ce_test' as measurement_type,
        ctm.created_at as recorded_at
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'pressure_differential'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '3 years'
)
SELECT 
    floor_id,
    door_configuration,
    measurement_date,
    measurement_value,
    measurement_type,
    recorded_at,
    -- Calculate running statistics
    AVG(measurement_value) OVER (
        PARTITION BY floor_id, door_configuration 
        ORDER BY measurement_date 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_avg_3,
    STDDEV(measurement_value) OVER (
        PARTITION BY floor_id, door_configuration 
        ORDER BY measurement_date 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_stddev_3
FROM pressure_trends
ORDER BY floor_id, door_configuration, measurement_date;

-- =============================================================================
-- AIR VELOCITY TRENDS
-- =============================================================================

-- Get 3-year air velocity trends by doorway
WITH velocity_trends AS (
    -- Baseline air velocities
    SELECT 
        bav.building_id,
        bav.doorway_id,
        bav.velocity_ms as measurement_value,
        bav.measured_date as measurement_date,
        'baseline' as measurement_type,
        bav.created_at as recorded_at
    FROM baseline_air_velocities bav
    WHERE bav.building_id = :building_id
      AND bav.measured_date >= CURRENT_DATE - INTERVAL '3 years'
    
    UNION ALL
    
    -- C&E test air velocity measurements
    SELECT 
        cts.building_id,
        ctm.location_id as doorway_id,
        ctm.measurement_value,
        ctm.timestamp::date as measurement_date,
        'ce_test' as measurement_type,
        ctm.created_at as recorded_at
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'air_velocity'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '3 years'
)
SELECT 
    doorway_id,
    measurement_date,
    measurement_value,
    measurement_type,
    recorded_at,
    -- Calculate running statistics
    AVG(measurement_value) OVER (
        PARTITION BY doorway_id 
        ORDER BY measurement_date 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_avg_3,
    STDDEV(measurement_value) OVER (
        PARTITION BY doorway_id 
        ORDER BY measurement_date 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_stddev_3,
    -- Calculate trend direction
    CASE 
        WHEN measurement_value > LAG(measurement_value, 1) OVER (
            PARTITION BY doorway_id ORDER BY measurement_date
        ) THEN 'increasing'
        WHEN measurement_value < LAG(measurement_value, 1) OVER (
            PARTITION BY doorway_id ORDER BY measurement_date
        ) THEN 'decreasing'
        ELSE 'stable'
    END as trend_direction
FROM velocity_trends
ORDER BY doorway_id, measurement_date;

-- =============================================================================
-- DOOR FORCE TRENDS
-- =============================================================================

-- Get 3-year door force trends by door
WITH force_trends AS (
    -- Baseline door forces
    SELECT 
        bdf.building_id,
        bdf.door_id,
        bdf.force_newtons as measurement_value,
        bdf.measured_date as measurement_date,
        'baseline' as measurement_type,
        bdf.created_at as recorded_at
    FROM baseline_door_forces bdf
    WHERE bdf.building_id = :building_id
      AND bdf.measured_date >= CURRENT_DATE - INTERVAL '3 years'
    
    UNION ALL
    
    -- C&E test door force measurements
    SELECT 
        cts.building_id,
        ctm.location_id as door_id,
        ctm.measurement_value,
        ctm.timestamp::date as measurement_date,
        'ce_test' as measurement_type,
        ctm.created_at as recorded_at
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'door_force'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '3 years'
)
SELECT 
    door_id,
    measurement_date,
    measurement_value,
    measurement_type,
    recorded_at,
    -- Calculate running statistics
    AVG(measurement_value) OVER (
        PARTITION BY door_id 
        ORDER BY measurement_date 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_avg_3,
    STDDEV(measurement_value) OVER (
        PARTITION BY door_id 
        ORDER BY measurement_date 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_stddev_3,
    -- Calculate trend direction
    CASE 
        WHEN measurement_value > LAG(measurement_value, 1) OVER (
            PARTITION BY door_id ORDER BY measurement_date
        ) THEN 'increasing'
        WHEN measurement_value < LAG(measurement_value, 1) OVER (
            PARTITION BY door_id ORDER BY measurement_date
        ) THEN 'decreasing'
        ELSE 'stable'
    END as trend_direction
FROM force_trends
ORDER BY door_id, measurement_date;

-- =============================================================================
-- DEFECT TRENDS
-- =============================================================================

-- Get 3-year defect trends by category and severity
WITH defect_trends AS (
    SELECT 
        d.building_id,
        d.category,
        d.severity,
        d.discovered_at::date as defect_date,
        d.status,
        d.as1851_rule_code,
        -- Count defects per month
        DATE_TRUNC('month', d.discovered_at) as month_period
    FROM defects d
    WHERE d.building_id = :building_id
      AND d.discovered_at >= CURRENT_DATE - INTERVAL '3 years'
)
SELECT 
    category,
    severity,
    month_period,
    COUNT(*) as defect_count,
    COUNT(CASE WHEN status NOT IN ('closed', 'verified') THEN 1 END) as open_defect_count,
    -- Calculate running totals
    SUM(COUNT(*)) OVER (
        PARTITION BY category, severity 
        ORDER BY month_period 
        ROWS UNBOUNDED PRECEDING
    ) as cumulative_defects,
    -- Calculate trend direction
    CASE 
        WHEN COUNT(*) > LAG(COUNT(*), 1) OVER (
            PARTITION BY category, severity ORDER BY month_period
        ) THEN 'increasing'
        WHEN COUNT(*) < LAG(COUNT(*), 1) OVER (
            PARTITION BY category, severity ORDER BY month_period
        ) THEN 'decreasing'
        ELSE 'stable'
    END as trend_direction
FROM defect_trends
GROUP BY category, severity, month_period
ORDER BY category, severity, month_period;

-- =============================================================================
-- C&E TEST HISTORY ROLLUP
-- =============================================================================

-- Get C&E test session summary with compliance scores
SELECT 
    cts.id as session_id,
    cts.session_name,
    cts.test_type,
    cts.compliance_standard,
    cts.status,
    cts.compliance_score,
    cts.created_at,
    cts.updated_at,
    -- Count measurements and deviations
    COUNT(DISTINCT ctm.id) as measurement_count,
    COUNT(DISTINCT ctd.id) as deviation_count,
    -- Calculate average measurement values by type
    AVG(CASE WHEN ctm.measurement_type = 'pressure_differential' THEN ctm.measurement_value END) as avg_pressure_pa,
    AVG(CASE WHEN ctm.measurement_type = 'air_velocity' THEN ctm.measurement_value END) as avg_velocity_ms,
    AVG(CASE WHEN ctm.measurement_type = 'door_force' THEN ctm.measurement_value END) as avg_force_n,
    -- Count deviations by severity
    COUNT(CASE WHEN ctd.severity = 'critical' THEN 1 END) as critical_deviations,
    COUNT(CASE WHEN ctd.severity = 'high' THEN 1 END) as high_deviations,
    COUNT(CASE WHEN ctd.severity = 'medium' THEN 1 END) as medium_deviations,
    COUNT(CASE WHEN ctd.severity = 'low' THEN 1 END) as low_deviations
FROM ce_test_sessions cts
LEFT JOIN ce_test_measurements ctm ON cts.id = ctm.test_session_id
LEFT JOIN ce_test_deviations ctd ON cts.id = ctd.test_session_id
WHERE cts.building_id = :building_id
  AND cts.created_at >= CURRENT_DATE - INTERVAL '3 years'
GROUP BY cts.id, cts.session_name, cts.test_type, cts.compliance_standard, 
         cts.status, cts.compliance_score, cts.created_at, cts.updated_at
ORDER BY cts.created_at DESC;

-- =============================================================================
-- COMPLIANCE SCORE TRENDS
-- =============================================================================

-- Get compliance score trends over time
WITH compliance_scores AS (
    SELECT 
        cts.building_id,
        cts.created_at::date as test_date,
        cts.compliance_score,
        cts.test_type,
        -- Calculate monthly averages
        DATE_TRUNC('month', cts.created_at) as month_period
    FROM ce_test_sessions cts
    WHERE cts.building_id = :building_id
      AND cts.compliance_score IS NOT NULL
      AND cts.created_at >= CURRENT_DATE - INTERVAL '3 years'
)
SELECT 
    month_period,
    test_type,
    COUNT(*) as test_count,
    AVG(compliance_score) as avg_compliance_score,
    MIN(compliance_score) as min_compliance_score,
    MAX(compliance_score) as max_compliance_score,
    STDDEV(compliance_score) as compliance_score_stddev,
    -- Calculate trend direction
    CASE 
        WHEN AVG(compliance_score) > LAG(AVG(compliance_score), 1) OVER (
            PARTITION BY test_type ORDER BY month_period
        ) THEN 'improving'
        WHEN AVG(compliance_score) < LAG(AVG(compliance_score), 1) OVER (
            PARTITION BY test_type ORDER BY month_period
        ) THEN 'declining'
        ELSE 'stable'
    END as trend_direction
FROM compliance_scores
GROUP BY month_period, test_type
ORDER BY test_type, month_period;

-- =============================================================================
-- ANOMALY DETECTION QUERIES
-- =============================================================================

-- Detect anomalous pressure differential measurements
WITH pressure_stats AS (
    SELECT 
        floor_id,
        door_configuration,
        AVG(measurement_value) as mean_pressure,
        STDDEV(measurement_value) as stddev_pressure
    FROM (
        SELECT 
            bpd.floor_id,
            bpd.door_configuration,
            bpd.pressure_pa as measurement_value
        FROM baseline_pressure_differentials bpd
        WHERE bpd.building_id = :building_id
        
        UNION ALL
        
        SELECT 
            COALESCE(ctm.measurement_metadata->>'floor_id', 'unknown') as floor_id,
            COALESCE(ctm.measurement_metadata->>'door_configuration', 'unknown') as door_configuration,
            ctm.measurement_value
        FROM ce_test_measurements ctm
        JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
        WHERE cts.building_id = :building_id
          AND ctm.measurement_type = 'pressure_differential'
    ) all_measurements
    GROUP BY floor_id, door_configuration
)
SELECT 
    ctm.id as measurement_id,
    ctm.measurement_value,
    ctm.timestamp,
    ps.mean_pressure,
    ps.stddev_pressure,
    ABS(ctm.measurement_value - ps.mean_pressure) / ps.stddev_pressure as z_score,
    CASE 
        WHEN ABS(ctm.measurement_value - ps.mean_pressure) / ps.stddev_pressure > 2 THEN 'anomaly'
        ELSE 'normal'
    END as anomaly_status
FROM ce_test_measurements ctm
JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
JOIN pressure_stats ps ON 
    COALESCE(ctm.measurement_metadata->>'floor_id', 'unknown') = ps.floor_id
    AND COALESCE(ctm.measurement_metadata->>'door_configuration', 'unknown') = ps.door_configuration
WHERE cts.building_id = :building_id
  AND ctm.measurement_type = 'pressure_differential'
  AND ctm.timestamp >= CURRENT_DATE - INTERVAL '3 years'
  AND ps.stddev_pressure > 0
ORDER BY z_score DESC;

-- =============================================================================
-- PREDICTIVE MAINTENANCE QUERIES
-- =============================================================================

-- Identify systems approaching failure thresholds
WITH system_health AS (
    SELECT 
        'pressure_differential' as system_type,
        COALESCE(ctm.measurement_metadata->>'floor_id', 'unknown') as location,
        AVG(ctm.measurement_value) as current_avg,
        COUNT(*) as measurement_count,
        MAX(ctm.timestamp) as last_measurement
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'pressure_differential'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY COALESCE(ctm.measurement_metadata->>'floor_id', 'unknown')
    
    UNION ALL
    
    SELECT 
        'air_velocity' as system_type,
        ctm.location_id as location,
        AVG(ctm.measurement_value) as current_avg,
        COUNT(*) as measurement_count,
        MAX(ctm.timestamp) as last_measurement
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'air_velocity'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY ctm.location_id
    
    UNION ALL
    
    SELECT 
        'door_force' as system_type,
        ctm.location_id as location,
        AVG(ctm.measurement_value) as current_avg,
        COUNT(*) as measurement_count,
        MAX(ctm.timestamp) as last_measurement
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'door_force'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY ctm.location_id
)
SELECT 
    system_type,
    location,
    current_avg,
    measurement_count,
    last_measurement,
    -- AS 1851-2012 compliance thresholds
    CASE 
        WHEN system_type = 'pressure_differential' THEN
            CASE 
                WHEN current_avg < 20 THEN 'BELOW_MINIMUM'
                WHEN current_avg > 80 THEN 'ABOVE_MAXIMUM'
                ELSE 'COMPLIANT'
            END
        WHEN system_type = 'air_velocity' THEN
            CASE 
                WHEN current_avg < 1.0 THEN 'BELOW_MINIMUM'
                ELSE 'COMPLIANT'
            END
        WHEN system_type = 'door_force' THEN
            CASE 
                WHEN current_avg > 110 THEN 'ABOVE_MAXIMUM'
                ELSE 'COMPLIANT'
            END
    END as compliance_status,
    -- Risk assessment
    CASE 
        WHEN system_type = 'pressure_differential' AND (current_avg < 20 OR current_avg > 80) THEN 'HIGH'
        WHEN system_type = 'air_velocity' AND current_avg < 1.0 THEN 'HIGH'
        WHEN system_type = 'door_force' AND current_avg > 110 THEN 'HIGH'
        WHEN measurement_count < 3 THEN 'MEDIUM'
        ELSE 'LOW'
    END as risk_level
FROM system_health
WHERE measurement_count >= 1
ORDER BY 
    CASE 
        WHEN system_type = 'pressure_differential' AND (current_avg < 20 OR current_avg > 80) THEN 1
        WHEN system_type = 'air_velocity' AND current_avg < 1.0 THEN 1
        WHEN system_type = 'door_force' AND current_avg > 110 THEN 1
        ELSE 2
    END,
    current_avg;

-- =============================================================================
-- BUILDING HEALTH SUMMARY
-- =============================================================================

-- Get comprehensive building health summary
WITH building_metrics AS (
    -- Pressure differential health
    SELECT 
        'pressure_differential' as metric_type,
        COUNT(*) as total_measurements,
        AVG(measurement_value) as avg_value,
        COUNT(CASE WHEN measurement_value < 20 OR measurement_value > 80 THEN 1 END) as non_compliant_count
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'pressure_differential'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '1 year'
    
    UNION ALL
    
    -- Air velocity health
    SELECT 
        'air_velocity' as metric_type,
        COUNT(*) as total_measurements,
        AVG(measurement_value) as avg_value,
        COUNT(CASE WHEN measurement_value < 1.0 THEN 1 END) as non_compliant_count
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'air_velocity'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '1 year'
    
    UNION ALL
    
    -- Door force health
    SELECT 
        'door_force' as metric_type,
        COUNT(*) as total_measurements,
        AVG(measurement_value) as avg_value,
        COUNT(CASE WHEN measurement_value > 110 THEN 1 END) as non_compliant_count
    FROM ce_test_measurements ctm
    JOIN ce_test_sessions cts ON ctm.test_session_id = cts.id
    WHERE cts.building_id = :building_id
      AND ctm.measurement_type = 'door_force'
      AND ctm.timestamp >= CURRENT_DATE - INTERVAL '1 year'
),
defect_summary AS (
    SELECT 
        COUNT(*) as total_defects,
        COUNT(CASE WHEN status NOT IN ('closed', 'verified') THEN 1 END) as open_defects,
        COUNT(CASE WHEN severity = 'critical' AND status NOT IN ('closed', 'verified') THEN 1 END) as critical_defects
    FROM defects
    WHERE building_id = :building_id
      AND discovered_at >= CURRENT_DATE - INTERVAL '1 year'
)
SELECT 
    bm.metric_type,
    bm.total_measurements,
    bm.avg_value,
    bm.non_compliant_count,
    ROUND((bm.total_measurements - bm.non_compliant_count)::numeric / bm.total_measurements * 100, 1) as compliance_percentage,
    ds.total_defects,
    ds.open_defects,
    ds.critical_defects
FROM building_metrics bm
CROSS JOIN defect_summary ds
ORDER BY compliance_percentage ASC;
