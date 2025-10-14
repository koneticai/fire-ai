"""
DynamoDBSchemaLoader
- Fetches JSON Schemas from DynamoDB Schema Versions table.
- Key model: (endpoint: "POST /results", version: "v1")
- Fields: endpoint (PK), version (SK), schema (JSON), is_active ("1"/"0"), updated_at
- Fallback: returns None if not found; registry will fall back to local files.
"""

from __future__ import annotations
from typing import Optional, Tuple
import os
import json
import boto3
from botocore.config import Config

class DynamoDBSchemaLoader:
    def __init__(self, table_name: Optional[str] = None, region_name: Optional[str] = None):
        self.table_name = table_name or os.getenv("FIRE_SCHEMA_TABLE", "fire-ai-schema-versions")
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-southeast-2")
        self.ddb = boto3.resource("dynamodb", region_name=self.region_name, config=Config(retries={"max_attempts": 3}))
        self.table = self.ddb.Table(self.table_name)

    def fetch(self, endpoint: str, version: str = "v1") -> Optional[dict]:
        resp = self.table.get_item(Key={"endpoint": endpoint, "version": version})
        item = resp.get("Item")
        if not item:
            return None
        raw = item.get("schema")
        if isinstance(raw, str):
            return json.loads(raw)
        if isinstance(raw, dict):
            return raw
        return None

    def fetch_active(self, endpoint: str) -> Optional[Tuple[str, dict]]:
        """
        Returns (version, schema) for the currently active schema for this endpoint.
        GSI: gsi_active_by_endpoint (endpoint HASH, is_active RANGE)
        """
        resp = self.table.query(
            IndexName="gsi_active_by_endpoint",
            KeyConditionExpression="endpoint = :e AND is_active = :one",
            ExpressionAttributeValues={":e": endpoint, ":one": "1"},
            Limit=1,
        )
        items = resp.get("Items") or []
        if not items:
            return None
        it = items[0]
        raw = it.get("schema")
        schema = json.loads(raw) if isinstance(raw, str) else raw
        return it.get("version", "v1"), schema or None

