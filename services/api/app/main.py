from fastapi import FastAPI
from typing import Dict
import os

app = FastAPI(title="Fire-AI API", version="0.1.0")

READY = {"ok": False}

@app.on_event("startup")
async def on_startup():
    # minimal init; flip readiness
    READY["ok"] = True

@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok", "service": "fire-ai-api"}

@app.get("/readyz")
async def readyz() -> Dict[str, str]:
    if READY.get("ok"):
        return {"status": "ready"}
    from fastapi import Response, status
    return Response(content='{"status":"not-ready"}', media_type="application/json",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
