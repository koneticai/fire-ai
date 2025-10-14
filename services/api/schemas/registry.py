"""
FM-ENH-001: Centralised JSON Schema v7 validation registry.
Implements request/response validation with caching, Draft-07 validators,
and FIRE-422 error shaping. (MPKF v3.1, TDD v4.0 §11.5)
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import json
import re
from functools import lru_cache
from datetime import datetime
import secrets

from jsonschema import Draft7Validator, RefResolver, exceptions as js_exceptions

class SchemaNotFoundError(KeyError):
    pass

# endpoint -> version -> raw schema dict
_SCHEMA_STORE: Dict[str, Dict[str, dict]] = {}
# endpoint -> version -> compiled validator
_VALIDATORS: Dict[str, Dict[str, Draft7Validator]] = {}

class SchemaRegistry:
    def __init__(self, schemas_root: Optional[Path] = None) -> None:
        self.schemas_root = Path(schemas_root or Path(__file__).parent)
        self._load_all_schemas()

    def _endpoint_from_filename(self, subdir: str, name: str) -> str:
        # "post_results" -> "POST /results"
        # "error_422" -> "ERROR /422"
        method, path = name.split("_", 1)
        return f"{method.upper()} /{path.replace('_','/')}"

    def _key(self, endpoint: str, schema_type: str) -> str:
        """Generate storage key: REQ:POST /results or RESP:POST /results"""
        return f"{schema_type}:{endpoint}"

    def _load_all_schemas(self) -> int:
        import itertools
        count = 0
        # Preload common refs and build a resolver base
        common_dir = self.schemas_root / "common"
        common_ids = {}
        for p in common_dir.rglob("*.json"):
            with p.open("r", encoding="utf-8") as f:
                doc = json.load(f)
                if "$id" in doc:
                    common_ids[doc["$id"]] = doc

        for subdir in ("requests", "responses"):
            schema_type = "REQ" if subdir == "requests" else "RESP"
            for p in (self.schemas_root / subdir).rglob("*.json"):
                with p.open("r", encoding="utf-8") as f:
                    schema = json.load(f)
                m = re.match(r"^(?P<name>.+)_v(?P<num>\d+)\.json$", p.name)
                if not m:
                    continue
                endpoint = self._endpoint_from_filename(subdir, m.group("name"))
                version = f"v{m.group('num')}"
                key = self._key(endpoint, schema_type)
                _SCHEMA_STORE.setdefault(key, {})[version] = schema

                # Build a RefResolver that knows about our common IDs
                resolver = RefResolver.from_schema(schema, store=common_ids)
                validator = Draft7Validator(schema, resolver=resolver)
                _VALIDATORS.setdefault(key, {})[version] = validator
                count += 1
        return count

    def get_schema(self, endpoint: str, version: str = "v1", schema_type: str = "REQ") -> dict:
        try:
            key = self._key(endpoint, schema_type)
            return _SCHEMA_STORE[key][version]
        except KeyError as e:
            raise SchemaNotFoundError(f"Schema not found for {schema_type}:{endpoint} {version}") from e

    def _validator(self, endpoint: str, version: str = "v1", schema_type: str = "REQ") -> Draft7Validator:
        try:
            key = self._key(endpoint, schema_type)
            return _VALIDATORS[key][version]
        except KeyError as e:
            raise SchemaNotFoundError(f"Validator not found for {schema_type}:{endpoint} {version}") from e

    @staticmethod
    def _now_utc_iso() -> str:
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _transaction_id() -> str:
        # FIRE-YYYYMMDD-HHMMSS-<8hex> (example-friendly and cheap to produce)
        return datetime.utcnow().strftime("FIRE-%Y%m%d-%H%M%S-") + secrets.token_hex(4)

    def _shape_fire_422(
        self,
        field: str,
        constraint: str,
        provided_value=None,
        expected: Optional[str] = None,
        code_suffix: str = "VALIDATION_FAILED",
        message: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict:
        return {
            "error_code": f"FIRE-422-{code_suffix}",
            "message": message or f"Validation failed for '{field}' ({constraint})",
            "details": {
                "field": field,
                "constraint": constraint,
                **({"provided_value": provided_value} if provided_value is not None else {}),
                **({"expected": expected} if expected is not None else {}),
            },
            "transaction_id": self._transaction_id(),
            "timestamp": self._now_utc_iso(),
            "request_id": request_id or "req-unknown",
        }

    def validate_request(self, endpoint: str, data: dict, version: str = "v1", request_id: Optional[str] = None) -> Tuple[bool, Optional[dict]]:
        """
        Validate incoming request payload. On success -> (True, None).
        On failure -> (False, FIRE-422 dict).
        """
        try:
            validator = self._validator(f"POST {endpoint.split(' ',1)[1]}", version, "REQ") if endpoint.startswith("GET ") else self._validator(endpoint, version, "REQ")
        except SchemaNotFoundError:
            # Treat missing schema as server issue; return generic 422 shape (still helpful to client)
            return False, self._shape_fire_422(field="__root__", constraint="schema_exists", expected=f"{endpoint} {version}", code_suffix="SCHEMA_MISSING", message="Schema not found", request_id=request_id)

        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if not errors:
            return True, None

        # Take first error for FIRE-422 (later we can aggregate)
        e: js_exceptions.ValidationError = errors[0]
        field = ".".join(str(p) for p in e.path) if e.path else "__root__"
        constraint = e.validator  # e.g., 'required', 'type', 'format', 'minimum'
        expected = str(e.schema.get(e.validator)) if isinstance(e.schema, dict) else None
        provided = e.instance
        suffix_map = {
            "required": "MISSING_FIELD",
            "type": "TYPE_MISMATCH",
            "format": "FORMAT_VIOLATION",
            "minimum": "RANGE_CONSTRAINT",
            "maximum": "RANGE_CONSTRAINT",
            "pattern": "PATTERN_MISMATCH",
            "enum": "ENUM_VIOLATION",
            "additionalProperties": "EXTRA_FIELD",
        }
        code_suffix = suffix_map.get(constraint, "VALIDATION_FAILED")
        msg = e.message
        return False, self._shape_fire_422(field, constraint, provided, expected, code_suffix, msg, request_id)

    def validate_response(self, endpoint: str, data: dict, version: str = "v1") -> bool:
        """
        Validate outgoing response payload. Returns True/False.
        Should NOT block responses (middleware logs only).
        """
        try:
            validator = self._validator(endpoint, version, "RESP")
        except SchemaNotFoundError:
            return True  # don't punish response path for missing schema
        return validator.is_valid(data)

    def list_schemas(self) -> List[str]:
        # Return only request endpoints (user-facing)
        return sorted([k.replace("REQ:", "") for k in _SCHEMA_STORE.keys() if k.startswith("REQ:")])

