from sqlalchemy import select, and_, or_
from sqlalchemy.sql import Select
from typing import Dict, Any, Optional, Type
from datetime import datetime

class QueryBuilder:
    def __init__(self, base_query: Select, model: Type):
        self.query = base_query
        self.model = model
    
    def apply_filters(self, filters: Dict[str, Any]) -> 'QueryBuilder':
        """Apply TDD-compliant filtering"""
        if "status" in filters and filters["status"]:
            self.query = self.query.where(
                self.model.status.in_(filters["status"])
            )
        
        if "date_from" in filters and filters["date_from"]:
            self.query = self.query.where(
                self.model.created_at >= filters["date_from"]
            )
        
        if "date_to" in filters and filters["date_to"]:
            self.query = self.query.where(
                self.model.created_at <= filters["date_to"]
            )
        
        if "technician_id" in filters and filters["technician_id"]:
            self.query = self.query.where(
                self.model.created_by == filters["technician_id"]
            )
        
        return self
    
    def apply_cursor_pagination(
        self, 
        cursor_data: Dict[str, Any],
        limit: int = 20
    ) -> 'QueryBuilder':
        """Apply vector-clock aware pagination with deterministic ordering"""
        # Add deterministic ordering
        self.query = self.query.order_by(self.model.created_at, self.model.id)
        
        if "last_evaluated_id" in cursor_data:
            # Continue from last position using keyset pagination
            self.query = self.query.where(
                self.model.id > cursor_data["last_evaluated_id"]
            )
        
        # Fetch limit+1 to detect if there are more results
        self.query = self.query.limit(limit + 1)
        return self
    
    def build(self) -> Select:
        return self.query