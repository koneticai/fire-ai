"""Compliance workflow API endpoints"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_active_user
from ..database.core import get_db
from ..models.compliance_workflow import ComplianceWorkflow, ComplianceWorkflowInstance
from ..schemas.compliance_workflow import (
    ComplianceWorkflowCreate,
    ComplianceWorkflowUpdate,
    ComplianceWorkflowRead,
    ComplianceWorkflowInstanceCreate,
    ComplianceWorkflowInstanceRead,
)
from ..schemas.token import TokenData


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/compliance/workflows", tags=["compliance-workflows"])


async def verify_workflow_access(
    workflow: ComplianceWorkflow,
    current_user: TokenData,
    require_ownership: bool = False
) -> None:
    """Verify user has access to workflow"""
    if workflow.created_by != current_user.user_id:
        if require_ownership:
            raise HTTPException(status_code=403, detail="Not authorized")
        # TODO: Add organization-level access check
        raise HTTPException(status_code=403, detail="Not authorized")


def _workflow_definition_payload(definition):
    if definition is None:
        return None
    return definition.model_dump(by_alias=True)


@router.post("/", response_model=ComplianceWorkflowRead, status_code=201)
async def create_workflow(
    workflow_data: ComplianceWorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user),
):
    """
    Create a new compliance workflow
    
    Example Request:
    ```json
    {
      "name": "Fire Extinguisher Inspection",
      "description": "Monthly inspection workflow",
      "compliance_standard": "AS1851-2012",
      "workflow_definition": {
        "nodes": [
          {
            "id": "node1",
            "type": "evidence",
            "position": {"x": 100, "y": 100},
            "data": {"name": "Collect photos"}
          }
        ],
        "edges": []
      }
    }
    ```
    """

    workflow = ComplianceWorkflow(
        name=workflow_data.name,
        description=workflow_data.description,
        compliance_standard=workflow_data.compliance_standard,
        workflow_definition=_workflow_definition_payload(workflow_data.workflow_definition),
        status=workflow_data.status or 'draft',
        is_template=workflow_data.is_template,
        created_by=current_user.user_id,
    )

    db.add(workflow)

    try:
        await db.commit()
        await db.refresh(workflow)
        logger.info("Created compliance workflow %s", workflow.id)
        return workflow
    except Exception as exc:  # pragma: no cover - logged and re-raised
        await db.rollback()
        logger.error("Failed to create workflow: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create workflow")


@router.get("/", response_model=List[ComplianceWorkflowRead])
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, pattern="^(draft|active|archived)$"),
    compliance_standard: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user),
):
    """List compliance workflows with optional filters"""

    query = select(ComplianceWorkflow)

    if status:
        query = query.where(ComplianceWorkflow.status == status)
    if compliance_standard:
        query = query.where(ComplianceWorkflow.compliance_standard == compliance_standard)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    workflows = result.scalars().all()
    return workflows


@router.get("/{workflow_id}", response_model=ComplianceWorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user),
):
    """Retrieve a workflow by id"""

    result = await db.execute(
        select(ComplianceWorkflow).where(ComplianceWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Verify user has access to this workflow
    await verify_workflow_access(workflow, current_user)

    return workflow


@router.put("/{workflow_id}", response_model=ComplianceWorkflowRead)
async def update_workflow(
    workflow_id: UUID,
    workflow_data: ComplianceWorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user),
):
    """Update workflow metadata or definition"""

    result = await db.execute(
        select(ComplianceWorkflow).where(ComplianceWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Verify user has ownership of this workflow
    await verify_workflow_access(workflow, current_user, require_ownership=True)

    payload = workflow_data.model_dump(exclude_unset=True)

    if 'workflow_definition' in payload and payload['workflow_definition'] is not None:
        payload['workflow_definition'] = workflow_data.workflow_definition.model_dump(by_alias=True)

    for field, value in payload.items():
        setattr(workflow, field, value)

    try:
        await db.commit()
        await db.refresh(workflow)
        logger.info("Updated compliance workflow %s", workflow_id)
        return workflow
    except Exception as exc:  # pragma: no cover - logged and re-raised
        await db.rollback()
        logger.error("Failed to update workflow %s: %s", workflow_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update workflow")


@router.get("/instances", response_model=List[ComplianceWorkflowInstanceRead])
async def list_workflow_instances(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    workflow_id: Optional[UUID] = Query(None),
    building_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None, pattern="^(active|completed|failed|paused)$"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user)
):
    """List workflow instances with filtering"""
    query = select(ComplianceWorkflowInstance)
    
    if workflow_id:
        query = query.where(ComplianceWorkflowInstance.workflow_id == workflow_id)
    if building_id:
        query = query.where(ComplianceWorkflowInstance.building_id == building_id)
    if status:
        query = query.where(ComplianceWorkflowInstance.status == status)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/instances", response_model=ComplianceWorkflowInstanceRead, status_code=201)
async def create_workflow_instance(
    instance_data: ComplianceWorkflowInstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user),
):
    """
    Create a workflow instance for a building
    
    Example Request:
    ```json
    {
      "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
      "building_id": "123e4567-e89b-12d3-a456-426614174001"
    }
    ```
    """

    result = await db.execute(
        select(ComplianceWorkflow).where(ComplianceWorkflow.id == instance_data.workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    instance = ComplianceWorkflowInstance(
        workflow_id=instance_data.workflow_id,
        building_id=instance_data.building_id,
        instance_data={},
    )

    db.add(instance)

    try:
        await db.commit()
        await db.refresh(instance)
        logger.info("Created workflow instance %s", instance.id)
        return instance
    except Exception as exc:  # pragma: no cover
        await db.rollback()
        logger.error("Failed to create workflow instance: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create workflow instance")


@router.get("/instances/{instance_id}", response_model=ComplianceWorkflowInstanceRead)
async def get_workflow_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user),
):
    """Retrieve workflow instance state"""

    result = await db.execute(
        select(ComplianceWorkflowInstance).where(ComplianceWorkflowInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    return instance


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user)
):
    """Delete a workflow (soft delete recommended)"""
    result = await db.execute(
        select(ComplianceWorkflow).where(ComplianceWorkflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Verify ownership
    await verify_workflow_access(workflow, current_user, require_ownership=True)
    
    # Soft delete: archive instead of hard delete
    workflow.status = 'archived'
    await db.commit()
    
    logger.info(f"Archived workflow {workflow_id}")


@router.delete("/instances/{instance_id}", status_code=204)
async def delete_workflow_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(get_current_active_user)
):
    """Delete a workflow instance"""
    result = await db.execute(
        select(ComplianceWorkflowInstance).where(ComplianceWorkflowInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    
    # For now, allow deletion of any instance - could add ownership check later
    # by joining with workflow table
    
    await db.delete(instance)
    await db.commit()
    
    logger.info(f"Deleted workflow instance {instance_id}")
