"""
Cursor-based pagination utilities for FireMode API
"""

import base64
import json
from typing import Optional, Dict, Any
from fastapi import HTTPException


def encode_cursor(data: Dict[str, Any]) -> str:
    """
    Encode pagination state as base64 cursor per TDD spec.
    
    Args:
        data: Dictionary containing pagination state (id, vector_clock, etc.)
        
    Returns:
        Base64 encoded cursor string
    """
    cursor_data = {
        "last_evaluated_id": str(data.get("id")),
        "vector_clock": data.get("vector_clock", {}),
        "created_at": data.get("created_at").isoformat() if data.get("created_at") and hasattr(data.get("created_at"), 'isoformat') else None
    }
    return base64.b64encode(json.dumps(cursor_data).encode()).decode()


def decode_cursor(cursor: Optional[str]) -> Dict[str, Any]:
    """
    Decode base64 cursor to pagination state.
    
    Args:
        cursor: Base64 encoded cursor string
        
    Returns:
        Dictionary containing pagination state
        
    Raises:
        HTTPException: If cursor is invalid
    """
    if not cursor:
        return {}
    
    try:
        decoded = base64.b64decode(cursor).decode()
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail="Invalid cursor format")


def create_pagination_filter(cursor_data: Dict[str, Any], table_alias=None):
    """
    Create SQLAlchemy filter conditions for cursor-based pagination.
    
    Args:
        cursor_data: Decoded cursor data
        table_alias: Optional table alias for queries
        
    Returns:
        SQLAlchemy filter conditions
    """
    from sqlalchemy import and_, or_, text
    from datetime import datetime
    
    if not cursor_data:
        return []
    
    conditions = []
    table_prefix = f"{table_alias}." if table_alias else ""
    
    # Add ID-based filtering for consistent ordering
    if "last_evaluated_id" in cursor_data and cursor_data["last_evaluated_id"]:
        conditions.append(text(f"{table_prefix}id > :cursor_id").params(cursor_id=cursor_data["last_evaluated_id"]))
    
    # Add timestamp-based filtering for chronological ordering
    if "created_at" in cursor_data and cursor_data["created_at"]:
        try:
            created_at = datetime.fromisoformat(cursor_data["created_at"])
            conditions.append(text(f"{table_prefix}created_at > :cursor_created_at").params(cursor_created_at=created_at))
        except (ValueError, TypeError):
            pass  # Skip invalid timestamps
    
    return conditions