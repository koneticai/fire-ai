# Reports API Documentation

## Overview

The Reports API provides endpoints for generating comprehensive compliance reports with trend analysis, C&E test results, interface test results, and engineer compliance statements.

## Base URL
```
/v1/reports
```

## Authentication
All endpoints require authentication via JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. Generate Report

Generate a comprehensive compliance report.

**Endpoint**: `POST /v1/reports/generate`

**Request Body**:
```json
{
  "building_id": "uuid",
  "test_session_id": "uuid",
  "report_type": "comprehensive",
  "include_ce_tests": true,
  "include_interface_tests": true,
  "include_trends": true,
  "include_calibration_table": true,
  "include_compliance_statement": true,
  "trend_period_years": 3,
  "include_predictions": true,
  "engineer_id": "uuid",
  "date_range": {
    "start_date": "2022-01-17T00:00:00Z",
    "end_date": "2025-01-17T23:59:59Z"
  }
}
```

**Response**:
```json
{
  "report_id": "uuid",
  "status": "generating",
  "estimated_completion_time": "2025-01-17T10:02:00Z",
  "sections": {
    "executive_summary": true,
    "ce_test_results": true,
    "interface_test_results": true,
    "trend_analysis": true,
    "calibration_verification": true,
    "compliance_statement": true
  },
  "data_summary": {
    "total_tests": 45,
    "date_range": {
      "start_date": "2022-01-17T00:00:00Z",
      "end_date": "2025-01-17T23:59:59Z"
    },
    "building_info": {
      "name": "Test Building",
      "address": "123 Test Street"
    }
  }
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/reports/generate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "building_id": "123e4567-e89b-12d3-a456-426614174000",
    "test_session_id": "123e4567-e89b-12d3-a456-426614174001",
    "report_type": "comprehensive",
    "include_trends": true,
    "trend_period_years": 3
  }'
```

### 2. Get Trend Analysis

Retrieve 3-year trend analysis data.

**Endpoint**: `GET /v1/reports/{building_id}/trends`

**Parameters**:
- `building_id` (path, required): UUID of the building

**Query Parameters**:
- `period_years` (optional): Number of years for trend analysis (default: 3)
- `include_predictions` (optional): Include predictive analysis (default: false)

**Response**:
```json
{
  "building_id": "uuid",
  "trends": {
    "pressure_differentials": {
      "floors": {
        "floor_1": {
          "current": 50.2,
          "trend": "stable",
          "change_percentage": 2.1,
          "time_series": [
            {
              "date": "2022-01-17",
              "value": 49.1
            }
          ]
        }
      },
      "statistics": {
        "mean": 50.2,
        "std_dev": 2.1,
        "trend_direction": "stable"
      }
    },
    "air_velocity": {
      "doorways": {
        "doorway_1": {
          "current": 1.2,
          "trend": "decreasing",
          "change_percentage": -5.3,
          "time_series": []
        }
      },
      "statistics": {
        "mean": 1.2,
        "std_dev": 0.1,
        "trend_direction": "decreasing"
      }
    },
    "door_force": {
      "doors": {
        "door_1": {
          "current": 75.5,
          "trend": "increasing",
          "change_percentage": 3.2,
          "time_series": []
        }
      },
      "statistics": {
        "mean": 75.5,
        "std_dev": 2.3,
        "trend_direction": "increasing"
      }
    }
  },
  "predictions": {
    "next_6_months": {
      "pressure_differentials": {
        "predicted_value": 51.2,
        "confidence_interval": [49.8, 52.6]
      }
    }
  },
  "analysis_date": "2025-01-17T10:00:00Z"
}
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/reports/123e4567-e89b-12d3-a456-426614174000/trends?period_years=3&include_predictions=true" \
  -H "Authorization: Bearer <token>"
```

### 3. Get Chart Data

Retrieve chart data for visualizations.

**Endpoint**: `GET /v1/reports/{building_id}/chart-data`

**Parameters**:
- `building_id` (path, required): UUID of the building

**Query Parameters**:
- `chart_type` (optional): Type of chart data (pressure, velocity, force)
- `period_months` (optional): Number of months for chart data (default: 36)

**Response**:
```json
{
  "building_id": "uuid",
  "pressure_charts": {
    "floors": {
      "floor_1": {
        "time_series": [
          {
            "date": "2022-01-17",
            "value": 49.1
          }
        ],
        "trend_lines": {
          "linear": {
            "slope": 0.1,
            "intercept": 49.0
          }
        }
      }
    }
  },
  "velocity_charts": {
    "doorways": {
      "doorway_1": {
        "time_series": [],
        "trend_lines": {}
      }
    }
  },
  "force_charts": {
    "doors": {
      "door_1": {
        "time_series": [],
        "trend_lines": {}
      }
    }
  }
}
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/reports/123e4567-e89b-12d3-a456-426614174000/chart-data?chart_type=pressure&period_months=36" \
  -H "Authorization: Bearer <token>"
```

### 4. Get Report Status

Check the status of a report generation.

**Endpoint**: `GET /v1/reports/{report_id}/status`

**Parameters**:
- `report_id` (path, required): UUID of the report

