"""Unit tests for compliance workflow models and schemas"""

from uuid import uuid4

import pytest

from src.app.models.compliance_workflow import (
    ComplianceWorkflow,
    ComplianceWorkflowInstance,
)
from src.app.schemas.compliance_workflow import (
    ComplianceWorkflowCreate,
    ComplianceWorkflowUpdate,
    WorkflowDefinition,
    ComplianceNode,
    ComplianceEdge,
)


def test_compliance_workflow_defaults():
    """Ensure default workflow values are applied"""

    workflow = ComplianceWorkflow(
        name="Test Workflow",
        compliance_standard="AS1851-2012",
        workflow_definition={"nodes": [], "edges": []},
        created_by=uuid4(),
    )

    assert workflow.workflow_definition == {"nodes": [], "edges": []}
    assert workflow.status is None
    assert workflow.is_template is None

    status_column = ComplianceWorkflow.__table__.c.status
    template_column = ComplianceWorkflow.__table__.c.is_template

    assert status_column.default.arg == 'draft'
    assert str(status_column.server_default.arg) == 'draft'
    assert template_column.default.arg is False
    assert str(template_column.server_default.arg) == 'false'


def test_compliance_workflow_instance_defaults():
    """Ensure workflow instance defaults match expectations"""

    instance = ComplianceWorkflowInstance(
        workflow_id=uuid4(),
        building_id=uuid4(),
        instance_data={},
    )

    assert instance.status is None
    assert ComplianceWorkflowInstance.__table__.c.status.default.arg == 'active'
    assert instance.current_node_id is None
    assert instance.completed_at is None


def test_workflow_definition_schema_alias_dump():
    """Workflow definition should preserve alias names on dump"""

    node = ComplianceNode(
        id="node-1",
        type="evidence",
        position={"x": 120.0, "y": 150.0},
        data={"name": "Collect photos"},
    )
    edge = ComplianceEdge(
        from_node="node-1",
        to_node="node-2",
        condition="completed",
    )

    definition = WorkflowDefinition(nodes=[node], edges=[edge])
    dumped = definition.model_dump(by_alias=True)

    assert dumped["nodes"][0]["data"]["name"] == "Collect photos"
    assert dumped["edges"][0]["from"] == "node-1"
    assert dumped["edges"][0]["to"] == "node-2"


def test_workflow_create_schema_defaults():
    """Create schema should apply default status"""

    definition = WorkflowDefinition(nodes=[], edges=[])
    payload = ComplianceWorkflowCreate(
        name="Template",
        description="Basic template",
        compliance_standard="AS1851-2012",
        workflow_definition=definition,
    )

    assert payload.status == 'draft'
    assert payload.workflow_definition.nodes == []


@pytest.mark.parametrize("status", [None, 'active'])
def test_workflow_update_schema(status):
    """Update schema allows optional status changes"""

    update = ComplianceWorkflowUpdate(status=status)
    assert update.status == status


def test_workflow_validation_max_nodes():
    """Test workflow validation with too many nodes"""
    
    # Create 101 nodes (exceeds limit of 100)
    nodes = [
        ComplianceNode(
            id=f"node{i}",
            type="evidence",
            position={"x": 100, "y": 100},
            data={"name": f"Node {i}"}
        )
        for i in range(101)
    ]
    
    definition = WorkflowDefinition(nodes=nodes, edges=[])
    
    with pytest.raises(ValueError, match="Workflow cannot have more than 100 nodes"):
        ComplianceWorkflowCreate(
            name="Test Workflow",
            compliance_standard="AS1851-2012",
            workflow_definition=definition
        )


def test_workflow_validation_duplicate_node_ids():
    """Test workflow validation with duplicate node IDs"""
    
    nodes = [
        ComplianceNode(
            id="duplicate",
            type="evidence",
            position={"x": 100, "y": 100},
            data={"name": "Node 1"}
        ),
        ComplianceNode(
            id="duplicate",  # Same ID
            type="inspection",
            position={"x": 200, "y": 200},
            data={"name": "Node 2"}
        )
    ]
    
    definition = WorkflowDefinition(nodes=nodes, edges=[])
    
    with pytest.raises(ValueError, match="Duplicate node IDs detected"):
        ComplianceWorkflowCreate(
            name="Test Workflow",
            compliance_standard="AS1851-2012",
            workflow_definition=definition
        )


def test_workflow_validation_invalid_edge_references():
    """Test workflow validation with invalid edge references"""
    
    nodes = [
        ComplianceNode(
            id="node1",
            type="evidence",
            position={"x": 100, "y": 100},
            data={"name": "Node 1"}
        )
    ]
    
    edges = [
        ComplianceEdge(
            from_node="node1",
            to_node="nonexistent"  # References non-existent node
        )
    ]
    
    definition = WorkflowDefinition(nodes=nodes, edges=edges)
    
    with pytest.raises(ValueError, match="Edge references non-existent node"):
        ComplianceWorkflowCreate(
            name="Test Workflow",
            compliance_standard="AS1851-2012",
            workflow_definition=definition
        )


def test_workflow_validation_valid_workflow():
    """Test workflow validation with valid workflow"""
    
    nodes = [
        ComplianceNode(
            id="node1",
            type="evidence",
            position={"x": 100, "y": 100},
            data={"name": "Node 1"}
        ),
        ComplianceNode(
            id="node2",
            type="inspection",
            position={"x": 200, "y": 200},
            data={"name": "Node 2"}
        )
    ]
    
    edges = [
        ComplianceEdge(
            from_node="node1",
            to_node="node2"
        )
    ]
    
    definition = WorkflowDefinition(nodes=nodes, edges=edges)
    
    # Should not raise any exception
    workflow = ComplianceWorkflowCreate(
        name="Test Workflow",
        compliance_standard="AS1851-2012",
        workflow_definition=definition
    )
    
    assert workflow.name == "Test Workflow"
    assert len(workflow.workflow_definition.nodes) == 2
    assert len(workflow.workflow_definition.edges) == 1


def test_compliance_workflow_instance_defaults():
    """Test that instance defaults are properly set"""
    
    instance = ComplianceWorkflowInstance(
        workflow_id=uuid4(),
        building_id=uuid4(),
        instance_data={}
    )
    
    # These should be None until after commit/refresh
    assert instance.status is None
    assert instance.current_node_id is None
    assert instance.completed_at is None
    assert instance.instance_data == {}
