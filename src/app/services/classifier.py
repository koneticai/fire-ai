"""
Classification service for FireMode Compliance Platform
Implements business logic for fault classification using AS1851 rules
"""

import json
from typing import Tuple, Optional
from uuid import UUID

import psycopg2
import semver
from fastapi import HTTPException, status

from ..models import FaultDataInput, AS1851Rule


def classify_fault(conn, fault_data: FaultDataInput) -> Tuple[AS1851Rule, str]:
    """
    Finds the latest active rule version and applies its logic to the fault data.
    Returns the rule object used and the resulting classification.
    """
    try:
        with conn.cursor() as cursor:
            # Find all active rules for this rule code
            cursor.execute("""
                SELECT id, rule_code, version, rule_name, description, rule_schema, 
                       is_active, created_at
                FROM as1851_rules 
                WHERE rule_code = %s AND is_active = true
                ORDER BY version DESC
            """, (fault_data.item_code,))
            
            rows = cursor.fetchall()
            if not rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No active rule found for item code '{fault_data.item_code}'."
                )
            
            # Find the highest semantic version using semver comparison
            latest_rule = None
            latest_version = None
            
            for row in rows:
                try:
                    current_version = semver.VersionInfo.parse(row[2])  # version field
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No valid semantic versions found for rule {fault_data.item_code}"
                )
            
            # Apply the rule's classification logic from the rule_schema
            # Ensure rule_schema is a dict (handle potential JSONB string conversion)
            rule_schema = latest_rule.rule_schema
            if isinstance(rule_schema, str):
                try:
                    rule_schema = json.loads(rule_schema)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Invalid rule schema format for rule {latest_rule.rule_code} v{latest_rule.version}"
                    )
            
            # Look for classification mappings in the rule schema
            classification_mappings = rule_schema.get('classification_mappings', {})
            if not classification_mappings:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Rule {latest_rule.rule_code} v{latest_rule.version} does not define classification mappings."
                )
            
            # Get the classification for the observed condition
            classification = classification_mappings.get(fault_data.observed_condition)
            if not classification:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Rule {latest_rule.rule_code} v{latest_rule.version} does not define a classification for condition '{fault_data.observed_condition}'."
                )
            
            return latest_rule, classification
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to classify fault: {str(e)}"
        )


def create_audit_log(conn, user_id: UUID, fault_data: FaultDataInput, rule_used: Optional[AS1851Rule], classification: Optional[str], client_ip: str, user_agent: str, success: bool = True, error_detail: Optional[str] = None) -> UUID:
    """
    Creates an immutable audit log entry for the classification transaction.
    Returns the audit log ID.
    """
    try:
        with conn.cursor() as cursor:
            action = 'CLASSIFY_FAULT' if success else 'CLASSIFY_FAULT_FAILED'
            new_values = {
                'classification': classification,
                'rule_code': rule_used.rule_code if rule_used else None,
                'rule_version': rule_used.version if rule_used else None
            }
            if error_detail:
                new_values['error'] = error_detail
                
            cursor.execute("""
                INSERT INTO audit_log 
                (user_id, action, resource_type, resource_id, old_values, new_values, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                action,
                'as1851_rule',
                rule_used.id if rule_used else None,
                json.dumps(fault_data.model_dump()),  # Input data
                json.dumps(new_values),  # Output or error
                client_ip,
                user_agent
            ))
            
            audit_log_id = cursor.fetchone()[0]
            conn.commit()
            
            return audit_log_id
            
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create audit log: {str(e)}"
        )