from fastapi import FastAPI, Response, status
from typing import Dict
from contextlib import asynccontextmanager
from schemas.registry import SchemaRegistry

READY = {"ok": True}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # If you need async init, set READY["ok"] = False here and flip after init completes.
    try:
        yield
    finally:
        READY["ok"] = False


app = FastAPI(title="Fire-AI API", version="0.1.0", lifespan=lifespan)

# Initialize schema registry (respects FIRE_SCHEMA_SOURCE env var)
# No behavior change if DynamoDB table is empty - falls back to local schemas
schema_registry = SchemaRegistry()

# Schema validation middleware can be added here when needed:
# app.add_middleware(
#     SchemaValidationMiddleware,
#     registry=schema_registry
# )


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok", "service": "fire-ai-api"}


@app.get("/readyz")
async def readyz():
    if READY.get("ok"):
        return {"status": "ready"}
    return Response(
        content='{"status":"not-ready"}',
        media_type="application/json",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
