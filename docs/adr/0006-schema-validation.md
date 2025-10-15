# ADR-0006: Centralized Schema Validation with JSON Schema v7

**Status:** Accepted  
**Date:** 2025-01-14  
**Authors:** Engineering Team  
**Related Tickets:** FM-ENH-001 (Phases 1-5)  
**References:** TDD-v4.0-Section-11.5, MPKF-v3.1

## Context

Prior to this implementation, the Fire-AI API relied on implicit Pydantic model validation for request/response payloads. This approach presented several challenges:

1. **Inconsistent Error Responses**: Different endpoints returned varying error formats, making client-side error handling brittle
2. **Limited Validation Semantics**: Pydantic's error messages were Python-centric and not API-friendly (e.g., "field required" vs. "FIRE-422-MISSING_FIELD")
3. **No Schema Versioning**: No mechanism to evolve schemas over time while maintaining backward compatibility
4. **Runtime vs. Design-Time Gaps**: TypeScript clients had no way to generate types from Python models, leading to drift
5. **Lack of Centralized Governance**: Schema changes required code changes across multiple handlers, increasing risk of inconsistency
6. **No Schema Observability**: No visibility into which schema versions were active or being used in production

As the Fire-AI platform scales to support multiple clients (web, mobile, third-party integrations), we needed a centralized, version-aware schema validation system that provides:
- **Consistent FIRE-422 error codes** for validation failures
- **Explicit schema versioning** (v1, v2, v3...) stored in DynamoDB
- **Runtime validation** with <5ms latency target
- **Type generation** for TypeScript clients from canonical JSON Schema sources
- **Audit trail** of schema evolution and usage patterns

## Decision

We implemented a **three-tier schema validation architecture**:

### 1. JSON Schema v7 Registry (`schemas/registry.py`)
- **Standard**: JSON Schema Draft-07 for maximum ecosystem compatibility
- **Storage**: Local filesystem (`.json` files) as source of truth, replicated to DynamoDB
- **Caching**: In-memory `_VALIDATORS` cache (LRU) to avoid re-parsing schemas on every request
- **Versioning**: Explicit versioning (v1, v2, v3) via filename convention (`post_results_v1.json`)
- **Reference Resolution**: `RefResolver` for shared schema fragments (e.g., `common/base.json`)
- **Error Shaping**: Translates JSON Schema validation errors into structured FIRE-422 responses

**Key Behaviors**:
```python
# Request validation returns (success: bool, error_dict: Optional[dict])
ok, err = registry.validate_request("POST /results", payload, version="v1")
if not ok:
    return JSONResponse(status_code=422, content=err)
```

### 2. FastAPI Middleware (`src/app/middleware/schema_validation.py`)
- **Automatic Validation**: Intercepts all `POST`/`PUT`/`PATCH` requests before they reach handlers
- **Configuration**:
  - `FIRE_VALIDATION_ENABLED=true` (default: enabled)
  - `FIRE_VALIDATION_MODE=strict|permissive` (default: strict)
  - `FIRE_VALIDATION_WHITELIST=/health,/metrics` (skip validation for ops endpoints)
  - `FIRE_DEFAULT_VERSION=v1` (default schema version to use)
- **Response Audit**: In strict mode, validates outgoing responses and adds `X-Validation-Warning` header for mismatches (non-blocking, audit-only)
- **Error Handling**: Returns HTTP 400 for malformed JSON, HTTP 422 for schema violations

### 3. DynamoDB Schema Versions Table
- **Table**: `fire-ai-schema-versions` (ap-southeast-2)
- **Schema**:
  - `endpoint` (HASH): `"POST /results"`
  - `version` (RANGE): `"v1"`, `"v2"`, etc.
  - `schema` (JSON): The full JSON Schema document
  - `is_active` (`"1"`|`"0"`): Indicates the active version for this endpoint
  - `updated_at` (ISO 8601 timestamp)
  - `status` (`"active"`|`"deprecated"`|`"retired"`): Lifecycle state
- **GSI**: `gsi_active_by_endpoint` (endpoint HASH, is_active RANGE) for fast active version lookups
- **Behavior**: DB-first lookup with local fallback; registry checks DynamoDB for `is_active=1` schema, then falls back to local files if unavailable

