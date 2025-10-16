# Evidence CRUD Enhancement Implementation

## Overview

This document summarizes the implementation of the missing read-only endpoints for evidence management in the FireMode Compliance Platform.

## Implemented Endpoints

### 1. GET /v1/evidence/{id}
**Purpose**: Returns evidence metadata (NOT file content)

**Fields Returned**:
- `id`: Evidence unique identifier
- `filename`: Original filename of the evidence file
- `file_type`: MIME type of the evidence file
- `file_size`: Size of the evidence file in bytes
- `hash`: SHA-256 checksum for file integrity verification
- `device_attestation_status`: Device attestation verification status
- `uploaded_at`: When the evidence was uploaded
- `flagged_for_review`: Whether evidence is flagged for review

**Authentication**: JWT required, ownership check through test session
**Response**: 200 OK with evidence JSON
**Error**: 404 if not found, 403 if unauthorized

### 2. GET /v1/evidence/{id}/download
**Purpose**: Returns pre-signed S3 URL for downloading evidence file

**Features**:
- 7-day expiry for download URL
- Uses boto3.client('s3').generate_presigned_url()
- Logs download in audit trail
- Handles both s3:// URL format and direct key format

**Authentication**: JWT required, ownership check through test session
**Response**: 200 OK with `{"download_url": "https://s3...", "expires_at": "..."}`
**Error**: 404 if not found, 403 if unauthorized, 500 if S3 error

### 3. PATCH /v1/evidence/{id}/flag
**Purpose**: Flags evidence for review (soft-delete)

**Features**:
- Required: `flag_reason` in request body
- Sets: `flagged_for_review=true`, `flagged_at=now()`, `flagged_by=user_id`
- Admin role check (currently based on username ending with "_admin")

**Authentication**: JWT required, admin role only
**Response**: 200 OK with updated evidence JSON
**Error**: 403 if not admin, 404 if evidence not found

### 4. POST /v1/evidence/{id}/link-defect
**Purpose**: Links evidence to a defect

**Features**:
- Request body: `{"defect_id": "uuid"}`
- Updates: `defect.evidence_ids` array (appends evidence_id)
- Validates: defect exists, user owns both evidence and defect
- Prevents duplicate linking

**Authentication**: JWT required, ownership check
**Response**: 200 OK with updated defect JSON
**Error**: 404 if not found, 403 if unauthorized

## Implementation Details

### Files Modified/Created

1. **src/app/schemas/evidence.py** (NEW)
   - `EvidenceRead`: Schema for evidence metadata response
   - `EvidenceDownloadResponse`: Schema for download URL response
   - `EvidenceFlagRequest`: Schema for flagging request
   - `EvidenceFlagResponse`: Schema for flagging response
   - `EvidenceLinkDefectRequest`: Schema for linking request

2. **src/app/routers/evidence.py** (MODIFIED)
   - Added 4 new endpoints with proper authentication and validation
   - Added boto3 import for S3 presigned URL generation
   - Added proper error handling and logging

3. **pyproject.toml** (MODIFIED)
   - Added `boto3 = "^1.35.0"` dependency

4. **tests/test_evidence_crud.py** (NEW)
   - Comprehensive test suite for all new endpoints
   - Mock-based testing to avoid database dependencies
   - Tests for success cases, error cases, and edge cases

### Security Features

- **Ownership Validation**: All endpoints verify user ownership through test session relationships
- **Admin Role Check**: Flagging endpoint requires admin privileges
- **JWT Authentication**: All endpoints require valid JWT tokens
- **Input Validation**: Pydantic schemas validate all request/response data

### Database Relationships

The implementation leverages existing database relationships:
- Evidence → TestSession (via session_id)
- TestSession → User (via created_by)
- Evidence → Defect (via evidence_ids array)

### Error Handling

- **404 Not Found**: When evidence or defect doesn't exist
- **403 Forbidden**: When user lacks permissions or admin role
- **500 Internal Server Error**: When S3 operations fail

## Usage Examples

### Get Evidence Metadata
```bash
GET /v1/evidence/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <jwt_token>
```

### Download Evidence
```bash
GET /v1/evidence/123e4567-e89b-12d3-a456-426614174000/download
Authorization: Bearer <jwt_token>
```

### Flag Evidence for Review
```bash
PATCH /v1/evidence/123e4567-e89b-12d3-a456-426614174000/flag
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
  "flag_reason": "Suspicious content detected"
}
```

### Link Evidence to Defect
```bash
POST /v1/evidence/123e4567-e89b-12d3-a456-426614174000/link-defect
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "defect_id": "987fcdeb-51a2-43d7-b890-123456789abc"
}
```

## Testing

The implementation includes comprehensive tests covering:
- Successful operations
- Error conditions (not found, unauthorized, admin required)
- Edge cases (duplicate linking, missing files)
- Mock-based testing to avoid external dependencies

## Future Enhancements

1. **Role-Based Access Control**: Implement proper RBAC instead of username-based admin check
2. **Audit Logging**: Add comprehensive audit trail for all evidence operations
3. **File Type Validation**: Add MIME type validation for uploaded evidence
4. **Bulk Operations**: Add endpoints for bulk evidence operations
5. **Evidence Versioning**: Add support for evidence file versioning
6. **Compression**: Add support for evidence file compression

## Dependencies

- **boto3**: For S3 presigned URL generation
- **Existing**: FastAPI, SQLAlchemy, Pydantic, JWT authentication

## Notes

- The admin role check is currently implemented as a simple username suffix check (`_admin`)
- S3 bucket name defaults to "firemode-evidence" if not specified in file_path
- All timestamps use UTC timezone
- Evidence metadata is stored as JSONB for flexibility