**Response**:
```json
{
  "report_id": "uuid",
  "status": "completed",
  "progress": 100,
  "created_at": "2025-01-17T10:00:00Z",
  "updated_at": "2025-01-17T10:02:30Z",
  "estimated_completion_time": "2025-01-17T10:02:00Z",
  "sections_completed": [
    "executive_summary",
    "ce_test_results",
    "interface_test_results",
    "trend_analysis",
    "calibration_verification",
    "compliance_statement"
  ],
  "file_size": 2048576,
  "download_ready": true
}
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/reports/123e4567-e89b-12d3-a456-426614174000/status" \
  -H "Authorization: Bearer <token>"
```

### 5. Download Report

Download the generated PDF report.

**Endpoint**: `GET /v1/reports/{report_id}/download`

**Parameters**:
- `report_id` (path, required): UUID of the report

**Response**: PDF file with appropriate headers

**Headers**:
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="compliance_report_2025-01-17.pdf"
Content-Length: 2048576
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/reports/123e4567-e89b-12d3-a456-426614174000/download" \
  -H "Authorization: Bearer <token>" \
  -o "compliance_report.pdf"
```

### 6. Generate Statistical Analysis

Generate statistical analysis for a building.

**Endpoint**: `POST /v1/reports/generate-statistical-analysis`

**Request Body**:
```json
{
  "building_id": "uuid",
  "include_statistics": true,
  "analysis_type": "comprehensive",
  "date_range": {
    "start_date": "2022-01-17T00:00:00Z",
    "end_date": "2025-01-17T23:59:59Z"
  }
}
```

**Response**:
```json
{
  "report_id": "uuid",
  "statistical_analysis": {
    "descriptive_stats": {
      "pressure_differentials": {
        "mean": 50.2,
        "median": 50.1,
        "std_dev": 2.1,
        "min": 45.8,
        "max": 54.3,
        "percentiles": {
          "25th": 48.9,
          "75th": 51.5,
          "95th": 53.2
        }
      }
    },
    "correlation_analysis": {
      "pressure_vs_velocity": 0.85,
      "pressure_vs_force": 0.72
    },
    "confidence_intervals": {
      "pressure_differentials": {
        "95_confidence": [49.8, 50.6],
        "99_confidence": [49.6, 50.8]
      }
    }
  }
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/reports/generate-statistical-analysis" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "building_id": "123e4567-e89b-12d3-a456-426614174000",
    "include_statistics": true
  }'
```

## Report Types

### 1. Comprehensive Report
- **Includes**: All sections (C&E tests, interface tests, trends, calibration, compliance statement)
- **Use Case**: Complete compliance documentation
- **Generation Time**: 5-10 seconds

### 2. Trend Analysis Report
- **Includes**: 3-year trend analysis with predictions
- **Use Case**: Historical analysis and predictive maintenance
- **Generation Time**: 3-5 seconds

### 3. Statistical Analysis Report
- **Includes**: Descriptive statistics, correlations, confidence intervals
- **Use Case**: Data analysis and insights
- **Generation Time**: 2-3 seconds

### 4. Historical Analysis Report
- **Includes**: Historical data analysis over specified period
- **Use Case**: Long-term trend analysis
- **Generation Time**: 5-8 seconds

## Report Sections

### 1. Executive Summary
- Building information
- Overall compliance status
- Key findings and recommendations
- Summary statistics

### 2. C&E Test Results
- Test execution details
- Deviation analysis
- Generated faults
- Evidence documentation

### 3. Interface Test Results
- All 4 interface test types
- Timing validation results
- Pass/fail status
- Compliance verification

### 4. Trend Analysis
- 3-year historical trends
- Pressure differentials per floor
- Air velocity per doorway
- Door force per door
- Predictive insights

### 5. Calibration Verification
- Calibration certificate status
- Equipment verification
- Maintenance schedules
- Compliance tracking

### 6. Compliance Statement
- Engineer review and sign-off
- Digital signature
- License verification
- Regulatory compliance confirmation

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data",
  "errors": [
    {
      "field": "building_id",
      "message": "Invalid UUID format"
    }
  ]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication required"
}
```

### 404 Not Found
```json
{
  "detail": "Report not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "trend_period_years",
      "message": "Trend period must be between 1 and 10 years"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Performance Requirements

- **Trend Analysis**: < 5s for 3-year data
- **Chart Generation**: < 2s
- **PDF Assembly**: < 5s
- **Total Report Generation**: < 10s
- **Statistical Analysis**: < 3s

## Rate Limits

- **Report Generation**: 10 requests/minute
- **Trend Analysis**: 50 requests/minute
- **Chart Data**: 100 requests/minute
- **Report Download**: 20 requests/minute

## Caching

- **Trend Analysis**: Cached for 1 hour
- **Chart Data**: Cached for 30 minutes
- **Statistical Analysis**: Cached for 2 hours
- **Report Status**: Real-time (no caching)

## Webhooks

The Reports API supports webhooks for report generation notifications:

### Events
- `report.generation.started`
- `report.generation.progress`
- `report.generation.completed`
- `report.generation.failed`
- `report.download.ready`

### Webhook Payload
```json
{
  "event": "report.generation.completed",
  "data": {
    "report_id": "uuid",
    "building_id": "uuid",
    "report_type": "comprehensive",
    "file_size": 2048576,
    "download_url": "https://api.fireai.com/v1/reports/uuid/download"
  },
  "timestamp": "2025-01-17T10:02:30Z"
}
```
