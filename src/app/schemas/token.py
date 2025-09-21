# src/app/schemas/token.py
import uuid
from pydantic import BaseModel, Field
from typing import Optional, Any

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = Field(None, description="User identifier")
    username: Optional[str] = Field(None, description="Username")
    jti: Optional[uuid.UUID] = Field(None, description="JWT ID for revocation list")
    exp: Optional[int] = Field(None, description="Expiration timestamp")

class APIResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[Any] = None

class FaultDataInput(BaseModel):
    fault_id: str
    classification_request: dict

class ClassificationResult(BaseModel):
    result_id: str
    fault_id: str
    classification: str
    confidence: float