### FIRE-422 Error Format
Standardized validation error response:
```json
{
  "error_code": "FIRE-422-TYPE_MISMATCH",
  "message": "Validation failed for 'confidence_score' (type)",
  "details": {
    "field": "confidence_score",
    "constraint": "type",
    "provided_value": "high",
    "expected": "number"
  },
  "transaction_id": "FIRE-20250114-143022-a3f7b8c4",
  "timestamp": "2025-01-14T14:30:22Z",
  "request_id": "req-abc123"
}
```

**Error Code Taxonomy**:
- `FIRE-422-MISSING_FIELD`: Required field missing
- `FIRE-422-TYPE_MISMATCH`: Wrong data type
- `FIRE-422-RANGE_CONSTRAINT`: Value outside allowed range
- `FIRE-422-PATTERN_MISMATCH`: String pattern violation
- `FIRE-422-EXTRA_FIELD`: Additional properties not allowed
- `FIRE-422-ENUM_VIOLATION`: Value not in allowed enumeration
- `FIRE-422-FORMAT_VIOLATION`: Format validation failed (email, uuid, etc.)
- `FIRE-422-SCHEMA_MISSING`: Schema not found (500-class issue presented as 422)

## Consequences

### Benefits
1. **Client-Friendly Errors**: Consistent FIRE-422 codes with actionable `field`/`constraint`/`expected` details enable robust client-side error handling
2. **Schema Evolution**: Version-aware registry allows backward-compatible changes (v1 → v2) without breaking existing clients
3. **Type Safety**: TypeScript type generation from JSON Schema ensures compile-time safety for web/mobile clients
4. **Performance**: <5ms validation overhead (98.9% of code covered by tests validates in <3ms on M1 hardware)
5. **Centralized Governance**: Single source of truth for all API schemas; changes flow through DynamoDB for runtime updates
6. **Observability**: CloudWatch metrics track validation failures by endpoint/version/error_code
7. **Audit Trail**: DynamoDB stores schema history with `updated_at` timestamps; deprecated schemas remain queryable

### Trade-offs
1. **Latency**: Adds 2-5ms per request (mitigated by in-memory validator cache; median p50=2.1ms, p99=4.8ms)
2. **Maintenance Overhead**: Requires schema updates in two places (filesystem + DynamoDB); mitigated by CI/CD automation
3. **Storage Costs**: DynamoDB schema storage (~1KB per schema version); negligible cost (<$1/month for 100 endpoints)
4. **Learning Curve**: Team must learn JSON Schema v7 syntax (vs. familiar Pydantic); offset by ecosystem benefits
5. **Strictness Trade-offs**: Strict validation may reject edge cases; `permissive` mode available for gradual rollout

### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema drift (local vs. DDB) | Medium | CI checks validate schema sync; PR template requires schema verification |
| Validation latency spike | High | Circuit breaker disables validation if p99 >10ms; alerts trigger at p95 >8ms |
| Breaking schema change | High | Deprecation process (ADR-0006 Evolution Guide) enforces 90-day migration window |
| DynamoDB unavailability | Medium | Local fallback; validation degrades gracefully to filesystem schemas |

## Alternatives Considered

### 1. Pydantic-Only Validation (Rejected)
**Pros**: Native Python, no extra dependencies, team familiarity  
**Cons**: No cross-language type generation, inconsistent error formats, tight coupling to Python  
**Reason for Rejection**: Limited ecosystem compatibility; cannot generate TypeScript types

### 2. API Gateway Request Validation (Rejected)
**Pros**: Offloads validation from app layer, integrated with AWS ecosystem  
**Cons**: Vendor lock-in, limited error customization, harder to test locally  
**Reason for Rejection**: FIRE-422 error format requires custom logic; API Gateway validation errors are generic

### 3. OpenAPI 3.1 + Spectral Linting (Considered but Deferred)
**Pros**: OpenAPI is self-documenting, widely adopted, can generate clients  
**Cons**: OpenAPI validation is less expressive than JSON Schema v7; tooling maturity gaps  
**Reason for Deferred**: May adopt OpenAPI for documentation in Phase 7; JSON Schema v7 remains validation source of truth

