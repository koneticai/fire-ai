"""
AS1851 rules router for FireMode Compliance Platform
Handles rule management and fault classification
"""

import json
from datetime import datetime
from typing import List
from uuid import UUID

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import (
    AS1851Rule, AS1851RuleCreate, FaultClassificationRequest, 
    FaultClassificationResult, APIResponse
)
from ..dependencies import get_current_active_user, get_database_connection, TokenData

router = APIRouter(tags=["AS1851 Rules"])

@router.get("/", response_model=List[AS1851Rule], summary="List AS1851 Rules", description="Retrieve all active AS1851 compliance rules available in the system, sorted by rule code")
async def list_rules(
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """List all active AS1851 rules"""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, rule_code, rule_name, description, rule_schema, 
                       is_active, created_at, updated_at
                FROM as1851_rules 
                WHERE is_active = true
                ORDER BY rule_code
            """)
            
            rows = cursor.fetchall()
            rules = []
            
            for row in rows:
                rule = AS1851Rule(
                    id=row[0],
                    rule_code=row[1],
                    rule_name=row[2],
                    description=row[3],
                    rule_schema=row[4],
                    is_active=row[5],
                    created_at=row[6],
                    updated_at=row[7]
                )
                rules.append(rule)
        
        conn.close()
        return rules
        
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list rules: {str(e)}"
        )

@router.post("/", response_model=AS1851Rule, summary="Create AS1851 Rule", description="Create a new AS1851 compliance rule with schema definition for fault classification")
async def create_rule(
    rule_data: AS1851RuleCreate,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Create a new AS1851 rule"""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO as1851_rules 
                (rule_code, rule_name, description, rule_schema, is_active)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, created_at, updated_at
            """, (
                rule_data.rule_code,
                rule_data.rule_name,
                rule_data.description,
                json.dumps(rule_data.rule_schema),
                rule_data.is_active
            ))
            
            result = cursor.fetchone()
            rule_id, created_at, updated_at = result
            
            conn.commit()
        
        conn.close()
        
        return AS1851Rule(
            id=rule_id,
            rule_code=rule_data.rule_code,
            rule_name=rule_data.rule_name,
            description=rule_data.description,
            rule_schema=rule_data.rule_schema,
            is_active=rule_data.is_active,
            created_at=created_at,
            updated_at=updated_at
        )
        
    except psycopg2.IntegrityError as e:
        conn.close()
        if "rule_code" in str(e):
            raise HTTPException(
                status_code=400,
                detail="Rule code already exists"
            )
        raise HTTPException(
            status_code=400,
            detail=f"Database integrity error: {str(e)}"
        )
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create rule: {str(e)}"
        )

@router.get("/{rule_code}", response_model=AS1851Rule, summary="Get AS1851 Rule", description="Retrieve a specific AS1851 rule by its unique rule code")
async def get_rule(
    rule_code: str,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Get a specific rule by code"""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, rule_code, rule_name, description, rule_schema,
                       is_active, created_at, updated_at
                FROM as1851_rules 
                WHERE rule_code = %s
            """, (rule_code,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            rule = AS1851Rule(
                id=row[0],
                rule_code=row[1],
                rule_name=row[2],
                description=row[3],
                rule_schema=row[4],
                is_active=row[5],
                created_at=row[6],
                updated_at=row[7]
            )
        
        conn.close()
        return rule
        
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get rule: {str(e)}"
        )

@router.post("/classify-faults", response_model=FaultClassificationResult, summary="Classify Faults", description="Apply AS1851 rules to evidence for automated fault classification and compliance assessment")
async def classify_faults(
    classification_request: FaultClassificationRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Classify faults based on evidence and rules"""
    
    try:
        # Get evidence details
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, session_id, evidence_type, metadata, checksum
                FROM evidence 
                WHERE id = %s
            """, (classification_request.evidence_id,))
            
            evidence_row = cursor.fetchone()
            if not evidence_row:
                raise HTTPException(status_code=404, detail="Evidence not found")
            
            evidence_id, session_id, evidence_type, metadata, checksum = evidence_row
            
            # Get requested rules
            placeholders = ','.join(['%s'] * len(classification_request.rule_codes))
            cursor.execute(f"""
                SELECT rule_code, rule_name, rule_schema
                FROM as1851_rules 
                WHERE rule_code IN ({placeholders}) AND is_active = true
            """, classification_request.rule_codes)
            
            rules = cursor.fetchall()
            
            if not rules:
                raise HTTPException(status_code=400, detail="No valid rules found")
            
            # Apply rule schemas (simplified implementation)
            classifications = []
            confidence_scores = {}
            
            for rule_code, rule_name, rule_schema in rules:
                # Simplified rule application logic
                classification = {
                    "rule_code": rule_code,
                    "rule_name": rule_name,
                    "evidence_type": evidence_type,
                    "applied_schema": rule_schema,
                    "result": "compliant",  # Simplified - would contain actual classification logic
                    "details": {
                        "checksum_verified": bool(checksum),
                        "metadata_complete": bool(metadata),
                        "context_provided": bool(classification_request.context)
                    }
                }
                classifications.append(classification)
                confidence_scores[rule_code] = 0.85  # Mock confidence score
            
            # Log the classification in audit_log
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            cursor.execute("""
                INSERT INTO audit_log 
                (user_id, action, resource_type, resource_id, new_values, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                current_user.user_id,
                "classify_faults",
                "evidence",
                evidence_id,
                json.dumps({
                    "rule_codes": classification_request.rule_codes,
                    "classifications": classifications,
                    "confidence_scores": confidence_scores
                }),
                client_ip,
                user_agent
            ))
            
            conn.commit()
        
        conn.close()
        
        return FaultClassificationResult(
            evidence_id=classification_request.evidence_id,
            classifications=classifications,
            confidence_scores=confidence_scores,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to classify faults: {str(e)}"
        )

@router.put("/{rule_code}/deactivate", response_model=APIResponse, summary="Deactivate Rule", description="Deactivate an AS1851 rule to prevent it from being used in new fault classifications")
async def deactivate_rule(
    rule_code: str,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """Deactivate a rule"""
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE as1851_rules 
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE rule_code = %s
            """, (rule_code,))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            conn.commit()
        
        conn.close()
        
        return APIResponse(
            status="success",
            message=f"Rule {rule_code} deactivated successfully"
        )
        
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate rule: {str(e)}"
        )