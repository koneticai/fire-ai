from sqlalchemy import select, and_, or_
from sqlalchemy.sql import Select
from typing import Dict, Any, Optional
from datetime import datetime

class QueryBuilder:
    def __init__(self, base_query: Select):
        self.query = base_query
    
    def apply_filters(self, filters: Dict[str, Any]) -> 'QueryBuilder':
        """Apply TDD-compliant filtering"""
        if "status" in filters:
            self.query = self.query.where(
                self.query.selected_columns[0].status.in_(filters["status"])
            )
        
        if "date_from" in filters:
            self.query = self.query.where(
                self.query.selected_columns[0].created_at >= filters["date_from"]
            )
        
        if "date_to" in filters:
            self.query = self.query.where(
                self.query.selected_columns[0].created_at <= filters["date_to"]
            )
        
        return self
    
    def apply_cursor_pagination(
        self, 
        cursor_data: Dict[str, Any],
        limit: int = 20
    ) -> 'QueryBuilder':
        """Apply vector-clock aware pagination"""
        if "last_evaluated_id" in cursor_data:
            # Continue from last position
            self.query = self.query.where(
                self.query.selected_columns[0].id > cursor_data["last_evaluated_id"]
            )
        
        self.query = self.query.limit(limit)
        return self
    
    def build(self) -> Select:
        return self.query