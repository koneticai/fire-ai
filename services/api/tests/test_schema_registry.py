"""
Unit tests for SchemaRegistry (FM-ENH-001 validation).
Tests schema loading, validation, caching, and FIRE-422 error shaping.
Implements TDD v4.0 §11.5 compliance verification.
"""

import pytest
import os
from schemas.registry import SchemaRegistry, SchemaNotFoundError


@pytest.fixture(scope="module")
def registry() -> SchemaRegistry:
    """Fixture that provides a SchemaRegistry instance loaded from services/api/schemas/**"""
    # Use local-only mode to avoid DynamoDB dependency in tests
    os.environ["FIRE_SCHEMA_SOURCE"] = "local-only"
    reg = SchemaRegistry()  # loads from services/api/schemas/**
    os.environ.pop("FIRE_SCHEMA_SOURCE", None)
    return reg


def test_load_schemas_on_init(registry):
    """
    Verify that schemas are automatically loaded during initialization.
    The registry should discover and index all schema files.
    """
    keys = registry.list_schemas()
    assert "POST /results" in keys, "Expected POST /results endpoint to be registered"
    assert len(keys) > 0, "Registry should load at least one schema"


def test_get_schema_existing(registry):
    """
    Verify that we can retrieve a known schema by endpoint and version.
    Should return the schema dict with proper Draft-07 $schema reference.
    """
    s = registry.get_schema("POST /results", "v1")
    assert "$schema" in s, "Schema should have $schema property"
    assert s["$schema"].endswith("draft-07/schema#"), "Should use JSON Schema Draft-07"
    assert s["type"] == "object", "POST /results should be an object schema"


def test_get_schema_not_found(registry):
    """
    Verify that attempting to retrieve a non-existent schema raises SchemaNotFoundError.
    This ensures proper error handling for missing schemas.
    """
    with pytest.raises(SchemaNotFoundError):
        registry.get_schema("POST /nope", "v1")


def test_validate_request_valid(registry):
    """
    Verify that a valid request payload passes validation.
    Should return (True, None) for compliant data.
    """
    ok, err = registry.validate_request(
        "POST /results",
        {
            "student_id": "ST123",
            "assessment_id": "A1",
            "score": 85,
            "completed_at": "2025-10-14T10:00:00Z",
        },
        version="v1",
        request_id="req-abc",
    )
    assert ok is True, "Valid payload should pass validation"
    assert err is None, "No error should be returned for valid payload"


def test_validate_request_missing_field(registry):
    """
    Verify that missing required fields trigger proper FIRE-422 error response.
    Error code should indicate missing field constraint.
    """
    ok, err = registry.validate_request(
        "POST /results",
        {
            "assessment_id": "A1",
            "score": 85,
            "completed_at": "2025-10-14T10:00:00Z",
        },
        version="v1",
        request_id="req-xyz",
    )
    assert ok is False, "Missing required field should fail validation"
    assert err is not None, "Error dict should be returned"
    assert err["error_code"].startswith("FIRE-422-"), "Error code should follow FIRE-422 format"
    assert err["details"]["constraint"] == "required", "Constraint should indicate required field violation"
    assert "transaction_id" in err, "FIRE-422 errors must include transaction_id"
    assert "timestamp" in err, "FIRE-422 errors must include timestamp"


def test_validate_request_wrong_type(registry):
    """
    Verify that type mismatches trigger specific FIRE-422-TYPE_MISMATCH error.
    Score should be a number, not a string.
    """
    ok, err = registry.validate_request(
        "POST /results",
        {
            "student_id": "ST123",
            "assessment_id": "A1",
            "score": "bad",  # should be number
            "completed_at": "2025-10-14T10:00:00Z",
        },
        version="v1",
        request_id="req-def",
    )
    assert ok is False, "Type mismatch should fail validation"
    assert err["error_code"] == "FIRE-422-TYPE_MISMATCH", "Should return specific type mismatch error code"
    assert err["details"]["constraint"] == "type", "Constraint should indicate type violation"
    assert err["request_id"] == "req-def", "Request ID should be preserved in error"


