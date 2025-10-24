# C&E Tests API Documentation

## Overview

The C&E (Cause-and-Effect) Tests API provides endpoints for executing cause-and-effect tests with real-time sequence recording, offline capability, and automatic deviation analysis.

## Base URL
```
/v1/ce-tests
```

## Authentication
All endpoints require authentication via JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. Download C&E Scenario

Download a C&E scenario for offline mobile execution.

**Endpoint**: `GET /v1/ce-tests/scenarios/{workflow_id}`

**Parameters**:
- `workflow_id` (path, required): UUID of the compliance workflow

**Response**:
```json
{
  "id": "uuid",
  "name": "Stair Pressurization C&E Test",
  "description": "Cause-and-effect test for stair pressurization system",
  "compliance_standard": "AS1851-2012",
  "workflow_definition": {
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
  "status": "active",
  "created_at": "2025-01-17T10:00:00Z"
}
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/ce-tests/scenarios/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>"
```

### 2. Create C&E Test Session

Create a new C&E test session for execution.

**Endpoint**: `POST /v1/ce-tests/sessions`

**Request Body**:
```json
{
  "test_session_id": "uuid",
  "building_id": "uuid",
  "workflow_id": "uuid",
  "test_type": "stair_pressurization",
  "device_info": {
    "device_id": "mobile-device-123",
    "platform": "ios",
    "app_version": "1.0.0"
  }
}
```

**Response**:
```json
{
  "id": "uuid",
  "test_session_id": "uuid",
  "building_id": "uuid",
  "workflow_id": "uuid",
  "test_type": "stair_pressurization",
  "status": "active",
  "created_at": "2025-01-17T10:00:00Z",
  "offline_sync_ready": true
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/ce-tests/sessions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "test_session_id": "123e4567-e89b-12d3-a456-426614174000",
    "building_id": "123e4567-e89b-12d3-a456-426614174001",
    "workflow_id": "123e4567-e89b-12d3-a456-426614174002",
    "test_type": "stair_pressurization"
  }'
```

### 3. Record Test Step

Record a test step with timing data and evidence.

**Endpoint**: `POST /v1/ce-tests/sessions/{session_id}/steps`

**Parameters**:
- `session_id` (path, required): UUID of the C&E test session

**Request Body**:
```json
{
  "step_id": "step1",
  "action": "Activate Fire Panel",
  "started_at": "2025-01-17T10:00:00Z",
  "completed_at": "2025-01-17T10:00:02.5Z",
  "actual_time": 2.5,
  "expected_time": 2.0,
  "status": "completed",
  "notes": "Panel activated successfully",
  "device_timestamp": "2025-01-17T10:00:00Z",
  "location": {
    "latitude": -33.8688,
    "longitude": 151.2093,
    "accuracy": 5.0
  },
  "evidence_ids": ["photo-123", "video-456"]
}
```

**Response**:
```json
{
  "id": "uuid",
  "step_id": "step1",
  "action": "Activate Fire Panel",
  "actual_time": 2.5,
  "expected_time": 2.0,
  "deviation_seconds": 0.5,
  "status": "completed",
  "validation_status": "passed",
  "evidence_ids": ["photo-123", "video-456"],
  "created_at": "2025-01-17T10:00:02.5Z"
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/ce-tests/sessions/123e4567-e89b-12d3-a456-426614174000/steps" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "step_id": "step1",
    "action": "Activate Fire Panel",
    "started_at": "2025-01-17T10:00:00Z",
    "completed_at": "2025-01-17T10:00:02.5Z",
    "actual_time": 2.5,
    "expected_time": 2.0,
    "status": "completed"
  }'
```

### 4. Complete C&E Test

Complete the C&E test and trigger deviation analysis.

**Endpoint**: `POST /v1/ce-tests/sessions/{session_id}/complete`

**Parameters**:
- `session_id` (path, required): UUID of the C&E test session

**Request Body**:
```json
{
  "completed_at": "2025-01-17T10:05:00Z",
  "overall_status": "completed_with_deviations",
  "device_info": {
    "device_id": "mobile-device-123",
    "platform": "ios",
    "app_version": "1.0.0"
  }
}
```

**Response**:
```json
{
  "id": "uuid",
  "overall_status": "completed_with_deviations",
  "deviations": [
    {
      "step_id": "step1",
      "deviation_seconds": 0.5,
      "severity": "low",
      "description": "Fire panel activation delayed by 0.5 seconds"
    }
  ],
  "generated_faults": [
    {
      "id": "uuid",
      "severity": "low",
      "category": "ce_test_deviation",
      "description": "C&E test deviation: Fire panel activation delayed by 0.5 seconds"
    }
  ],
  "summary": {
    "total_steps": 3,
    "completed_steps": 3,
    "deviations_count": 1,
    "overall_status": "completed_with_deviations"
  }
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/ce-tests/sessions/123e4567-e89b-12d3-a456-426614174000/complete" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "completed_at": "2025-01-17T10:05:00Z",
    "overall_status": "completed_with_deviations"
  }'
```

### 5. Get Session Details

Retrieve detailed information about a C&E test session.

**Endpoint**: `GET /v1/ce-tests/sessions/{session_id}`

**Parameters**:
- `session_id` (path, required): UUID of the C&E test session

