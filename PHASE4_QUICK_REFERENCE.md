# Phase 4 Quick Reference Card

## 🚀 Quick Start

### Deploy Infrastructure
```bash
cd fire-ai
./infra/cloudformation/schema-registry/deploy.sh dev
```

### Seed Database
```bash
export AWS_REGION=ap-southeast-2
python3 tools/dev/seed_schema_dynamodb.py
```

### Configure Service
```bash
export FIRE_SCHEMA_SOURCE=local+ddb
export FIRE_SCHEMA_TABLE=fire-ai-schema-versions
```

### Verify Implementation
```bash
python3 tools/dev/verify_phase4.py
```

---

## 📋 Checklist at a Glance

| # | Item | Status | File |
|---|------|--------|------|
| 1 | CloudFormation template | ✅ | `infra/cloudformation/schema-registry/stack.yml` |
| 2 | DynamoDB table + GSI | ✅ | Table: `fire-ai-schema-versions` |
| 3 | Loader file | ✅ | `services/api/schemas/loader_dynamodb.py` |
| 4 | Registry integration | ✅ | `services/api/schemas/registry.py` |
| 5 | Seed script | ✅ | `tools/dev/seed_schema_dynamodb.py` |
| 6 | Middleware validation | ✅ | `services/api/src/app/middleware/schema_validation.py` |

---

## 🔧 Environment Variables

```bash
# Schema loading strategy
FIRE_SCHEMA_SOURCE=local+ddb     # DB-first with local fallback (default)
FIRE_SCHEMA_SOURCE=local-only    # Local files only (testing)

# DynamoDB configuration
FIRE_SCHEMA_TABLE=fire-ai-schema-versions
AWS_REGION=ap-southeast-2

# Validation settings
FIRE_VALIDATION_ENABLED=true
FIRE_VALIDATION_MODE=strict
FIRE_VALIDATION_WHITELIST=/health,/metrics
FIRE_DEFAULT_VERSION=v1
```

---

## 🧪 Test Commands

```bash
# All tests
cd services/api
python3 -m pytest tests/test_schema_validation_middleware.py -v  # 7 tests
python3 -m pytest tests/test_schema_registry.py -v               # 20 tests

# Verification script
cd ../..
python3 tools/dev/verify_phase4.py                               # 8 checks
```

---

## 📊 DynamoDB Schema

**Table:** `fire-ai-schema-versions`

| Attribute | Type | Key Type | Description |
|-----------|------|----------|-------------|
| `endpoint` | String | HASH | e.g., "POST /results" |
| `version` | String | RANGE | e.g., "v1" |
| `is_active` | String | - | "1" or "0" |
| `schema` | String/Map | - | JSON schema |
| `updated_at` | String | - | ISO timestamp |

**GSI:** `gsi_active_by_endpoint`
- HASH: `endpoint`
- RANGE: `is_active`

---

## 🔄 Fallback Behavior

```
┌──────────────────────┐
│ Request arrives      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Try DB schema        │
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     │ Found?    │
     └─────┬─────┘
       Yes │ No
           │  │
           │  ▼
           │ ┌──────────────────┐
           │ │ Fallback to      │
           │ │ local JSON files │
           │ └────────┬─────────┘
           │          │
           ▼          ▼
      ┌────────────────────┐
      │ Validate request   │
      └────────┬───────────┘
               │
         ┌─────┴─────┐
         │ Valid?    │
         └─────┬─────┘
          Yes  │  No
               │  │
               │  ▼
               │ ┌──────────────┐
               │ │ FIRE-422     │
               │ └──────────────┘
               ▼
      ┌────────────────┐
      │ Continue       │
      └────────────────┘
```

---

## 🐛 Common Issues

### AWS Credentials Error
```bash
# Solution: Use local-only mode
export FIRE_SCHEMA_SOURCE=local-only
```

### Schema Not Found
```bash
# Check local file exists
ls services/api/schemas/requests/post_results_v1.json

# Check DB has schema
aws dynamodb get-item \
  --table-name fire-ai-schema-versions \
  --key '{"endpoint":{"S":"POST /results"},"version":{"S":"v1"}}'
```

### Validation Not Working
```bash
# Check validation is enabled
echo $FIRE_VALIDATION_ENABLED  # should be "true"

# Check middleware is loaded
# (verify in app startup logs)
```

---

## 📖 Example Requests

### Valid Request
```bash
curl -X POST http://localhost:8000/results \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "ST123",
    "assessment_id": "A1",
    "score": 85,
    "completed_at": "2025-10-14T10:00:00Z"
  }'
```

### Invalid Request (Type Mismatch)
```bash
curl -X POST http://localhost:8000/results \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "ST123",
    "assessment_id": "A1",
    "score": "not-a-number",
    "completed_at": "2025-10-14T10:00:00Z"
  }'
```

**Response:**
```json
{
  "error_code": "FIRE-422-TYPE_MISMATCH",
  "message": "Validation failed for 'score' (type)",
  "details": {
    "field": "score",
    "constraint": "type",
    "provided_value": "not-a-number",
    "expected": "number"
  },
  "transaction_id": "FIRE-20251014-103000-550e8400",
  "timestamp": "2025-10-14T10:30:00Z"
}
```

---

## 📁 Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `infra/cloudformation/schema-registry/stack.yml` | CloudFormation template | 75 |
| `services/api/schemas/loader_dynamodb.py` | DynamoDB loader | 54 |
| `services/api/schemas/registry.py` | Schema registry | 227 |
| `services/api/src/app/middleware/schema_validation.py` | Validation middleware | 92 |
| `tools/dev/seed_schema_dynamodb.py` | Seed script | 37 |
| `tools/dev/verify_phase4.py` | Verification script | 271 |

---

## 🔗 Documentation Links

- **Detailed Report:** [PHASE4_VERIFICATION_REPORT.md](PHASE4_VERIFICATION_REPORT.md)
- **Complete Checklist:** [PHASE4_CHECKLIST_COMPLETE.md](PHASE4_CHECKLIST_COMPLETE.md)
- **Summary:** [PHASE4_SUMMARY.md](PHASE4_SUMMARY.md)

---

## ✅ Status

**Phase 4:** ✅ COMPLETE  
**Tests Passing:** 27/27 (100%)  
**Verification:** 8/8 checks pass  
**Production Ready:** YES

---

*Last Updated: October 14, 2025*

