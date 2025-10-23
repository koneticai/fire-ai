"""
Integration tests for compliance workflow API endpoints
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.app.schemas.compliance_workflow import (
    ComplianceWorkflowCreate,
    WorkflowDefinition,
    ComplianceNode,
    ComplianceEdge,
    ComplianceWorkflowInstanceCreate
)


@pytest.mark.asyncio
async def test_workflow_lifecycle(test_client: AsyncClient, auth_headers: dict):
    """Test full workflow CRUD lifecycle"""
    
    # Create workflow
    workflow_data = {
        "name": "Test Workflow",
        "description": "Integration test workflow",
        "compliance_standard": "AS1851-2012",
        "workflow_definition": {
            "nodes": [
                {
                    "id": "node1",
                    "type": "evidence",
                    "position": {"x": 100, "y": 100},
                    "data": {"name": "Collect evidence"}
                }
            ],
            "edges": []
        }
    }
    
    response = await test_client.post(
        "/v1/compliance/workflows",
        json=workflow_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    workflow = response.json()
    workflow_id = workflow["id"]
    
    # Get workflow
    response = await test_client.get(
        f"/v1/compliance/workflows/{workflow_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    retrieved_workflow = response.json()
    assert retrieved_workflow["name"] == "Test Workflow"
    
    # Update workflow
    update_data = {
        "name": "Updated Test Workflow",
        "description": "Updated description"
    }
    response = await test_client.put(
        f"/v1/compliance/workflows/{workflow_id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    updated_workflow = response.json()
    assert updated_workflow["name"] == "Updated Test Workflow"
    
    # List workflows
    response = await test_client.get(
        "/v1/compliance/workflows",
        headers=auth_headers
    )
    assert response.status_code == 200
    workflows = response.json()
    assert len(workflows) >= 1
    assert any(w["id"] == workflow_id for w in workflows)
    
    # Archive workflow (soft delete)
    response = await test_client.delete(
        f"/v1/compliance/workflows/{workflow_id}",
        headers=auth_headers
    )
    assert response.status_code == 204
    
    # Verify workflow is archived
    response = await test_client.get(
        f"/v1/compliance/workflows/{workflow_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    archived_workflow = response.json()
    assert archived_workflow["status"] == "archived"


@pytest.mark.asyncio
async def test_workflow_instance_lifecycle(test_client: AsyncClient, auth_headers: dict):
    """Test workflow instance creation and management"""
    
    # First create a workflow
    workflow_data = {
        "name": "Instance Test Workflow",
        "compliance_standard": "AS1851-2012",
        "workflow_definition": {
            "nodes": [
                {
                    "id": "node1",
                    "type": "evidence",
                    "position": {"x": 100, "y": 100},
                    "data": {"name": "Collect evidence"}
                }
            ],
            "edges": []
        }
    }
    
    response = await test_client.post(
        "/v1/compliance/workflows",
        json=workflow_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    workflow = response.json()
    workflow_id = workflow["id"]
    
    # Create workflow instance
    instance_data = {
        "workflow_id": workflow_id,
        "building_id": str(uuid4())  # Mock building ID
    }
    
    response = await test_client.post(
        "/v1/compliance/workflows/instances",
        json=instance_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    instance = response.json()
    instance_id = instance["id"]
    
    # Get instance
    response = await test_client.get(
        f"/v1/compliance/workflows/instances/{instance_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    retrieved_instance = response.json()
    assert retrieved_instance["workflow_id"] == workflow_id
    
    # List instances
    response = await test_client.get(
        "/v1/compliance/workflows/instances",
        headers=auth_headers
    )
    assert response.status_code == 200
    instances = response.json()
    assert len(instances) >= 1
    assert any(i["id"] == instance_id for i in instances)
    
    # Delete instance
    response = await test_client.delete(
        f"/v1/compliance/workflows/instances/{instance_id}",
        headers=auth_headers
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_workflow_validation_errors(test_client: AsyncClient, auth_headers: dict):
    """Test workflow validation error cases"""
    
    # Test with too many nodes
    workflow_data = {
        "name": "Invalid Workflow",
        "compliance_standard": "AS1851-2012",
        "workflow_definition": {
            "nodes": [
                {
                    "id": f"node{i}",
                    "type": "evidence",
                    "position": {"x": 100, "y": 100},
                    "data": {"name": f"Node {i}"}
                }
                for i in range(101)  # Exceeds 100 node limit
            ],
            "edges": []
        }
    }
    
    response = await test_client.post(
        "/v1/compliance/workflows",
        json=workflow_data,
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error
    
    # Test with duplicate node IDs
    workflow_data = {
        "name": "Invalid Workflow",
        "compliance_standard": "AS1851-2012",
        "workflow_definition": {
            "nodes": [
                {
                    "id": "duplicate",
                    "type": "evidence",
                    "position": {"x": 100, "y": 100},
                    "data": {"name": "Node 1"}
                },
                {
                    "id": "duplicate",  # Same ID
                    "type": "inspection",
                    "position": {"x": 200, "y": 200},
                    "data": {"name": "Node 2"}
                }
            ],
            "edges": []
        }
    }
    
    response = await test_client.post(
        "/v1/compliance/workflows",
        json=workflow_data,
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_workflow_authorization(test_client: AsyncClient, auth_headers: dict, other_user_headers: dict):
    """Test workflow authorization scenarios"""
    
    # Create workflow with first user
    workflow_data = {
        "name": "Private Workflow",
        "compliance_standard": "AS1851-2012",
        "workflow_definition": {
            "nodes": [],
            "edges": []
        }
    }
    
    response = await test_client.post(
        "/v1/compliance/workflows",
        json=workflow_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    workflow = response.json()
    workflow_id = workflow["id"]
    
    # Try to access with different user (should fail)
    response = await test_client.get(
        f"/v1/compliance/workflows/{workflow_id}",
        headers=other_user_headers
    )
    assert response.status_code == 403  # Forbidden
    
    # Try to update with different user (should fail)
    update_data = {"name": "Hacked Workflow"}
    response = await test_client.put(
        f"/v1/compliance/workflows/{workflow_id}",
        json=update_data,
        headers=other_user_headers
    )
    assert response.status_code == 403  # Forbidden
    
    # Try to delete with different user (should fail)
    response = await test_client.delete(
        f"/v1/compliance/workflows/{workflow_id}",
        headers=other_user_headers
    )
    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_workflow_pagination(test_client: AsyncClient, auth_headers: dict):
    """Test workflow list pagination"""
    
    # Create multiple workflows
    for i in range(5):
        workflow_data = {
            "name": f"Pagination Test Workflow {i}",
            "compliance_standard": "AS1851-2012",
            "workflow_definition": {
                "nodes": [],
                "edges": []
            }
        }
        
        response = await test_client.post(
            "/v1/compliance/workflows",
            json=workflow_data,
            headers=auth_headers
        )
        assert response.status_code == 201
    
    # Test pagination
    response = await test_client.get(
        "/v1/compliance/workflows?limit=3&skip=0",
        headers=auth_headers
    )
    assert response.status_code == 200
    workflows = response.json()
    assert len(workflows) <= 3
    
    # Test second page
    response = await test_client.get(
        "/v1/compliance/workflows?limit=3&skip=3",
        headers=auth_headers
    )
    assert response.status_code == 200
    workflows_page2 = response.json()
    assert len(workflows_page2) <= 3
    
    # Ensure no overlap
    page1_ids = {w["id"] for w in workflows}
    page2_ids = {w["id"] for w in workflows_page2}
    assert len(page1_ids.intersection(page2_ids)) == 0


@pytest.mark.asyncio
async def test_workflow_filtering(test_client: AsyncClient, auth_headers: dict):
    """Test workflow filtering by status and compliance standard"""
    
    # Create workflows with different statuses
    workflow_data = {
        "name": "Draft Workflow",
        "compliance_standard": "AS1851-2012",
        "status": "draft",
        "workflow_definition": {
            "nodes": [],
            "edges": []
        }
    }
    
    response = await test_client.post(
        "/v1/compliance/workflows",
        json=workflow_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    
    # Filter by status
    response = await test_client.get(
        "/v1/compliance/workflows?status=draft",
        headers=auth_headers
    )
    assert response.status_code == 200
    workflows = response.json()
    assert all(w["status"] == "draft" for w in workflows)
    
    # Filter by compliance standard
    response = await test_client.get(
        "/v1/compliance/workflows?compliance_standard=AS1851-2012",
        headers=auth_headers
    )
    assert response.status_code == 200
    workflows = response.json()
    assert all(w["compliance_standard"] == "AS1851-2012" for w in workflows)


@pytest.mark.asyncio
async def test_workflow_not_found(test_client: AsyncClient, auth_headers: dict):
    """Test 404 responses for non-existent workflows"""
    
    fake_id = str(uuid4())
    
    # Get non-existent workflow
    response = await test_client.get(
        f"/v1/compliance/workflows/{fake_id}",
        headers=auth_headers
    )
    assert response.status_code == 404
    
    # Update non-existent workflow
    response = await test_client.put(
        f"/v1/compliance/workflows/{fake_id}",
        json={"name": "Updated"},
        headers=auth_headers
    )
    assert response.status_code == 404
    
    # Delete non-existent workflow
    response = await test_client.delete(
        f"/v1/compliance/workflows/{fake_id}",
        headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_workflow_instance_not_found(test_client: AsyncClient, auth_headers: dict):
    """Test 404 responses for non-existent workflow instances"""
    
    fake_id = str(uuid4())
    
    # Get non-existent instance
    response = await test_client.get(
        f"/v1/compliance/workflows/instances/{fake_id}",
        headers=auth_headers
    )
    assert response.status_code == 404
    
    # Delete non-existent instance
    response = await test_client.delete(
        f"/v1/compliance/workflows/instances/{fake_id}",
        headers=auth_headers
    )
    assert response.status_code == 404
