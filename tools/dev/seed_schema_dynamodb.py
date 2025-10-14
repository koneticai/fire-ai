"""
Seed a single endpoint schema into DynamoDB for testing:
- Endpoint: "POST /results", Version: "v1"
- Pulls schema JSON from local file and inserts into the table.
"""

import os
import json
import boto3

TABLE = os.getenv("FIRE_SCHEMA_TABLE", "fire-ai-schema-versions")
REGION = os.getenv("AWS_REGION", "ap-southeast-2")


def main():
    ddb = boto3.resource("dynamodb", region_name=REGION)
    table = ddb.Table(TABLE)
    
    with open("services/api/schemas/requests/post_results_v1.json", "r", encoding="utf-8") as f:
        req_schema = json.load(f)
    
    table.put_item(
        Item={
            "endpoint": "POST /results",
            "version": "v1",
            "is_active": "1",
            "schema": json.dumps(req_schema),
            "updated_at": "2025-10-15T00:00:00Z",
        }
    )
    
    print(f"Seeded POST /results v1 to {TABLE}")


if __name__ == "__main__":
    main()

