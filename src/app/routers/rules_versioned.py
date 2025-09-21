"""
Versioned AS1851 rules router for FireMode Compliance Platform
Implements immutable rule management with semantic versioning
"""

import json
from datetime import datetime
from typing import List
from uuid import UUID

import psycopg2
import semver
from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..models import AS1851Rule, AS1851RuleCreate
from ..dependencies import get_current_active_user, get_database_connection
from ..schemas.token import TokenData, APIResponse

router = APIRouter(tags=["AS1851 Rules (Versioned)"])

@router.post("/", response_model=AS1851Rule, status_code=status.HTTP_201_CREATED, 
             summary="Create Versioned AS1851 Rule", 
             description="Creates a new versioned AS1851 rule. Each version is immutable and prevents duplicates.")
async def create_versioned_rule(
    rule: AS1851RuleCreate,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Creates a new, versioned AS1851 rule. Rejects duplicates."""
    
    try:
        with conn.cursor() as cursor:
            # Check if this exact version already exists
            cursor.execute("""
                SELECT COUNT(*) FROM as1851_rules 
                WHERE rule_code = %s AND version = %s
            """, (rule.rule_code, rule.version))
            
            existing_count = cursor.fetchone()[0]
            if existing_count > 0:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Rule {rule.rule_code} version {rule.version} already exists."
                )
            
            # Insert the new versioned rule
            cursor.execute("""
                INSERT INTO as1851_rules 
                (rule_code, version, rule_name, description, rule_schema, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (
                rule.rule_code,
                rule.version,
                rule.rule_name,
                rule.description,
                json.dumps(rule.rule_schema),
                True
            ))
            
            result = cursor.fetchone()
            rule_id, created_at = result
            
            conn.commit()
        
        conn.close()
        
        return AS1851Rule(
            id=rule_id,
            rule_code=rule.rule_code,
            version=rule.version,
            rule_name=rule.rule_name,
            description=rule.description,
            rule_schema=rule.rule_schema,
            is_active=True,
            created_at=created_at
        )
        
    except psycopg2.IntegrityError as e:
        conn.rollback()
        conn.close()
        if "rule_code_version" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Rule {rule.rule_code} version {rule.version} already exists."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {str(e)}"
        )
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rule: {str(e)}"
        )

@router.get("/", response_model=List[AS1851Rule], 
            summary="List All Active Versioned Rules", 
            description="Lists all active AS1851 rule versions available in the system.")
async def get_all_active_versioned_rules(
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Lists all active AS1851 rules (all versions)."""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, rule_code, version, rule_name, description, rule_schema, 
                       is_active, created_at
                FROM as1851_rules 
                WHERE is_active = true
                ORDER BY rule_code, version DESC
            """)
            
            rows = cursor.fetchall()
            rules = []
            
            for row in rows:
                rule = AS1851Rule(
                    id=row[0],
                    rule_code=row[1],
                    version=row[2],
                    rule_name=row[3],
                    description=row[4],
                    rule_schema=row[5],
                    is_active=row[6],
                    created_at=row[7]
                )
                rules.append(rule)
        
        conn.close()
        return rules
        
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list rules: {str(e)}"
        )

@router.get("/{rule_code}/latest", response_model=AS1851Rule, 
            summary="Get Latest Active Rule Version", 
            description="Gets the latest active version of a rule by its code using semantic versioning.")