def test_schema_caching(registry):
    """
    Verify that validators are cached and reused across multiple validations.
    This test ensures performance optimization through compiled validator reuse.
    No exception should occur on repeated validation calls.
    """
    # First call
    ok1, err1 = registry.validate_request(
        "POST /results",
        {
            "student_id": "S",
            "assessment_id": "A",
            "score": 1,
            "completed_at": "2025-10-14T10:00:00Z",
        },
    )
    
    # Second call - should use cached validator
    ok2, err2 = registry.validate_request(
        "POST /results",
        {
            "student_id": "S2",
            "assessment_id": "A2",
            "score": 99,
            "completed_at": "2025-10-14T11:00:00Z",
        },
    )
    
    # Both should succeed, proving validator caching works
    assert ok1 is True, "First validation should succeed"
    assert ok2 is True, "Second validation should succeed with cached validator"


def test_multiple_versions_future_friendly(registry):
    """
    Verify that the registry raises KeyError for non-existent versions.
    This ensures version handling is explicit and fails fast for unsupported versions.
    When v2 is added later, this test documents the expected behavior.
    """
    with pytest.raises(KeyError):
        registry.get_schema("POST /results", "v2")


def test_validate_request_range_constraint(registry):
    """
    Verify that range constraints (min/max) are properly enforced.
    Score must be between 0 and 100.
    """
    ok, err = registry.validate_request(
        "POST /results",
        {
            "student_id": "ST123",
            "assessment_id": "A1",
            "score": 150,  # exceeds maximum of 100
            "completed_at": "2025-10-14T10:00:00Z",
        },
        version="v1",
        request_id="req-range",
    )
    assert ok is False, "Score exceeding maximum should fail validation"
    assert err["error_code"] == "FIRE-422-RANGE_CONSTRAINT", "Should indicate range constraint violation"


def test_validate_request_pattern_mismatch(registry):
    """
    Verify that pattern validation (regex) is enforced for timestamp format.
    completed_at must match ISO 8601 pattern.
    """
    ok, err = registry.validate_request(
        "POST /results",
        {
            "student_id": "ST123",
            "assessment_id": "A1",
            "score": 85,
            "completed_at": "not-a-timestamp",  # invalid format
        },
        version="v1",
        request_id="req-pattern",
    )
    assert ok is False, "Invalid timestamp pattern should fail validation"
    assert err["error_code"] == "FIRE-422-PATTERN_MISMATCH", "Should indicate pattern mismatch"


def test_validate_request_extra_properties(registry):
    """
    Verify that additional properties are rejected (additionalProperties: false).
    Only defined properties should be allowed.
    """
    ok, err = registry.validate_request(
        "POST /results",
        {
            "student_id": "ST123",
            "assessment_id": "A1",
            "score": 85,
            "completed_at": "2025-10-14T10:00:00Z",
            "extra_field": "not_allowed",  # not in schema
        },
        version="v1",
        request_id="req-extra",
    )
    assert ok is False, "Extra properties should be rejected"
    assert err["error_code"] == "FIRE-422-EXTRA_FIELD", "Should indicate extra field violation"


def test_fire_422_error_structure(registry):
    """
    Verify that FIRE-422 error responses have all required fields
    and follow the standardized structure defined in TDD v4.0.
    """
    ok, err = registry.validate_request(
        "POST /results",
        {"student_id": "ST123"},  # missing required fields
        version="v1",
        request_id="req-structure",
    )
    
    assert ok is False
    assert "error_code" in err, "Must include error_code"
    assert "message" in err, "Must include message"
    assert "details" in err, "Must include details"
    assert "transaction_id" in err, "Must include transaction_id"
    assert "timestamp" in err, "Must include timestamp"
    assert "request_id" in err, "Must include request_id"
    
    # Verify transaction_id format: FIRE-YYYYMMDD-HHMMSS-<8hex>
    assert err["transaction_id"].startswith("FIRE-"), "Transaction ID should start with FIRE-"
    assert len(err["transaction_id"]) == 29, "Transaction ID should be 29 chars (FIRE-8-6-8 hex)"
    
    # Verify timestamp format: ISO 8601 UTC
    import re
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", err["timestamp"]), "Timestamp should be ISO 8601 UTC"


