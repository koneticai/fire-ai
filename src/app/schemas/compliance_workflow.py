"""Pydantic schemas for compliance workflows"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ComplianceNode(BaseModel):
    """Graph node within a compliance workflow"""

    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description="Node type: evidence | inspection | approval | remediation")
    position: Dict[str, float] = Field(..., description="Absolute canvas position")
    data: Dict[str, Any] = Field(default_factory=dict, description="Custom node metadata")


class ComplianceEdge(BaseModel):
    """Graph edge between workflow nodes"""

    model_config = ConfigDict(populate_by_name=True)

    from_node: str = Field(..., alias='from', description="Source node id")
    to_node: str = Field(..., alias='to', description="Destination node id")
    condition: Optional[str] = Field(None, description="Optional condition for transition")


class WorkflowDefinition(BaseModel):
    """Workflow graph definition"""

    model_config = ConfigDict(populate_by_name=True)

    nodes: List[ComplianceNode] = Field(..., description="Workflow nodes")
    edges: List[ComplianceEdge] = Field(default_factory=list, description="Workflow edges")

    @field_validator('nodes')
    @classmethod
    def validate_nodes(cls, v):
        if len(v) > 100:  # Max nodes limit
            raise ValueError('Workflow cannot have more than 100 nodes')
        
        # Check for duplicate node IDs
        node_ids = [node.id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError('Duplicate node IDs detected')
        
        return v
    
    @field_validator('edges')
    @classmethod
    def validate_edges(cls, v, info):
        nodes = info.data.get('nodes', [])
        node_ids = {node.id for node in nodes}
        
        # Validate edge references
        for edge in v:
            if edge.from_node not in node_ids:
                raise ValueError(f'Edge references non-existent node: {edge.from_node}')
            if edge.to_node not in node_ids:
                raise ValueError(f'Edge references non-existent node: {edge.to_node}')
        
        # TODO: Add cycle detection
        return v


class ComplianceWorkflowBase(BaseModel):
    """Shared attributes for workflow payloads"""

    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    compliance_standard: str = Field(
        default='AS1851-2012',
        min_length=1,
        max_length=100,
        description="Associated compliance standard"
    )
    workflow_definition: WorkflowDefinition = Field(..., description="Workflow graph definition")
    is_template: bool = Field(default=False, description="Whether workflow is reusable")


class ComplianceWorkflowCreate(ComplianceWorkflowBase):
    """Payload for creating workflows"""

    status: Optional[str] = Field(default='draft', pattern='^(draft|active|archived)$')


class ComplianceWorkflowUpdate(BaseModel):
    """Payload for updating workflows"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    compliance_standard: Optional[str] = Field(None, min_length=1, max_length=100)
    workflow_definition: Optional[WorkflowDefinition] = None
    status: Optional[str] = Field(None, pattern='^(draft|active|archived)$')
    is_template: Optional[bool] = None


class ComplianceWorkflowRead(ComplianceWorkflowBase):
    """Read model for workflows"""

    id: UUID = Field(..., description="Workflow identifier")
    status: str = Field(..., description="Workflow status")
    created_by: UUID = Field(..., description="Author id")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        populate_by_name = True


class ComplianceWorkflowInstanceCreate(BaseModel):
    """Payload for starting workflow instances"""

    workflow_id: UUID = Field(..., description="Workflow template id")
    building_id: UUID = Field(..., description="Building id")


class ComplianceWorkflowInstanceRead(BaseModel):
    """Read model for workflow instances"""

    id: UUID = Field(..., description="Instance id")
    workflow_id: UUID = Field(..., description="Workflow template id")
    building_id: UUID = Field(..., description="Building id")
    current_node_id: Optional[str] = Field(None, description="Current node id")
    status: str = Field(..., description="Instance status")
    started_at: datetime = Field(..., description="Instance start time")
    completed_at: Optional[datetime] = Field(None, description="Instance completion time")

    class Config:
        from_attributes = True
        populate_by_name = True