async def get_latest_active_rule_by_code(
    rule_code: str,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Gets the latest active version of a rule by its code."""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, rule_code, version, rule_name, description, rule_schema, 
                       is_active, created_at
                FROM as1851_rules 
                WHERE rule_code = %s AND is_active = true
                ORDER BY version DESC
            """, (rule_code,))
            
            rows = cursor.fetchall()
            if not rows:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Active rule with code {rule_code} not found."
                )
            
            # Find the highest semantic version
            latest_rule = None
            latest_version = None
            
            for row in rows:
                try:
                    current_version = semver.VersionInfo.parse(row[2])
                    if latest_version is None or current_version > latest_version:
                        latest_version = current_version
                        latest_rule = AS1851Rule(
                            id=row[0],
                            rule_code=row[1],
                            version=row[2],
                            rule_name=row[3],
                            description=row[4],
                            rule_schema=row[5],
                            is_active=row[6],
                            created_at=row[7]
                        )
                except ValueError:
                    # Skip invalid semantic versions
                    continue
            
            if latest_rule is None:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"No valid semantic versions found for rule {rule_code}"
                )
        
        conn.close()
        return latest_rule
        
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rule: {str(e)}"
        )

@router.get("/{rule_code}/versions", response_model=List[AS1851Rule], 
            summary="Get All Rule Versions", 
            description="Gets all versions of a specific rule by its code, sorted by version.")
async def get_all_rule_versions(
    rule_code: str,
    include_inactive: bool = False,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Gets all versions of a specific rule by its code."""
    
    try:
        with conn.cursor() as cursor:
            if include_inactive:
                cursor.execute("""
                    SELECT id, rule_code, version, rule_name, description, rule_schema, 
                           is_active, created_at
                    FROM as1851_rules 
                    WHERE rule_code = %s
                    ORDER BY version DESC
                """, (rule_code,))
            else:
                cursor.execute("""
                    SELECT id, rule_code, version, rule_name, description, rule_schema, 
                           is_active, created_at
                    FROM as1851_rules 
                    WHERE rule_code = %s AND is_active = true
                    ORDER BY version DESC
                """, (rule_code,))
            
            rows = cursor.fetchall()
            rules = []
            
            for row in rows:
                rule = AS1851Rule(
                    id=row[0],
                    rule_code=row[1],
                    version=row[2],
                    rule_name=row[3],
                    description=row[4],
                    rule_schema=row[5],
                    is_active=row[6],
                    created_at=row[7]
                )
                rules.append(rule)
        
        conn.close()
        return rules
        
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rule versions: {str(e)}"
        )

@router.put("/id/{rule_id}/deactivate", response_model=AS1851Rule, 
            summary="Deactivate Rule Version", 
            description="Deactivates a specific rule version. This is the only way to 'update' a rule - no in-place modifications allowed.")
async def deactivate_rule_version(
    rule_id: UUID,
    request: Request,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Deactivates a specific rule version. This is the only way to 'update' a rule."""
    
    try:
        with conn.cursor() as cursor:
            # Get the current rule before deactivating
            cursor.execute("""
                SELECT id, rule_code, version, rule_name, description, rule_schema, 
                       is_active, created_at
                FROM as1851_rules 
                WHERE id = %s
            """, (rule_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Rule not found"
                )
            
            if not row[6]:  # is_active
                conn.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Rule is already deactivated"
                )
            
            # Deactivate the rule
            cursor.execute("""
                UPDATE as1851_rules 
                SET is_active = false 
                WHERE id = %s
            """, (rule_id,))
            
            # Log the deactivation in audit log
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            cursor.execute("""
                INSERT INTO audit_log 
                (user_id, action, resource_type, resource_id, old_values, new_values, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                current_user.user_id,
                "deactivate_rule",
                "as1851_rule",
                rule_id,
                json.dumps({"is_active": True, "rule_code": row[1], "version": row[2]}),
                json.dumps({"is_active": False, "rule_code": row[1], "version": row[2]}),
                client_ip,
                user_agent
            ))
            
            conn.commit()
            
            # Return the deactivated rule
            deactivated_rule = AS1851Rule(
                id=row[0],
                rule_code=row[1],
                version=row[2],
                rule_name=row[3],
                description=row[4],
                rule_schema=row[5],
                is_active=False,  # Now deactivated
                created_at=row[7]
            )
        
        conn.close()
        return deactivated_rule
        
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate rule: {str(e)}"
        )