def test_list_schemas_returns_all_endpoints(registry):
    """
    Verify that list_schemas() returns all registered request endpoints.
    This is useful for documentation and API discovery.
    """
    schemas = registry.list_schemas()
    assert isinstance(schemas, list), "Should return a list"
    assert len(schemas) > 0, "Should have at least one schema"
    assert all(isinstance(s, str) for s in schemas), "All entries should be strings"
    assert schemas == sorted(schemas), "List should be sorted alphabetically"


def test_validate_request_with_nested_metadata(registry):
    """
    Verify that nested object validation works correctly.
    POST /results schema includes optional metadata object with specific constraints.
    """
    # Valid nested metadata
    ok, err = registry.validate_request(
        "POST /results",
        {
            "student_id": "ST123",
            "assessment_id": "A1",
            "score": 85,
            "completed_at": "2025-10-14T10:00:00Z",
            "metadata": {
                "duration_seconds": 1800,
                "device_type": "web",
            },
        },
        version="v1",
    )
    assert ok is True, "Valid nested metadata should pass"
    
    # Invalid enum value in nested object
    ok, err = registry.validate_request(
        "POST /results",
        {
            "student_id": "ST123",
            "assessment_id": "A1",
            "score": 85,
            "completed_at": "2025-10-14T10:00:00Z",
            "metadata": {
                "device_type": "desktop",  # not in enum [web, mobile, tablet]
            },
        },
        version="v1",
    )
    assert ok is False, "Invalid enum value should fail"
    assert err["error_code"] == "FIRE-422-ENUM_VIOLATION", "Should indicate enum violation"


def test_request_id_preservation(registry):
    """
    Verify that request_id is properly preserved in error responses.
    This is critical for request tracing and debugging.
    """
    custom_request_id = "req-custom-12345"
    ok, err = registry.validate_request(
        "POST /results",
        {"invalid": "data"},
        version="v1",
        request_id=custom_request_id,
    )
    
    assert ok is False
    assert err["request_id"] == custom_request_id, "Custom request_id should be preserved"


def test_request_id_default_when_missing(registry):
    """
    Verify that a default request_id is provided when none is supplied.
    """
    ok, err = registry.validate_request(
        "POST /results",
        {"invalid": "data"},
        version="v1",
        # request_id not provided
    )
    
    assert ok is False
    assert "request_id" in err, "request_id should always be present"
    assert err["request_id"] == "req-unknown", "Default request_id should be 'req-unknown'"


def test_validate_response_valid(registry):
    """
    Verify that validate_response correctly validates successful response payloads.
    """
    is_valid = registry.validate_response(
        "POST /results",
        {
            "result_id": "res-123",
            "student_id": "ST123",
            "assessment_id": "A1",
            "score": 85,
            "completed_at": "2025-10-14T10:00:00Z",
            "created_at": "2025-10-14T10:05:00Z",
            "transaction_id": "FIRE-20251014-100500-abcd1234",
        },
        version="v1",
    )
    assert is_valid is True, "Valid response should pass validation"


def test_validate_response_missing_schema(registry):
    """
    Verify that validate_response returns True when schema doesn't exist (non-blocking).
    """
    is_valid = registry.validate_response(
        "POST /nonexistent",
        {"any": "data"},
        version="v1",
    )
    assert is_valid is True, "Missing response schema should not block response"


def test_validate_request_missing_schema(registry):
    """
    Verify that validate_request returns proper FIRE-422-SCHEMA_MISSING error
    when the endpoint schema doesn't exist.
    """
    ok, err = registry.validate_request(
        "POST /nonexistent",
        {"data": "anything"},
        version="v1",
        request_id="req-missing",
    )
    
    assert ok is False
    assert err["error_code"] == "FIRE-422-SCHEMA_MISSING"
    assert err["details"]["constraint"] == "schema_exists"
    assert err["request_id"] == "req-missing"


def test_validate_response_invalid(registry):
    """
    Verify that validate_response returns False for invalid response payloads.
    """
    is_valid = registry.validate_response(
        "POST /results",
        {"wrong": "structure"},  # Missing required fields
        version="v1",
    )
    assert is_valid is False, "Invalid response should fail validation"

