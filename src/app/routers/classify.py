"""
Classification router for FireMode Compliance Platform
Implements the v1/classify endpoint for fault classification
"""

from fastapi import APIRouter, Depends, status, Request, HTTPException

from ..models import FaultDataInput, ClassificationResult, TokenData
from ..dependencies import get_current_active_user, get_database_connection
from ..services.classifier import classify_fault, create_audit_log

router = APIRouter(tags=["Classification"])

@router.post("", response_model=ClassificationResult, status_code=status.HTTP_200_OK,
             summary="Classify Fault",
             description="Classifies a fault based on the latest active AS1851 rule and creates an immutable audit log of the transaction.")
async def create_classification(
    fault_data: FaultDataInput,
    request: Request,
    current_user: TokenData = Depends(get_current_active_user),
    conn = Depends(get_database_connection)
):
    """
    Classifies a fault based on the latest active AS1851 rule
    and creates an immutable audit log of the transaction.
    """
    # Get client metadata for audit logging
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        # 1. Get classification and the specific rule version used
        rule_used, classification_result = classify_fault(conn, fault_data)
        
        # 2. Create the immutable audit log entry for successful classification
        audit_log_id = create_audit_log(
            conn,
            current_user.user_id,
            fault_data,
            rule_used,
            classification_result,
            client_ip,
            user_agent,
            success=True
        )
        
        conn.close()
        
        # 3. Return the result to the user
        return ClassificationResult(
            classification=classification_result,
            rule_applied=rule_used.rule_code,
            version_applied=rule_used.version,
            audit_log_id=audit_log_id
        )
        
    except HTTPException as e:
        # Log failed classification attempts for compliance
        try:
            create_audit_log(
                conn,
                current_user.user_id,
                fault_data,
                None,  # No rule found/used
                None,  # No classification
                client_ip,
                user_agent,
                success=False,
                error_detail=e.detail
            )
        except Exception:
            # If audit logging fails, continue with original error
            pass
        conn.close()
        raise
    except Exception as e:
        # Log unexpected errors
        try:
            create_audit_log(
                conn,
                current_user.user_id,
                fault_data,
                None,
                None,
                client_ip,
                user_agent,
                success=False,
                error_detail=str(e)
            )
        except Exception:
            pass
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification failed"
        )