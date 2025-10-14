"""
SchemaValidationMiddleware
- Validates JSON request bodies against JSON Schema (Draft-07)
- Returns FIRE-422 on invalid payloads
- Optionally checks response shape (audit only)
Config:
  FIRE_VALIDATION_ENABLED=true|false (default true)
  FIRE_VALIDATION_MODE=strict|permissive (default strict)
  FIRE_VALIDATION_WHITELIST=/health,/metrics (comma-separated)
  FIRE_DEFAULT_VERSION=v1
"""

import os
import json
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp
from schemas.registry import SchemaRegistry

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
BODY_METHODS = {"POST", "PUT", "PATCH"}

def _normalise_endpoint(method: str, path: str) -> str:
    # path like "/results" => "POST /results"
    # collapse multiple slashes, strip trailing slash
    norm = "/" + "/".join([seg for seg in path.split("/") if seg])
    return f"{method.upper()} {norm}"

class SchemaValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, registry: SchemaRegistry | None = None):
        super().__init__(app)
        self.registry = registry or SchemaRegistry()
        self.enabled = os.getenv("FIRE_VALIDATION_ENABLED", "true").lower() == "true"
        self.mode = os.getenv("FIRE_VALIDATION_MODE", "strict").lower()  # strict | permissive
        wl = os.getenv("FIRE_VALIDATION_WHITELIST", "/health,/metrics")
        self.whitelist = {p.strip() for p in wl.split(",") if p.strip()}
        self.default_version = os.getenv("FIRE_DEFAULT_VERSION", "v1")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        method = request.method.upper()
        path = request.url.path

        # Skip non-body and whitelisted endpoints
        if method in SAFE_METHODS or any(path.startswith(w) for w in self.whitelist):
            return await call_next(request)

        if method in BODY_METHODS:
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error_code": "FIRE-400-MALFORMED_JSON",
                        "message": "Request body must be valid JSON",
                        "details": {"field": "__root__", "constraint": "json"},
                        "transaction_id": self.registry._transaction_id(),
                        "timestamp": self.registry._now_utc_iso(),
                        "request_id": request.headers.get("x-request-id", "req-unknown"),
                    },
                )

            endpoint = _normalise_endpoint(method, path)
            ok, err = self.registry.validate_request(endpoint, body, version=self.default_version, request_id=request.headers.get("x-request-id"))
            if not ok:
                return JSONResponse(status_code=422, content=err)

        # Continue to handler
        response = await call_next(request)

        # Optional response validation (non-blocking/audit-only)
        if self.mode == "strict" and response.media_type == "application/json":
            try:
                raw = await response.body()
                data = json.loads(raw.decode("utf-8")) if isinstance(raw, (bytes, bytearray)) else raw
            except Exception:
                data = None
            if isinstance(data, dict):
                endpoint = _normalise_endpoint(request.method, request.url.path).replace("POST ", "POST ")  # keep same form
                valid = self.registry.validate_response(endpoint, data, version=self.default_version)
                if not valid:
                    # Here we just annotate a header for audit visibility
                    response.headers["X-Validation-Warning"] = "response_schema_mismatch"

        return response

