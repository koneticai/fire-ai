from services.api.schemas.registry import SchemaRegistry

def main():
    r = SchemaRegistry()
    print("schemas:", r.list_schemas())

    ok, err = r.validate_request(
        "POST /results",
        {"student_id":"ST123","assessment_id":"A1","score":99,"completed_at":"2025-10-14T10:30:00Z"},
        version="v1",
        request_id="req-abc",
    )
    print("valid:", ok, "error:", err)

    ok2, err2 = r.validate_request(
        "POST /results",
        {"student_id":"ST123","assessment_id":"A1","score":"bad","completed_at":"2025-10-14T10:30:00Z"},
        version="v1",
        request_id="req-def",
    )
    print("invalid:", ok2, "error_code:", err2["error_code"], "constraint:", err2["details"]["constraint"])

if __name__ == "__main__":
    main()

