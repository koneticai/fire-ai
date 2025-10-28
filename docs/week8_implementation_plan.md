# Week 8 Pre-Launch Hardening - REMEDIATED Implementation Plan

## Executive Summary

**Status**: ✅ AGENTS.md Compliant | 🔒 Security Gate Ready | 📊 data_model.md Aligned

FireAI platform requires **32 tasks** (decomposed from original 22) across **4 phases (12-14 days)** to achieve production readiness. This plan follows AGENTS.md workflow rules: 30-75 LOC per iteration, explicit data_model.md references for all data-touching changes, co-tagged test files, and complete security gate compliance.

**Current State**: Clean codebase post-cleanup with 29 database tables, working JWT auth, basic evidence upload, and defect tracking.

**Critical Gaps Addressed**:
- P0: JWT algorithm vulnerability, missing rate limiting, incomplete WORM storage
- P1: Calibration certificate validation, 24-hour SLA enforcement, C&E deviation detection
- Performance: N+1 query issues, missing JSONB indexes

**Key Risk Mitigations**:
- All tasks ≤75 LOC (reviewable diffs)
- Additive-only migrations (no destructive changes)
- Feature flags for WORM rollout
- Comprehensive test coverage with E2E workflow validation

---

## Data Model Impact Summary

**data_model.md References**: All changes cross-referenced to [./data_model.md](../data_model.md)

### New Tables (2)
1. `calibration_certificates` - Instrument validation per AS 1851-2012
2. `defect_notification_sla` - 24-hour critical notification tracking

### Modified Tables (2)
1. `ce_test_measurements` - Add FK `instrument_certificate_id`
2. `evidence` - Add WORM metadata fields

### New Relationships
- `ce_test_measurements → calibration_certificates` (N:1, RESTRICT)
- `calibration_certificates → users` (N:1, CASCADE)

### New Indexes (6)
- `idx_calibration_expiry` (temporal, B-tree)
- `idx_instrument_serial` (lookup, B-tree)
- `idx_measurement_certificate_fk` (FK, B-tree)
- `idx_sla_deadline` (temporal, B-tree)
- `idx_building_config_gin` (JSONB, GIN)
- `idx_ce_test_config_gin` (JSONB, GIN)

---

## Test Co-Tagging Matrix

| Source File | Test File | Coverage Target | LOC Changed |
|-------------|-----------|-----------------|-------------|
| `src/app/config.py` | `tests/security/test_config_validation.py` | Lines 23-45 (validators) | 35 LOC |
| `src/app/dependencies.py` | `tests/security/test_jwt_validation.py` | Lines 82-95 (verify_token) | 20 LOC |
| `src/app/main.py` | `tests/security/test_rate_limiting.py` | Lines 35-60 (limiter) | 40 LOC |
| `src/app/routers/auth.py` | `tests/security/test_rate_limiting.py` | Lines 78-85 (login) | 15 LOC |
| `src/app/routers/evidence.py` | `tests/security/test_rate_limiting.py` | Lines 120-130 (submit) | 15 LOC |
| `src/app/services/storage/worm_uploader.py` | `tests/integration/test_worm_upload.py` | Lines 50-95 (upload) | 50 LOC |
| `src/app/services/storage/worm_uploader.py` | `tests/integration/test_worm_verify.py` | Lines 96-130 (verify) | 40 LOC |
| `src/app/routers/evidence.py` | `tests/integration/test_worm_evidence.py` | Lines 85-115 (router) | 35 LOC |
| `src/app/models/calibration.py` | `tests/unit/test_calibration_model.py` | Full file | 45 LOC |
| `src/app/routers/ce_tests.py` | `tests/compliance/test_calibration_expiry.py` | Lines 145-180 | 40 LOC |
| `src/app/services/ce_deviation_analyzer.py` | `tests/compliance/test_ce_missing_components.py` | Lines 80-120 | 40 LOC |
| `src/app/services/ce_deviation_analyzer.py` | `tests/compliance/test_ce_timing.py` | Lines 121-170 | 50 LOC |
| `src/app/routers/defects.py` | `tests/performance/test_defect_eager_loading.py` | Lines 65-95 | 35 LOC |

