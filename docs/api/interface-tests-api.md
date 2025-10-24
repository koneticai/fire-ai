# Interface Tests API Documentation

## Overview

The Interface Tests API provides endpoints for executing interface tests per AS 1851-2012 requirements, including manual override, alarm coordination, shutdown sequence, and sprinkler interface tests.

## Base URL
```
/v1/interface-tests
```

## Authentication
All endpoints require authentication via JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. Get Interface Test Templates

Retrieve available interface test templates.

**Endpoint**: `GET /v1/interface-tests/templates`

**Response**:
```json
[
  {
    "test_type": "manual_override",
    "name": "Manual Override Test",
    "description": "Test manual override functionality for fire panel, BMS, and local switches",
    "timing_requirements": {
      "max_response_time": 3.0,
      "unit": "seconds"
    },
    "steps": [
      {
        "step_name": "Fire Panel Override",
        "action": "Activate fire panel manual override",
        "expected_response_time": 2.0
      },
      {
        "step_name": "BMS Override",
        "action": "Test BMS manual override",
        "expected_response_time": 2.0
      },
      {
        "step_name": "Local Switch Override",
        "action": "Test local switch override",
        "expected_response_time": 2.0
      }
    ]
  },
  {
    "test_type": "alarm_coordination",
    "name": "Alarm Coordination Test",
    "description": "Test alarm coordination sequence from detection to pressurization",
    "timing_requirements": {
      "max_response_time": 10.0,
      "unit": "seconds"
    },
    "steps": [
      {
        "step_name": "Smoke Detection",
        "action": "Activate smoke detector",
        "expected_response_time": 1.0
      },
      {
        "step_name": "Alarm Activation",
        "action": "Verify alarm activation",
        "expected_response_time": 2.0
      },
      {
        "step_name": "Pressurization Start",
        "action": "Verify pressurization system starts",
        "expected_response_time": 7.0
      }
    ]
  },
  {
    "test_type": "shutdown_sequence",
    "name": "Shutdown Sequence Test",
    "description": "Test orderly shutdown sequence",
    "timing_requirements": {
      "max_response_time": 30.0,
      "unit": "seconds"
    },
    "steps": [
      {
        "step_name": "Shutdown Initiation",
        "action": "Initiate system shutdown",
        "expected_response_time": 1.0
      },
      {
        "step_name": "Fan Shutdown",
        "action": "Verify fan shutdown sequence",
        "expected_response_time": 5.0
      },
      {
        "step_name": "System Isolation",
        "action": "Verify system isolation",
        "expected_response_time": 3.0
      }
    ]
  },
  {
    "test_type": "sprinkler_interface",
    "name": "Sprinkler Interface Test",
    "description": "Test sprinkler interface activation response",
    "timing_requirements": {
      "max_response_time": 5.0,
      "unit": "seconds"
    },
    "steps": [
      {
        "step_name": "Sprinkler Activation",
        "action": "Simulate sprinkler activation",
        "expected_response_time": 1.0
      },
      {
        "step_name": "Interface Response",
        "action": "Verify interface response",
        "expected_response_time": 2.0
      },
      {
        "step_name": "System Coordination",
        "action": "Verify system coordination",
        "expected_response_time": 2.0
      }
    ]
  }
]
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/interface-tests/templates" \
  -H "Authorization: Bearer <token>"
```

### 2. Create Interface Test Session

Create a new interface test session.

**Endpoint**: `POST /v1/interface-tests/sessions`

**Request Body**:
```json
{
  "test_session_id": "uuid",
  "building_id": "uuid",
  "test_type": "manual_override",
  "description": "Test manual override functionality"
}
```

**Response**:
```json
{
  "id": "uuid",
  "test_session_id": "uuid",
  "building_id": "uuid",
  "test_type": "manual_override",
  "description": "Test manual override functionality",
  "status": "active",
  "created_at": "2025-01-17T10:00:00Z"
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/interface-tests/sessions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "test_session_id": "123e4567-e89b-12d3-a456-426614174000",
    "building_id": "123e4567-e89b-12d3-a456-426614174001",
    "test_type": "manual_override",
    "description": "Test manual override functionality"
  }'
```

### 3. Record Interface Test Step

Record a test step with timing validation.

**Endpoint**: `POST /v1/interface-tests/sessions/{session_id}/steps`

**Parameters**:
- `session_id` (path, required): UUID of the interface test session

**Request Body**:
```json
{
  "step_name": "Fire Panel Override",
  "action": "Activate fire panel manual override",
  "started_at": "2025-01-17T10:00:00Z",
  "completed_at": "2025-01-17T10:00:02.5Z",
  "response_time": 2.5,
  "status": "completed",
  "notes": "Panel responded within 2.5 seconds",
  "evidence_ids": ["photo-123", "video-456"]
}
```

**Response**:
```json
{
  "id": "uuid",
  "step_name": "Fire Panel Override",
  "action": "Activate fire panel manual override",
  "response_time": 2.5,
  "status": "completed",
  "validation_status": "passed",
  "timing_requirement": 3.0,
  "evidence_ids": ["photo-123", "video-456"],
  "created_at": "2025-01-17T10:00:02.5Z"
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/interface-tests/sessions/123e4567-e89b-12d3-a456-426614174000/steps" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "step_name": "Fire Panel Override",
    "action": "Activate fire panel manual override",
    "started_at": "2025-01-17T10:00:00Z",
    "completed_at": "2025-01-17T10:00:02.5Z",
    "response_time": 2.5,
    "status": "completed"
  }'
```

### 4. Complete Interface Test

Complete the interface test and get results.

