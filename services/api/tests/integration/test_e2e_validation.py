from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.app.middleware.schema_validation import SchemaValidationMiddleware
from schemas.registry import SchemaRegistry

def test_e2e_request_to_results():
    app = FastAPI()
    app.add_middleware(SchemaValidationMiddleware, registry=SchemaRegistry())
    @app.post("/results")
    def post_results(payload: dict):
        return {"status": "accepted", "conflicts_detected": False}
    client = TestClient(app)

    # Valid
    ok = client.post("/results", json={
        "student_id": "ST123", "assessment_id": "A1", "score": 75,
        "completed_at": "2025-10-14T10:00:00Z"
    })
    assert ok.status_code == 200

    # Invalid
    bad = client.post("/results", json={
        "student_id": "ST123", "assessment_id": "A1", "score": "bad",
        "completed_at": "2025-10-14T10:00:00Z"
    })
    assert bad.status_code == 422
    assert bad.json()["error_code"].startswith("FIRE-422-")