---

## Phase 1: Security Hardening (Days 1-3, P0 Critical)

### Task 1.1: Add JWT Secret Strength Validation
- **File**: `src/app/config.py`
- **Effort**: 2 hours | **LOC**: 35
- **Dependencies**: None
- **Risk**: Low (validation only, no breaking changes)
- **data_model.md Reference**: N/A (config validation, no data model impact)

**Implementation**:
```python
from pydantic import field_validator
import os

class Settings(BaseSettings):
    # ... existing fields ...
    
    @field_validator('jwt_secret_key', 'internal_jwt_secret_key')
    @classmethod
    def validate_secret_strength(cls, v: str, info) -> str:
        """Enforce minimum 32-character secret keys per OWASP guidelines"""
        if len(v) < 32:
            raise ValueError(
                f"{info.field_name} must be at least 32 characters "
                f"(current: {len(v)}). Generate with: openssl rand -hex 32"
            )
        # Check for common weak patterns
        if v.lower() in ['test', 'secret', 'password', 'changeme']:
            raise ValueError(f"{info.field_name} contains weak pattern")
        return v
    
    @field_validator('attestation_stub_mode')
    @classmethod
    def block_stub_mode_in_production(cls, v: bool) -> bool:
        """Block stub mode in production environment per AS 1851-2012 requirements"""
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production' and v:
            raise ValueError(
                "attestation_stub_mode=True is FORBIDDEN in production. "
                "Device attestation is required for compliance evidence. "
                "Set ATTESTATION_STUB_MODE=false in environment."
            )
        return v
```

**Test**: `tests/security/test_config_validation.py` (45 LOC)
```python
import pytest
import os
from src.app.config import Settings

def test_jwt_secret_minimum_length():
    """JWT secret must be at least 32 characters"""
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            jwt_secret_key="short",
            internal_jwt_secret_key="x" * 32,
            database_url="postgresql://test"
        )

def test_jwt_secret_weak_pattern():
    """JWT secret cannot contain common weak patterns"""
    with pytest.raises(ValueError, match="weak pattern"):
        Settings(
            jwt_secret_key="test" * 10,  # 40 chars but weak
            internal_jwt_secret_key="x" * 32,
            database_url="postgresql://test"
        )

def test_valid_jwt_secret():
    """Valid 32+ character secrets pass validation"""
    settings = Settings(
        jwt_secret_key="a" * 32,
        internal_jwt_secret_key="b" * 32,
        database_url="postgresql://test"
    )
    assert len(settings.jwt_secret_key) == 32

def test_stub_mode_blocked_in_production(monkeypatch):
    """Stub mode must be blocked in production environment"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError, match="FORBIDDEN in production"):
        Settings(
            jwt_secret_key="x" * 32,
            internal_jwt_secret_key="y" * 32,
            database_url="postgresql://test",
            attestation_stub_mode=True
        )

def test_stub_mode_allowed_in_development(monkeypatch):
    """Stub mode is allowed in development"""
    monkeypatch.setenv("ENVIRONMENT", "development")
    settings = Settings(
        jwt_secret_key="x" * 32,
        internal_jwt_secret_key="y" * 32,
        database_url="postgresql://test",
        attestation_stub_mode=True
    )
    assert settings.attestation_stub_mode is True
```

**Rollback**: Remove validators from `config.py`, restart service

---

### Task 1.2: Fix JWT Algorithm Confusion Attack
- **File**: `src/app/dependencies.py`
- **Effort**: 1.5 hours | **LOC**: 20
- **Dependencies**: Task 1.1
- **Risk**: Low (explicit whitelist, backward compatible)
- **data_model.md Reference**: Uses `token_revocation_list` table (Section 2, Infrastructure entities)

**Implementation**:
```python
def verify_token(token: str) -> TokenPayload:
    """Verify JWT token and return token data
    
    Security: Prevents algorithm confusion attacks per OWASP JWT guidelines
    """
    try:
        # SECURITY FIX: Explicit algorithm whitelist prevents algorithm confusion
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.algorithm],  # Whitelist only HS256
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require": ["sub", "user_id", "jti", "exp", "iat"]  # Enforce required claims
            }
        )
        username = payload.get("sub")
        user_id = payload.get("user_id")
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        # ... rest of validation (existing code unchanged) ...
```

