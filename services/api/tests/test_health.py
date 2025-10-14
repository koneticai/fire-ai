from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_readyz():
    r = client.get("/readyz")
    # after startup, should be ready
    assert r.status_code == 200
