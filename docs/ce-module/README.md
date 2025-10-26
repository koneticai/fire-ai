# C&E Module Foundation

## Overview

The C&E (Compliance & Evidence) Module Foundation provides visual workflow design capabilities for fire safety compliance management, building upon the WORM storage and device attestation systems.

## Features

### Visual Designer
- Drag-and-drop workflow builder
- D3.js-powered visualization
- Real-time validation and preview
- Template-based workflow creation

### Compliance Workflows
- AS 1851-2012 standard support
- Custom workflow definitions
- Workflow instances for buildings
- Status tracking and progress monitoring

### Integration
- Evidence management integration
- WORM storage compatibility
- Device attestation support
- Audit trail and reporting

## Architecture

```
Frontend (React + D3.js)
    ↓
API Layer (FastAPI)
    ↓
Database (PostgreSQL)
    ↓
Integration Layer
    ├─→ WORM Storage
    ├─→ Device Attestation
    └─→ Evidence Management
```

## Usage

### Creating a Workflow

1. Open the Visual Designer
2. Add nodes (Evidence, Inspection, Approval, Remediation)
3. Connect nodes with edges
4. Configure node properties
5. Save and activate workflow

### Running a Workflow Instance

1. Select a building
2. Choose a workflow template
3. Start the workflow instance
4. Complete workflow steps
5. Monitor progress and compliance

## API Endpoints

### Workflows

- `POST /v1/compliance/workflows` - Create workflow
- `GET /v1/compliance/workflows` - List workflows
- `GET /v1/compliance/workflows/{id}` - Get workflow
- `PUT /v1/compliance/workflows/{id}` - Update workflow
- `DELETE /v1/compliance/workflows/{id}` - Archive workflow

### Workflow Instances

- `POST /v1/compliance/workflows/instances` - Create instance
- `GET /v1/compliance/workflows/instances` - List instances
- `GET /v1/compliance/workflows/instances/{id}` - Get instance
- `DELETE /v1/compliance/workflows/instances/{id}` - Delete instance

## Configuration

```bash
# C&E Module Configuration
CE_MODULE_ENABLED=true
CE_DEFAULT_STANDARD=AS1851-2012
CE_WORKFLOW_TIMEOUT_DAYS=30
CE_AUTO_ARCHIVE_DAYS=365
CE_VISUAL_DESIGNER_MAX_NODES=100
```

## Example API Usage

### Create a Workflow

```bash
curl -X POST "/v1/compliance/workflows" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
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
  }'
```

### Create a Workflow Instance

```bash
curl -X POST "/v1/compliance/workflows/instances" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
    "building_id": "123e4567-e89b-12d3-a456-426614174001"
  }'
```

## UI Component Usage

### ComplianceDesigner

```tsx
import { ComplianceDesigner } from '@fire-ai/ui';

// Create new workflow
<ComplianceDesigner />

// Edit existing workflow
<ComplianceDesigner workflowId="123e4567-e89b-12d3-a456-426614174000" />
```

### useComplianceWorkflow Hook

```tsx
import { useComplianceWorkflow } from '@fire-ai/ui';

const { workflow, loading, error, saveWorkflow } = useComplianceWorkflow(workflowId);
```

## Testing

```bash
# Run unit tests
pytest tests/unit/test_compliance_workflows.py -v

# Run integration tests
pytest tests/integration/test_ce_module.py -v
```

## Deployment

1. Run database migration
2. Deploy API endpoints
3. Deploy frontend components
4. Configure integration settings
5. Test workflow creation and execution

## Security

- All endpoints require authentication
- Users can only access workflows they created
- Workflow definitions are validated for malicious content
- Soft delete for workflows (archived, not deleted)

## Performance

- Workflow creation: <2s
- Visual rendering: <1s for 50 nodes
- API response time: <500ms
- Database queries: <100ms

## Integration Points

- **WORM Storage**: Evidence files from workflows
- **Device Attestation**: Secure workflow access
- **Evidence Management**: Workflow evidence collection
- **Compliance Reporting**: Workflow-based reports