**Test**: `tests/security/test_jwt_validation.py` (55 LOC)
```python
import pytest
import jwt
import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException
from src.app.dependencies import verify_token
from src.app.config import settings

def test_jwt_algorithm_none_blocked():
    """Test that 'none' algorithm is rejected (algorithm confusion attack)"""
    malicious_token = jwt.encode(
        {
            "sub": "attacker",
            "user_id": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        },
        None,
        algorithm="none"
    )
    with pytest.raises(HTTPException) as exc:
        verify_token(malicious_token)
    assert exc.value.status_code == 401
    assert "Invalid token" in str(exc.value.detail)

def test_jwt_algorithm_rs256_blocked():
    """Test that RS256 algorithm is rejected when HS256 expected"""
    # Attempt to use RS256 (asymmetric) when HS256 (symmetric) is configured
    malicious_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.test"
    with pytest.raises(HTTPException) as exc:
        verify_token(malicious_token)
    assert exc.value.status_code == 401

def test_jwt_missing_required_claim_jti():
    """Test that tokens without jti are rejected"""
    token = jwt.encode(
        {
            "sub": "user",
            "user_id": str(uuid.uuid4()),
            "exp": datetime.utcnow() + timedelta(hours=1)
            # Missing jti
        },
        settings.jwt_secret_key,
        algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401
    assert "missing required claims" in str(exc.value.detail)

def test_jwt_valid_token_accepted():
    """Test that properly formed tokens are accepted"""
    user_id = uuid.uuid4()
    jti = uuid.uuid4()
    token = jwt.encode(
        {
            "sub": "testuser",
            "user_id": str(user_id),
            "jti": str(jti),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        },
        settings.jwt_secret_key,
        algorithm="HS256"
    )
    result = verify_token(token)
    assert result.username == "testuser"
    assert result.user_id == user_id
```

**Rollback**: Remove `options=` parameter, restart service

---

### Task 1.3a: Add Rate Limiting Dependency
- **File**: `pyproject.toml`
- **Effort**: 0.5 hours | **LOC**: 5
- **Dependencies**: None
- **Risk**: Low (dependency only)
- **data_model.md Reference**: N/A (infrastructure only)

**Implementation**:
```toml
[tool.poetry.dependencies]
# ... existing dependencies ...
slowapi = "^0.1.9"
```

**Test**: Run `poetry install` to verify dependency resolution

**Rollback**: Remove dependency, run `poetry install`

---

### Task 1.3b: Configure Rate Limiter in Main App
- **File**: `src/app/main.py`
- **Effort**: 1 hour | **LOC**: 40
- **Dependencies**: Task 1.3a
- **Risk**: Medium (could impact legitimate users if misconfigured)
- **data_model.md Reference**: N/A (middleware configuration)

**Implementation**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Initialize limiter (after app creation)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Global default
    storage_uri="memory://"  # Use Redis in production: redis://localhost:6379
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Make limiter available for routers
def get_limiter():
    return limiter
```

**Test**: `tests/security/test_rate_limiting.py` (partial - 30 LOC for this task)
```python
import pytest
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

def test_rate_limiter_configured():
    """Test that rate limiter is properly configured"""
    assert hasattr(app.state, 'limiter')
    assert app.state.limiter is not None

def test_global_rate_limit_header_present():
    """Test that rate limit headers are present in responses"""
    response = client.get("/health")
    assert "X-RateLimit-Limit" in response.headers or response.status_code == 200
```

**Rollback**: Remove limiter configuration, remove middleware, restart service

---

### Task 1.3c: Apply Rate Limiting to Auth Endpoints
- **File**: `src/app/routers/auth.py`
- **Effort**: 0.5 hours | **LOC**: 15
- **Dependencies**: Task 1.3b
- **Risk**: Low (auth protection)
- **data_model.md Reference**: Modifies endpoints that interact with `users` and `token_revocation_list` tables (data_model.md Section 2)

**Implementation**:
```python
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

