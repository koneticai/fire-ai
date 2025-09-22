"""
Users router for FireMode Compliance Platform
Handles user profile and compliance history retrieval
"""

import json
from typing import List
from uuid import UUID

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..schemas.user import UserProfile
from ..schemas.audit import AuditLogEntry
from ..schemas.token import TokenData
from ..dependencies import get_current_active_user
from ..database.core import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from ..security import decrypt_pii

router = APIRouter(tags=["Users"])

@router.get("/me", response_model=UserProfile, 
            summary="Get Current User Profile", 
            description="Retrieves the profile for the currently authenticated user with decrypted PII data.")
async def get_current_user_profile(
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the profile for the currently authenticated user.
    """
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, email, full_name_encrypted, is_active, created_at
                FROM users 
                WHERE id = %s
            """, (current_user.user_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                # This case can happen if a user is deleted but their token is still valid
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="User not found"
                )
            
            # Decrypt the full name
            try:
                full_name = decrypt_pii(row[3]) if row[3] else ""
            except Exception:
                # If decryption fails, use empty string
                full_name = ""
            
            user_profile = UserProfile(
                id=row[0],
                username=row[1],
                email=row[2],
                full_name=full_name,
                is_active=row[4],
                created_at=row[5]
            )
        
        conn.close()
        return user_profile
        
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user profile: {str(e)}"
        )

@router.get("/me/audits", response_model=List[AuditLogEntry], 
            summary="Get User Audit History", 
            description="Retrieves a paginated history of the current user's compliance activities and system interactions.")
async def get_user_audit_history(
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return")
):
    """
    Retrieves a paginated history of the current user's compliance activities.
    Returns audit log entries ordered by most recent first.
    """
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, action, resource_type, resource_id, old_values, new_values, 
                       ip_address, user_agent, created_at
                FROM audit_log 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                OFFSET %s LIMIT %s
            """, (current_user.user_id, skip, limit))
            
            rows = cursor.fetchall()
            audit_entries = []
            
            for row in rows:
                # Handle JSONB fields - they might be returned as strings
                old_values = row[4]
                if isinstance(old_values, str):
                    try:
                        old_values = json.loads(old_values)
                    except json.JSONDecodeError:
                        old_values = None
                
                new_values = row[5]
                if isinstance(new_values, str):
                    try:
                        new_values = json.loads(new_values)
                    except json.JSONDecodeError:
                        new_values = None
                
                audit_entry = AuditLogEntry(
                    id=row[0],
                    action=row[1],
                    resource_type=row[2],
                    resource_id=row[3],
                    old_values=old_values,
                    new_values=new_values,
                    ip_address=row[6],
                    user_agent=row[7],
                    created_at=row[8]
                )
                audit_entries.append(audit_entry)
        
        conn.close()
        return audit_entries
        
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit history: {str(e)}"
        )