**Endpoint**: `POST /v1/interface-tests/sessions/{session_id}/complete`

**Parameters**:
- `session_id` (path, required): UUID of the interface test session

**Request Body**:
```json
{
  "completed_at": "2025-01-17T10:05:00Z",
  "overall_status": "passed"
}
```

**Response**:
```json
{
  "id": "uuid",
  "test_type": "manual_override",
  "overall_status": "passed",
  "steps": [
    {
      "step_name": "Fire Panel Override",
      "response_time": 2.5,
      "validation_status": "passed"
    },
    {
      "step_name": "BMS Override",
      "response_time": 1.8,
      "validation_status": "passed"
    },
    {
      "step_name": "Local Switch Override",
      "response_time": 2.2,
      "validation_status": "passed"
    }
  ],
  "results": {
    "total_steps": 3,
    "passed_steps": 3,
    "failed_steps": 0,
    "average_response_time": 2.17,
    "max_response_time": 2.5,
    "compliance_status": "compliant"
  },
  "generated_faults": [],
  "completed_at": "2025-01-17T10:05:00Z"
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/interface-tests/sessions/123e4567-e89b-12d3-a456-426614174000/complete" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "completed_at": "2025-01-17T10:05:00Z",
    "overall_status": "passed"
  }'
```

### 5. Get Interface Test Session Details

Retrieve detailed information about an interface test session.

**Endpoint**: `GET /v1/interface-tests/sessions/{session_id}`

**Parameters**:
- `session_id` (path, required): UUID of the interface test session

**Response**:
```json
{
  "id": "uuid",
  "test_session_id": "uuid",
  "building_id": "uuid",
  "test_type": "manual_override",
  "description": "Test manual override functionality",
  "status": "completed",
  "steps": [
    {
      "id": "uuid",
      "step_name": "Fire Panel Override",
      "action": "Activate fire panel manual override",
      "response_time": 2.5,
      "status": "completed",
      "validation_status": "passed"
    }
  ],
  "results": {
    "total_steps": 3,
    "passed_steps": 3,
    "failed_steps": 0,
    "average_response_time": 2.17,
    "max_response_time": 2.5,
    "compliance_status": "compliant"
  },
  "created_at": "2025-01-17T10:00:00Z",
  "completed_at": "2025-01-17T10:05:00Z"
}
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/interface-tests/sessions/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>"
```

### 6. List Interface Test Sessions

List interface test sessions with filtering options.

**Endpoint**: `GET /v1/interface-tests/sessions`

**Query Parameters**:
- `building_id` (optional): Filter by building ID
- `test_type` (optional): Filter by test type
- `status` (optional): Filter by status
- `limit` (optional): Number of results to return (default: 50)
- `offset` (optional): Number of results to skip (default: 0)

**Response**:
```json
{
  "sessions": [
    {
      "id": "uuid",
      "test_session_id": "uuid",
      "building_id": "uuid",
      "test_type": "manual_override",
      "status": "completed",
      "created_at": "2025-01-17T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/interface-tests/sessions?building_id=123e4567-e89b-12d3-a456-426614174001&test_type=manual_override" \
  -H "Authorization: Bearer <token>"
```

## Test Types

### 1. Manual Override Test
- **Purpose**: Test manual override functionality for fire panel, BMS, and local switches
- **Timing Requirement**: < 3 seconds response time
- **Steps**: Fire panel override, BMS override, local switch override

### 2. Alarm Coordination Test
- **Purpose**: Test alarm coordination sequence from detection to pressurization
- **Timing Requirement**: < 10 seconds total sequence time
- **Steps**: Smoke detection, alarm activation, pressurization start

### 3. Shutdown Sequence Test
- **Purpose**: Test orderly shutdown sequence
- **Timing Requirement**: < 30 seconds total sequence time
- **Steps**: Shutdown initiation, fan shutdown, system isolation

### 4. Sprinkler Interface Test
- **Purpose**: Test sprinkler interface activation response
- **Timing Requirement**: < 5 seconds response time
- **Steps**: Sprinkler activation, interface response, system coordination

## Timing Validation

The API automatically validates timing requirements per AS 1851-2012:

- **Manual Override**: Response time < 3 seconds
- **Alarm Coordination**: Total sequence time < 10 seconds
- **Shutdown Sequence**: Total sequence time < 30 seconds
- **Sprinkler Interface**: Response time < 5 seconds

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data",
  "errors": [
    {
      "field": "test_type",
      "message": "Invalid test type. Must be one of: manual_override, alarm_coordination, shutdown_sequence, sprinkler_interface"
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
  "detail": "Interface test session not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "response_time",
      "message": "Response time must be greater than 0"
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

- **Session Creation**: p95 < 300ms
- **Step Recording**: p95 < 200ms
- **Test Completion**: p95 < 200ms
- **Session Retrieval**: p95 < 100ms

## Rate Limits

- **Session Creation**: 100 requests/minute
- **Step Recording**: 1000 requests/minute
- **Test Completion**: 200 requests/minute
- **Session Retrieval**: 2000 requests/minute

## Webhooks

The Interface Tests API supports webhooks for real-time notifications:

### Events
- `interface_test.session.created`
- `interface_test.step.recorded`
- `interface_test.session.completed`
- `interface_test.validation.failed`
- `interface_test.fault.generated`

### Webhook Payload
```json
{
  "event": "interface_test.session.completed",
  "data": {
    "session_id": "uuid",
    "building_id": "uuid",
    "test_type": "manual_override",
    "overall_status": "passed",
    "compliance_status": "compliant"
  },
  "timestamp": "2025-01-17T10:05:00Z"
}
```
