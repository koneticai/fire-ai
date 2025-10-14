"""
Application configuration for FireAI API service.
Environment-based settings for schema source and AWS resources.
"""

import os

# Schema source configuration
# "local-only" - Only use local JSON files
# "local+ddb" - Prefer DynamoDB, fallback to local files (default)
FIRE_SCHEMA_SOURCE = os.getenv("FIRE_SCHEMA_SOURCE", "local+ddb")

# DynamoDB table name for schema versions
FIRE_SCHEMA_TABLE = os.getenv("FIRE_SCHEMA_TABLE", "fire-ai-schema-versions")

# AWS region for DynamoDB and other services
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")