**Response**:
```json
{
  "id": "uuid",
  "test_session_id": "uuid",
  "building_id": "uuid",
  "workflow_id": "uuid",
  "test_type": "stair_pressurization",
  "status": "completed",
  "steps": [
    {
      "id": "uuid",
      "step_id": "step1",
      "action": "Activate Fire Panel",
      "actual_time": 2.5,
      "expected_time": 2.0,
      "deviation_seconds": 0.5,
      "status": "completed"
    }
  ],
  "deviations": [
    {
      "step_id": "step1",
      "deviation_seconds": 0.5,
      "severity": "low",
      "description": "Fire panel activation delayed by 0.5 seconds"
    }
  ],
  "workflow": {
    "id": "uuid",
    "name": "Stair Pressurization C&E Test",
    "workflow_definition": {}
  },
  "created_at": "2025-01-17T10:00:00Z",
  "completed_at": "2025-01-17T10:05:00Z"
}
```

**Example**:
```bash
curl -X GET "https://api.fireai.com/v1/ce-tests/sessions/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>"
```

### 6. CRDT Merge

Merge CRDT document for conflict resolution in multi-user scenarios.

**Endpoint**: `POST /v1/ce-tests/sessions/{session_id}/crdt-merge`

**Parameters**:
- `session_id` (path, required): UUID of the C&E test session

**Request Body**:
```json
{
  "document_id": "mobile-doc-123",
  "vector_clock": {
    "mobile-device-123": 1,
    "server": 0
  },
  "changes": [
    {
      "type": "step_completed",
      "step_id": "step1",
      "timestamp": "2025-01-17T10:00:00Z",
      "data": {
        "actual_time": 2.0,
        "status": "completed"
      }
    }
  ],
  "device_info": {
    "device_id": "mobile-device-123",
    "platform": "ios",
    "app_version": "1.0.0"
  }
}
```

**Response**:
```json
{
  "merged_document": {
    "document_id": "mobile-doc-123",
    "vector_clock": {
      "mobile-device-123": 1,
      "server": 1
    },
    "changes": []
  },
  "conflicts_resolved": 0,
  "status": "merged"
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/ce-tests/sessions/123e4567-e89b-12d3-a456-426614174000/crdt-merge" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "mobile-doc-123",
    "vector_clock": {
      "mobile-device-123": 1,
      "server": 0
    },
    "changes": []
  }'
```

### 7. Upload Evidence

Upload evidence with device attestation.

**Endpoint**: `POST /v1/ce-tests/sessions/{session_id}/evidence`

**Parameters**:
- `session_id` (path, required): UUID of the C&E test session

**Request Body**:
```json
{
  "step_id": "step1",
  "evidence_type": "photo",
  "filename": "fire_panel_activation.jpg",
  "mime_type": "image/jpeg",
  "file_size": 1024000,
  "device_attestation": {
    "device_id": "mobile-device-123",
    "platform": "ios",
    "attestation_token": "device-attestation-token-123",
    "timestamp": "2025-01-17T10:00:00Z"
  },
  "location": {
    "latitude": -33.8688,
    "longitude": 151.2093,
    "accuracy": 5.0
  }
}
```

**Response**:
```json
{
  "evidence_id": "uuid",
  "step_id": "step1",
  "evidence_type": "photo",
  "filename": "fire_panel_activation.jpg",
  "file_size": 1024000,
  "device_attestation": {
    "device_id": "mobile-device-123",
    "platform": "ios",
    "verified": true
  },
  "created_at": "2025-01-17T10:00:00Z"
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/ce-tests/sessions/123e4567-e89b-12d3-a456-426614174000/evidence" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "step_id": "step1",
    "evidence_type": "photo",
    "filename": "fire_panel_activation.jpg",
    "mime_type": "image/jpeg",
    "file_size": 1024000
  }'
```

### 8. Sync Offline Results

Sync offline test results with server.

**Endpoint**: `POST /v1/ce-tests/sessions/{session_id}/sync`

**Parameters**:
- `session_id` (path, required): UUID of the C&E test session

**Request Body**:
```json
{
  "steps": [
    {
      "step_id": "step1",
      "action": "Activate Fire Panel",
      "started_at": "2025-01-17T10:00:00Z",
      "completed_at": "2025-01-17T10:00:02.0Z",
      "actual_time": 2.0,
      "expected_time": 2.0,
      "status": "completed",
      "offline_timestamp": "2025-01-17T10:00:00Z"
    }
  ],
  "sync_timestamp": "2025-01-17T10:05:00Z",
  "device_id": "mobile-device-123"
}
```

**Response**:
```json
{
  "synced_steps": [
    {
      "step_id": "step1",
      "status": "synced",
      "server_id": "uuid"
    }
  ],
  "conflicts": [],
  "sync_status": "completed"
}
```

**Example**:
```bash
curl -X POST "https://api.fireai.com/v1/ce-tests/sessions/123e4567-e89b-12d3-a456-426614174000/sync" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "steps": [],
    "sync_timestamp": "2025-01-17T10:05:00Z",
    "device_id": "mobile-device-123"
  }'
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data",
  "errors": [
    {
      "field": "workflow_id",
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
  "detail": "C&E test session not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "actual_time",
      "message": "Actual time must be greater than 0"
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
- **Deviation Analysis**: < 200ms
- **CRDT Merge**: p95 < 500ms
- **Evidence Upload**: < 1s

## Rate Limits

- **Session Creation**: 100 requests/minute
- **Step Recording**: 1000 requests/minute
- **CRDT Merge**: 200 requests/minute
- **Evidence Upload**: 50 requests/minute

## Webhooks

The C&E Tests API supports webhooks for real-time notifications:

### Events
- `ce_test.session.created`
- `ce_test.step.recorded`
- `ce_test.session.completed`
- `ce_test.deviation.detected`
- `ce_test.fault.generated`

### Webhook Payload
```json
{
  "event": "ce_test.session.completed",
  "data": {
    "session_id": "uuid",
    "building_id": "uuid",
    "overall_status": "completed_with_deviations",
    "deviations_count": 1
  },
  "timestamp": "2025-01-17T10:05:00Z"
}
```
