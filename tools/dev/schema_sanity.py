"""
FM-ENH-001 Schema Sanity Check
Tests SchemaRegistry validation with POST /results endpoint.
Expected outputs:
1. List includes 'POST /results'
2. Valid payload: True, None
3. Invalid payload: False, FIRE-422-TYPE_MISMATCH with constraint='type'
"""

from services.api.schemas.registry import SchemaRegistry

def main():
    r = SchemaRegistry()
    print("schemas:", r.list_schemas())

    # Test 1: Valid payload
    ok, err = r.validate_request(
        "POST /results",
        {"student_id":"ST123","assessment_id":"A1","score":99,"completed_at":"2025-10-14T10:30:00Z"},
        version="v1", request_id="req-abc",
    )
    print("valid:", ok, "error:", err)

    # Test 2: Invalid payload (score should be number, not string)
    ok2, err2 = r.validate_request(
        "POST /results",
        {"student_id":"ST123","assessment_id":"A1","score":"bad","completed_at":"2025-10-14T10:30:00Z"},
        version="v1", request_id="req-def",
    )
    print("invalid:", ok2, "error_code:", err2["error_code"], "constraint:", err2["details"]["constraint"])

if __name__ == "__main__":
    main()