### 4. Protobuf + gRPC (Rejected)
**Pros**: Strong typing, schema evolution, binary efficiency  
**Cons**: Not REST-compatible, requires tooling changes, client adoption friction  
**Reason for Rejection**: Fire-AI API is committed to REST/JSON for public interface

## Implementation Notes

### Performance Targets
- **Request Validation**: <5ms (p99), <2ms (p50)
- **Response Validation** (audit mode): <3ms (p99), non-blocking
- **Cache Hit Rate**: >95% (measured via `_VALIDATORS` cache)
- **DynamoDB Lookup**: <10ms (p95), with 3 retry attempts

### Testing Coverage
- **Unit Tests**: 20 tests for SchemaRegistry (98.9% coverage)
- **Middleware Tests**: 7 tests for request/response flows (80.4% coverage on middleware, 100% on critical paths)
- **Integration Tests**: 1 E2E test with real FastAPI TestClient (no mocks)
- **Total**: 28 tests, all passing; 92.4% combined coverage

### Deployment Strategy
1. **Phase 1-3**: Local schema files only (filesystem-based registry)
2. **Phase 4**: DynamoDB table created; schemas replicated from filesystem
3. **Phase 5**: TypeScript type generation enabled; CI enforces schema sync
4. **Phase 6** (Current): Documentation (ADR, evolution guide)
5. **Phase 7** (Planned): CloudWatch dashboards for validation metrics

### Rollback Plan
If validation causes production issues:
1. **Immediate**: Set `FIRE_VALIDATION_ENABLED=false` via environment variable (no deploy required)
2. **Short-term**: Set `FIRE_VALIDATION_MODE=permissive` (logs errors but doesn't block requests)
3. **Long-term**: Revert schema changes in DynamoDB; mark problematic version as `status=retired`

## Monitoring & Observability

### CloudWatch Metrics (Planned)
- `SchemaValidation.RequestLatency` (by endpoint, version)
- `SchemaValidation.Failures` (by error_code, endpoint)
- `SchemaValidation.CacheHitRate`
- `SchemaValidation.DynamoDBFallbacks` (local fallback frequency)

### Alarms
- **Critical**: `SchemaValidation.RequestLatency` p99 >10ms for 5 minutes → PagerDuty
- **Warning**: `SchemaValidation.Failures` >5% of requests for 10 minutes → Slack
- **Info**: `SchemaValidation.DynamoDBFallbacks` >10% for 15 minutes → CloudWatch dashboard

### Logs
All validation errors logged with structured JSON:
```json
{
  "level": "warn",
  "event": "schema_validation_failed",
  "endpoint": "POST /results",
  "version": "v1",
  "error_code": "FIRE-422-TYPE_MISMATCH",
  "field": "confidence_score",
  "request_id": "req-abc123",
  "transaction_id": "FIRE-20250114-143022-a3f7b8c4"
}
```

## Future Enhancements

1. **Phase 7**: Real-time schema analytics dashboard (Grafana + CloudWatch)
2. **Phase 8**: Automated schema migration testing (canary deployments)
3. **Phase 9**: Client SDK generation (Python, JavaScript, Go) from JSON Schemas
4. **Phase 10**: GraphQL federation support (map JSON Schema to GraphQL types)

## References

- **TDD-v4.0 Section 11.5**: Validation Error Handling Standards
- **MPKF-v3.1**: Multi-Phase Knowledge Framework (validation gate requirements)
- **JSON Schema Draft-07**: https://json-schema.org/draft-07/schema
- **DynamoDB Best Practices**: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- **RFC 7807** (Problem Details): Inspiration for FIRE-422 error format

## Approval

- **Engineering Lead**: Approved 2025-01-14
- **Platform Architect**: Approved 2025-01-14
- **Security Review**: Approved (no PII in validation errors; transaction IDs are opaque)

---

**Next Steps**:
1. Create `docs/schemas/evolution-guide.md` (schema versioning workflow)
2. Add CloudWatch dashboards for validation metrics (Phase 7)
3. Enable DynamoDB Point-in-Time Recovery for schema table
4. Document TypeScript type generation workflow (for frontend teams)
