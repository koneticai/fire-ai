# src/app/schemas/user.py
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True