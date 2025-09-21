# src/app/schemas/audit.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any

class AuditLogEntry(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action: str
    details: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True