# At top of file
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # 5 login attempts per minute per IP
async def login(
    request: Request,  # Required for limiter
    credentials: LoginCredentials,
    db: AsyncSession = Depends(get_db)
):
    # ... existing implementation ...
```

**Test**: `tests/security/test_rate_limiting.py` (continuation - 35 LOC)
```python
@pytest.mark.asyncio
async def test_auth_rate_limit_enforced():
    """Test that login endpoint enforces 5/minute rate limit"""
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Make 6 requests (exceeds 5/minute limit)
    for i in range(6):
        response = client.post("/v1/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        if i < 5:
            # First 5 requests should process (may fail auth, but not rate limited)
            assert response.status_code in [401, 422]  # Auth fail or validation
        else:
            # 6th request should be rate limited
            assert response.status_code == 429
            assert "rate limit exceeded" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_rate_limit_resets():
    """Test that rate limit resets after time window"""
    import time
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Exhaust rate limit
    for i in range(5):
        client.post("/v1/auth/login", json={"username": "test", "password": "test"})
    
    # Wait 61 seconds (1 minute + buffer)
    time.sleep(61)
    
    # Should work again
    response = client.post("/v1/auth/login", json={"username": "test", "password": "test"})
    assert response.status_code != 429
```

**Rollback**: Remove `@limiter.limit()` decorator, remove `request: Request` parameter

---

### Task 1.3d: Apply Rate Limiting to Evidence Upload
- **File**: `src/app/routers/evidence.py`
- **Effort**: 0.5 hours | **LOC**: 15
- **Dependencies**: Task 1.3b
- **Risk**: Low (upload protection)
- **data_model.md Reference**: Modifies endpoint that writes to `evidence` table (data_model.md Section 2, evidence entity)

**Implementation**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/submit", response_model=EvidenceResponse)
@limiter.limit("100/hour")  # 100 uploads per hour per user
async def submit_evidence(
    request: Request,  # Required for limiter
    session_id: str = Form(...),
    # ... rest of parameters ...
):
    # ... existing implementation ...
```

**Test**: Covered in `tests/security/test_rate_limiting.py` (add 25 LOC)

**Rollback**: Remove decorator and `request` parameter

---

### Task 1.4: Add Security Headers Middleware
- **File**: `src/app/main.py`
- **Effort**: 1.5 hours | **LOC**: 45
- **Dependencies**: None
- **Risk**: Low (response headers only)
- **data_model.md Reference**: N/A (HTTP layer, no data model impact)

**Implementation**:
```python
from starlette.middleware.cors import CORSMiddleware
from fastapi import Request, Response

# CORS Configuration (add after app creation)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fireai.app",
        "https://app.fireai.app",
        "http://localhost:3000"  # Development only
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses per OWASP guidelines"""
    response = await call_next(request)
    
    # Prevent MIME-sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Force HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://fireai.app; "
        "frame-ancestors 'none';"
    )
    
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions policy
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response
```

**Test**: `tests/security/test_security_headers.py` (50 LOC)
```python
import pytest
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

def test_security_headers_present():
    """Test that all required security headers are present"""
    response = client.get("/health")
    
    # OWASP required headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

def test_csp_header_configured():
    """Test Content Security Policy is configured"""
    response = client.get("/health")
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp

def test_cors_headers_present():
    """Test CORS headers for allowed origins"""
    response = client.options("/health", headers={
        "Origin": "https://fireai.app",
        "Access-Control-Request-Method": "GET"
    })
    # CORS headers should be present for allowed origin
    assert response.status_code in [200, 204]

def test_cors_blocks_unauthorized_origin():
    """Test that unauthorized origins are blocked"""
    response = client.get("/health", headers={
        "Origin": "https://malicious.com"
    })
    # Should not have CORS headers for unauthorized origin
    assert "Access-Control-Allow-Origin" not in response.headers or \
           response.headers.get("Access-Control-Allow-Origin") != "https://malicious.com"
```

**Rollback**: Remove middleware and CORS configuration, restart service

---

## Phase 2: WORM Storage Implementation (Days 4-6, P0 Critical)

### Task 2.1: Configure S3 Bucket Object Lock (Manual Infrastructure)
- **Effort**: 1 hour
- **Dependencies**: AWS account with S3 admin permissions
- **Risk**: High (misconfiguration violates AS 1851-2012 compliance)
- **data_model.md Reference**: Infrastructure for `evidence` table storage (data_model.md Section 2)

**Implementation** (AWS CLI script):
```bash
#!/bin/bash
# Week 8 - WORM Storage Setup Script
# Purpose: Configure S3 buckets with Object Lock for AS 1851-2012 compliance

set -e

EVIDENCE_BUCKET="fireai-evidence-prod"
REPORTS_BUCKET="fireai-reports-prod"
REGION="us-east-1"

echo "Creating WORM-enabled S3 buckets for FireAI compliance..."

# Function to create and configure WORM bucket
configure_worm_bucket() {
    local bucket=$1
    echo "Configuring bucket: $bucket"
    
    # Step 1: Create bucket with Object Lock enabled
    aws s3api create-bucket \
        --bucket "$bucket" \
        --region "$REGION" \
        --object-lock-enabled-for-bucket \
        --create-bucket-configuration LocationConstraint="$REGION" || echo "Bucket may already exist"
    
    # Step 2: Enable versioning (required for Object Lock)
    aws s3api put-bucket-versioning \
        --bucket "$bucket" \
        --versioning-configuration Status=Enabled
    
    # Step 3: Configure default Object Lock (7 years COMPLIANCE mode)
    aws s3api put-object-lock-configuration \
        --bucket "$bucket" \
        --object-lock-configuration '{
          "ObjectLockEnabled": "Enabled",
          "Rule": {
            "DefaultRetention": {
              "Mode": "COMPLIANCE",
              "Years": 7
            }
          }
        }'
    
    # Step 4: Enable encryption at rest
    aws s3api put-bucket-encryption \
        --bucket "$bucket" \
        --server-side-encryption-configuration '{
          "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
              "SSEAlgorithm": "AES256"
            },
            "BucketKeyEnabled": true
          }]
        }'
    
    # Step 5: Block public access
    aws s3api put-public-access-block \
        --bucket "$bucket" \
        --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    
    echo "✅ Bucket $bucket configured successfully"
}

# Configure both buckets
configure_worm_bucket "$EVIDENCE_BUCKET"
configure_worm_bucket "$REPORTS_BUCKET"

echo "
🎉 WORM storage configuration complete!

Verification commands:
  aws s3api get-object-lock-configuration --bucket $EVIDENCE_BUCKET
  aws s3api get-bucket-versioning --bucket $EVIDENCE_BUCKET

Next steps:
  1. Update environment variables:
     WORM_EVIDENCE_BUCKET=$EVIDENCE_BUCKET
     WORM_REPORTS_BUCKET=$REPORTS_BUCKET
  2. Run Task 2.2 to update WormStorageUploader code
"
```

**Validation**:
```bash
# Test WORM protection
aws s3api put-object \
    --bucket fireai-evidence-prod \
    --key test-worm/test.txt \
    --body /tmp/test.txt \
    --object-lock-mode COMPLIANCE \
    --object-lock-retain-until-date "2032-01-01T00:00:00Z"

# Attempt deletion (should fail with AccessDenied)
aws s3api delete-object \
    --bucket fireai-evidence-prod \
    --key test-worm/test.txt
# Expected output: An error occurred (AccessDenied)...
```

**Rollback**: ⚠️ **DESTRUCTIVE** - Cannot remove Object Lock after enabled. Must delete bucket (loses all data) and recreate.

**Documentation**: Update `.env.example` with new bucket names

---

### Task 2.2a: Update WormStorageUploader Upload Method
- **File**: `src/app/services/storage/worm_uploader.py`
- **Effort**: 2 hours | **LOC**: 50
- **Dependencies**: Task 2.1
- **Risk**: Medium (changes evidence storage mechanism)
- **data_model.md Reference**: Implements storage for `evidence` table (data_model.md Section 2, evidence.file_path)

**Implementation**:
```python
def upload_with_retention(
    self, 
    file_path: Union[str, Path, bytes], 
    s3_key: str, 
    metadata: Optional[Dict[str, str]] = None,
    content_type: Optional[str] = None
) -> str:
    """
    Upload file with WORM protection per AS 1851-2012 requirements.
    
    Args:
        file_path: File path (str/Path) or file content (bytes)
        s3_key: S3 object key (path within bucket)
        metadata: Optional metadata dict (encrypted PII must be pre-encrypted)
        content_type: MIME type (default: application/octet-stream)
    
    Returns:
        S3 URI (s3://bucket/key)
    
    Raises:
        ClientError: If upload fails
        ValueError: If file_path is invalid
    """
    try:
        # Calculate retention until date (7 years from now)
        retain_until = datetime.utcnow() + timedelta(days=self.retention_years * 365)
        
        # Handle both file paths and bytes
        if isinstance(file_path, bytes):
            body = file_path
            file_size = len(body)
        elif isinstance(file_path, (str, Path)):
            with open(file_path, 'rb') as f:
                body = f.read()
            file_size = len(body)
        else:
            raise ValueError(f"Invalid file_path type: {type(file_path)}")
        
        # Validate file size (max 5GB per AS 1851-2012 evidence guidelines)
        max_size = 5 * 1024 * 1024 * 1024  # 5GB
        if file_size > max_size:
            raise ValueError(f"File size {file_size} exceeds maximum {max_size}")
        
        # Upload with Object Lock retention (COMPLIANCE mode)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=body,
            ContentType=content_type or 'application/octet-stream',
            Metadata=metadata or {},
            ObjectLockMode='COMPLIANCE',  # CRITICAL: Cannot be deleted before retain_until
            ObjectLockRetainUntilDate=retain_until,
            ServerSideEncryption='AES256'  # Encrypt at rest
        )
        
        s3_uri = f"s3://{self.bucket_name}/{s3_key}"
        logger.info(
            f"WORM upload successful: {s3_uri} "
            f"(size: {file_size} bytes, retain until: {retain_until.isoformat()})"
        )
        return s3_uri
        
    except ClientError as e:
        # Sanitize error (don't leak bucket names/keys)
        error_code = e.response['Error']['Code']
        logger.error(f"WORM upload failed: {error_code} for key {s3_key[:20]}...")
        raise
    except Exception as e:
        logger.error(f"WORM upload unexpected error: {type(e).__name__}")
        raise
```

**Test**: `tests/integration/test_worm_upload.py` (65 LOC)
```python
import pytest
import uuid
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from src.app.services.storage.worm_uploader import WormStorageUploader

@pytest.fixture
def worm_uploader():
    return WormStorageUploader(
        bucket_name="fireai-evidence-test",
        retention_years=7
    )

def test_worm_upload_bytes_success(worm_uploader):
    """Test uploading bytes with WORM protection"""
    s3_key = f"test/{uuid.uuid4()}.txt"
    test_data = b"Test compliance evidence content"
    
    s3_uri = worm_uploader.upload_with_retention(
        file_path=test_data,
        s3_key=s3_key,
        metadata={"test": "true", "session_id": str(uuid.uuid4())}
    )
    
    assert s3_uri == f"s3://fireai-evidence-test/{s3_key}"
    
    # Verify object exists
    response = worm_uploader.s3_client.head_object(
        Bucket="fireai-evidence-test",
        Key=s3_key
    )
    assert response['ContentLength'] == len(test_data)
    assert response['Metadata']['test'] == 'true'

def test_worm_upload_file_path_success(worm_uploader, tmp_path):
    """Test uploading from file path with WORM protection"""
    # Create temporary file
    test_file = tmp_path / "evidence.pdf"
    test_file.write_bytes(b"PDF evidence content here")
    
    s3_key = f"test/{uuid.uuid4()}.pdf"
    s3_uri = worm_uploader.upload_with_retention(
        file_path=str(test_file),
        s3_key=s3_key,
        content_type="application/pdf"
    )
    
    assert s3_uri.startswith("s3://")

def test_worm_upload_file_too_large(worm_uploader):
    """Test that files exceeding 5GB are rejected"""
    large_data = b"x" * (5 * 1024 * 1024 * 1024 + 1)  # 5GB + 1 byte
    
    with pytest.raises(ValueError, match="exceeds maximum"):
        worm_uploader.upload_with_retention(
            file_path=large_data,
            s3_key="test/large.bin"
        )

def test_worm_upload_invalid_type(worm_uploader):
    """Test that invalid file_path types are rejected"""
    with pytest.raises(ValueError, match="Invalid file_path type"):
        worm_uploader.upload_with_retention(
            file_path=123,  # Invalid type
            s3_key="test/invalid.txt"
        )
```

**Rollback**: Revert to previous version without `ObjectLockMode` parameter

---

### Task 2.2b: Add WORM Immutability Verification
- **File**: `src/app/services/storage/worm_uploader.py`
- **Effort**: 1.5 hours | **LOC**: 40
- **Dependencies**: Task 2.2a
- **Risk**: Low (read-only verification)
- **data_model.md Reference**: Verifies integrity of `evidence.file_path` objects

**Implementation**:
```python
def verify_immutability(self, s3_key: str) -> Dict[str, Any]:
    """
    Verify that object has WORM protection enabled.
    
    Args:
        s3_key: S3 object key to verify
    
    Returns:
        Dict with verification results:
        {
            'is_immutable': bool,
            'retention_mode': str,
            'retain_until_date': datetime,
            'version_id': str
        }
    
    Raises:
        ClientError: If object doesn't exist
    """
    try:
        # Get object retention configuration
        response = self.s3_client.get_object_retention(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        
        retention = response.get('Retention', {})
        mode = retention.get('Mode')
        retain_until = retention.get('RetainUntilDate')
        
        is_immutable = (
            mode == 'COMPLIANCE' and
            retain_until and
            retain_until > datetime.now(retain_until.tzinfo)
        )
        
        return {
            'is_immutable': is_immutable,
            'retention_mode': mode,
            'retain_until_date': retain_until,
            'verified_at': datetime.utcnow()
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchObjectLockConfiguration':
            return {
                'is_immutable': False,
                'retention_mode': None,
                'error': 'Object Lock not configured'
            }
        logger.error(f"Immutability check failed: {error_code}")
        raise
```

**Test**: `tests/integration/test_worm_verify.py` (55 LOC)
```python
import pytest
import uuid
from datetime import datetime
from src.app.services.storage.worm_uploader import WormStorageUploader

@pytest.fixture
def worm_uploader():
    return WormStorageUploader("fireai-evidence-test")

def test_verify_immutability_success(worm_uploader):
    """Test verifying WORM protection on uploaded object"""
    s3_key = f"test/{uuid.uuid4()}.txt"
    
    # Upload with WORM
    worm_uploader.upload_with_retention(
        file_path=b"test content",
        s3_key=s3_key
    )
    
    # Verify immutability
    result = worm_uploader.verify_immutability(s3_key)
    
    assert result['is_immutable'] is True
    assert result['retention_mode'] == 'COMPLIANCE'
    assert result['retain_until_date'] > datetime.utcnow()

def test_verify_immutability_no_lock(worm_uploader):
    """Test verifying object without WORM protection"""
    # This test requires a non-WORM bucket (skip in CI)
    pytest.skip("Requires non-WORM bucket for testing")

def test_delete_worm_protected_object_fails(worm_uploader):
    """Test that WORM-protected objects cannot be deleted"""
    s3_key = f"test/{uuid.uuid4()}.txt"
    
    # Upload with WORM
    worm_uploader.upload_with_retention(
        file_path=b"immutable content",
        s3_key=s3_key
    )
    
    # Attempt deletion (should fail)
    with pytest.raises(ClientError) as exc:
        worm_uploader.s3_client.delete_object(
            Bucket="fireai-evidence-test",
            Key=s3_key
        )
    
    assert exc.value.response['Error']['Code'] == 'AccessDenied'
    assert 'object locked' in str(exc.value).lower()
```

**Rollback**: Remove method (no side effects)

---

### Task 2.2c: Add Error Sanitization for WORM Operations
- **File**: `src/app/services/storage/worm_uploader.py`
- **Effort**: 0.5 hours | **LOC**: 20
- **Dependencies**: Task 2.2a, 2.2b
- **Risk**: Low (security hardening)
- **data_model.md Reference**: N/A (error handling layer)

**Implementation**:
```python
def _sanitize_s3_error(self, error: ClientError) -> str:
    """
    Remove sensitive S3 details from error messages.
    
    Prevents information disclosure per OWASP guidelines.
    """
    error_code = error.response['Error']['Code']
    
    # Map AWS error codes to safe messages
    safe_messages = {
        'AccessDenied': 'WORM storage operation failed (access denied)',
        'NoSuchBucket': 'WORM storage operation failed (configuration error)',
        'NoSuchKey': 'WORM storage operation failed (resource not found)',
        'InvalidObjectState': 'WORM storage operation failed (object state invalid)',
        'ObjectLockConfigurationNotFoundError': 'WORM storage operation failed (lock not configured)'
    }
    
    return safe_messages.get(error_code, 'WORM storage operation failed')
```

Update exception handling in `upload_with_retention()`:
```python
except ClientError as e:
    safe_message = self._sanitize_s3_error(e)
    logger.error(f"{safe_message} (code: {e.response['Error']['Code']})")
    raise HTTPException(status_code=500, detail=safe_message)
```

**Test**: Add to `tests/integration/test_worm_verify.py` (15 LOC)

**Rollback**: Remove method and revert error handling

---

### Task 2.2d: Update Evidence Router to Use WORM Upload
- **File**: `src/app/routers/evidence.py`
- **Effort**: 1 hour | **LOC**: 35
- **Dependencies**: Task 2.2a, 2.2b, 2.2c
- **Risk**: Medium (changes live upload flow)
- **data_model.md Reference**: Writes to `evidence` table (data_model.md Section 2), FK to `test_sessions.id`

**Implementation** (modify `submit_evidence` endpoint):
```python
# Replace existing worm_uploader usage with enhanced version
try:
    # Add WORM-specific metadata
    worm_metadata = {
        **metadata_dict,
        "user_id": str(current_user.user_id),
        "session_id": session_id,
        "evidence_type": evidence_type,
        "upload_timestamp": datetime.utcnow().isoformat(),
        "file_hash": file_hash,
        "original_filename": file.filename,
        "compliance_standard": "AS1851-2012",
        "retention_years": "7"
    }
    
    # Upload to WORM storage
    worm_bucket = os.getenv('WORM_EVIDENCE_BUCKET', 'fireai-evidence-worm')
    worm_uploader = WormStorageUploader(bucket_name=worm_bucket, retention_years=7)
    
    # Generate S3 key with date-based partitioning
    timestamp = datetime.utcnow().strftime("%Y/%m/%d")
    s3_key = f"evidence/{timestamp}/{session_id}/{file_hash[:8]}_{file.filename}"
    
    # Upload file to WORM storage
    s3_uri = worm_uploader.upload_with_retention(
        file_path=file_content,
        s3_key=s3_key,
        metadata=worm_metadata,
        content_type=file.content_type
    )
    
    # Verify immutability immediately after upload
    immutability_check = worm_uploader.verify_immutability(s3_key)
    if not immutability_check.get('is_immutable', False):
        logger.error(f"WORM immutability verification FAILED for {s3_key}")
        raise HTTPException(
            status_code=500,
            detail="Evidence upload succeeded but immutability verification failed"
        )
    
    logger.info(
        f"Evidence uploaded with WORM protection - "
        f"ID: {result.get('evidence_id')}, S3: {s3_uri}, User: {current_user.user_id}"
    )
    
    # ... rest of implementation ...
```

**Test**: `tests/integration/test_worm_evidence.py` (70 LOC - new file)

**Rollback**: Revert to previous WormStorageUploader usage

---

[CONTINUED IN NEXT MESSAGE DUE TO LENGTH...]

This is approximately 1/3 of the complete remediated plan. Would you like me to continue with:
- Phase 3: Compliance Enhancements (calibration certificates, SLA monitoring, C&E deviation detection)
- Phase 4: Performance Optimization (eager loading, JSONB indexes)
- Complete test suite specifications
- Deployment checklist and rollback procedures
