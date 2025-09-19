"""
Token Revocation List (RTL) model for secure JWT management
"""

from sqlalchemy import Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from ..database.core import Base

class TokenRevocationList(Base):
    """
    Token Revocation List for tracking revoked JWT tokens
    """
    __tablename__ = 'token_revocation_list'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    token_jti = Column(String(255), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Can be null for system tokens
    revoked_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('idx_rtl_expires', 'expires_at'),
        Index('idx_rtl_user', 'user_id'),
        Index('idx_rtl_jti', 'token_jti'),
    )