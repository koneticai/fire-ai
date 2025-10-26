import * as React from 'react';
import { select } from 'd3-selection';
import { drag } from 'd3-drag';
import { zoom } from 'd3-zoom';
import { Card } from '../molecules/Card';
import { Button } from '../atoms/Button';
import { Input } from '../atoms/Input';
import { tokens } from '../tokens';
import { useComplianceWorkflow, createWorkflowDraft } from '../hooks/useComplianceWorkflow';

const CANVAS_WIDTH = 960;
const CANVAS_HEIGHT = 600;
const NODE_SIZE = { width: 140, height: 72 };

const nodeFill = type => {
  switch (type) {
    case 'evidence':
      return '#4CAF50';
    case 'inspection':
      return '#2196F3';
    case 'approval':
      return '#FF9800';
    case 'remediation':
      return '#F44336';
    default:
      return '#9E9E9E';
  }
};

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export const ComplianceDesigner = () => {
  const svgRef = React.useRef(null);
  const [workflow, setWorkflow] = React.useState(() => createWorkflowDraft());
  const [selectedNode, setSelectedNode] = React.useState(null);
  const [isPreviewMode, setIsPreviewMode] = React.useState(false);
  const { saveWorkflow: persistWorkflow, loading: persisting, error: persistenceError } = useComplianceWorkflow();

  const handleMetaChange = React.useCallback((key, value) => {
    setWorkflow(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  const handleAddNode = React.useCallback(type => {
    setWorkflow(prev => {
      const nextNode = {
        id: `node-${Date.now()}`,
        type,
        position: {
          x: 120 + prev.workflow_definition.nodes.length * 24,
          y: 120 + prev.workflow_definition.nodes.length * 18
        },
        data: { name: `${type.charAt(0).toUpperCase()}${type.slice(1)} step` }
      };

      return {
        ...prev,
        workflow_definition: {
          ...prev.workflow_definition,
          nodes: [...prev.workflow_definition.nodes, nextNode]
        }
      };
    });
  }, []);

  const handleNodeUpdate = React.useCallback((nodeId, update) => {
    setWorkflow(prev => {
      const nextNodes = prev.workflow_definition.nodes.map(node =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...update } } : node
      );
      return {
        ...prev,
        workflow_definition: {
          ...prev.workflow_definition,
          nodes: nextNodes
        }
      };
    });
  }, []);

  const handleNodeDrag = React.useCallback((nodeId, position) => {
    setWorkflow(prev => {
      const nextNodes = prev.workflow_definition.nodes.map(node =>
        node.id === nodeId ? { ...node, position } : node
      );
      return {
        ...prev,
        workflow_definition: {
          ...prev.workflow_definition,
          nodes: nextNodes
        }
      };
    });
  }, []);

  const handleSaveWorkflow = React.useCallback(async () => {
    try {
      const saved = await persistWorkflow(workflow);
      setWorkflow(prev => ({ ...prev, ...saved }));
    } catch (error) {
      console.error('Failed to persist workflow', error);
    }
  }, [persistWorkflow, workflow]);

  React.useEffect(() => {
    if (!svgRef.current) return;

    const svg = select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${CANVAS_WIDTH} ${CANVAS_HEIGHT}`);
    svg.style('background', '#F9FAFB');

    const base = svg.append('g');

    const defs = svg.append('defs');
    defs
      .append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 9)
      .attr('refY', 5)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0 0 L 10 5 L 0 10 z')
      .attr('fill', '#6B7280');

    const edgesGroup = base.append('g').attr('class', 'edges');
    const nodesGroup = base.append('g').attr('class', 'nodes');

    const edges = edgesGroup
      .selectAll('path.edge')
      .data(workflow.workflow_definition.edges, edge => edge.id)
      .join('path')
      .attr('class', 'edge')
      .attr('stroke', '#9CA3AF')
      .attr('stroke-width', 2)
      .attr('fill', 'none')
      .attr('marker-end', 'url(#arrowhead)')
      .attr('d', edge => {
        const fromNode = workflow.workflow_definition.nodes.find(node => node.id === edge.from);
        const toNode = workflow.workflow_definition.nodes.find(node => node.id === edge.to);
        if (!fromNode || !toNode) return '';
        return `M${fromNode.position.x},${fromNode.position.y} L${toNode.position.x},${toNode.position.y}`;
      });

    edges.append('title').text(edge => edge.condition ?? '');

    const dragBehaviour = drag()
      .on('start', event => {
        event.sourceEvent.stopPropagation();
      })
      .on('drag', (event, node) => {
        const nextX = clamp(event.x, NODE_SIZE.width / 2, CANVAS_WIDTH - NODE_SIZE.width / 2);
        const nextY = clamp(event.y, NODE_SIZE.height / 2, CANVAS_HEIGHT - NODE_SIZE.height / 2);
        handleNodeDrag(node.id, { x: nextX, y: nextY });
      });

    const nodeGroups = nodesGroup
      .selectAll('g.node')
      .data(workflow.workflow_definition.nodes, node => node.id)
      .join(enter => {
        const group = enter.append('g').attr('class', 'node').style('cursor', 'move');
        group
          .append('rect')
          .attr('rx', 10)
          .attr('ry', 10)
          .attr('width', NODE_SIZE.width)
          .attr('height', NODE_SIZE.height)
          .attr('stroke-width', 2);

        group
          .append('text')
          .attr('text-anchor', 'middle')
          .attr('x', NODE_SIZE.width / 2)
          .attr('y', NODE_SIZE.height / 2)
          .attr('dy', '0.3em')
          .style('font-family', tokens.typography.fontFamily.sans)
          .style('fill', '#111827')
          .style('font-size', tokens.typography.fontSize.base);

        return group;
      });

    nodeGroups
      .attr('transform', node => `translate(${node.position.x - NODE_SIZE.width / 2}, ${node.position.y - NODE_SIZE.height / 2})`)
      .call(dragBehaviour)
      .on('click', (_, node) => {
        setSelectedNode(node);
      });

    nodeGroups
      .select('rect')
      .attr('stroke', node => (selectedNode?.id === node.id ? tokens.colors.primary : '#374151'))
      .attr('fill', node => nodeFill(node.type));

    nodeGroups
      .select('text')
      .text(node => node.data.name ?? node.type);

    svg.call(
      zoom()
        .scaleExtent([0.5, 1.5])
        .on('zoom', event => {
          base.attr('transform', event.transform.toString());
        })
    );

    return () => {
      svg.on('.zoom', null);
    };
  }, [workflow, selectedNode, handleNodeDrag]);

  React.useEffect(() => {
    if (!selectedNode) return;
    const nextNode = workflow.workflow_definition.nodes.find(node => node.id === selectedNode.id);
    if (nextNode && nextNode !== selectedNode) {
      setSelectedNode(nextNode);
    }
    if (!nextNode) {
      setSelectedNode(null);
    }
  }, [workflow, selectedNode]);

  return (
    <Card title="Compliance Workflow Designer">
      <div style={{ display: 'flex', flexDirection: 'column', gap: tokens.spacing.md }}>
        <div style={{ display: 'flex', gap: tokens.spacing.sm, flexWrap: 'wrap' }}>
          <Button onClick={() => handleAddNode('evidence')}>Add Evidence</Button>
          <Button onClick={() => handleAddNode('inspection')}>Add Inspection</Button>
          <Button onClick={() => handleAddNode('approval')}>Add Approval</Button>
          <Button onClick={() => handleAddNode('remediation')}>Add Remediation</Button>
          <Button variant="secondary" onClick={() => setIsPreviewMode(prev => !prev)}>
            {isPreviewMode ? 'Edit Mode' : 'Preview Mode'}
          </Button>
          <Button onClick={handleSaveWorkflow} disabled={persisting}>
            {persisting ? 'Saving…' : 'Save Workflow'}
          </Button>
        </div>

        {persistenceError ? (
          <div role="alert" style={{ color: tokens.colors.danger }}>
            {persistenceError}
          </div>
        ) : null}

        <div style={{ display: 'flex', gap: tokens.spacing.md, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 240, flex: '1 1 240px' }}>
            <label htmlFor="workflowName">Workflow Name</label>
            <Input
              id="workflowName"
              value={workflow.name}
              onChange={event => handleMetaChange('name', event.target.value)}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 240, flex: '1 1 240px' }}>
            <label htmlFor="complianceStandard">Compliance Standard</label>
            <Input
              id="complianceStandard"
              value={workflow.compliance_standard}
              onChange={event => handleMetaChange('compliance_standard', event.target.value)}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: tokens.spacing.lg, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 640px', minWidth: 320 }}>
            <svg ref={svgRef} width="100%" height={CANVAS_HEIGHT} role="application" aria-label="Compliance workflow canvas" />
          </div>

          {!isPreviewMode && selectedNode ? (
            <div style={{ flex: '0 0 280px', display: 'flex', flexDirection: 'column', gap: tokens.spacing.sm }}>
              <h3 style={{ margin: 0 }}>Node Properties</h3>
              <label htmlFor="nodeName">Name</label>
              <Input
                id="nodeName"
                value={selectedNode.data.name ?? ''}
                onChange={event => handleNodeUpdate(selectedNode.id, { name: event.target.value })}
              />
              <label htmlFor="nodeDescription">Description</label>
              <textarea
                id="nodeDescription"
                value={selectedNode.data.description ?? ''}
                onChange={event => handleNodeUpdate(selectedNode.id, { description: event.target.value })}
                style={{
                  minHeight: 96,
                  padding: tokens.spacing.sm,
                  borderRadius: tokens.radius.sm,
                  border: '1px solid #CED4DA',
                  fontFamily: tokens.typography.fontFamily.sans
                }}
              />
              <div>
                <strong>Type:</strong> {selectedNode.type}
              </div>
            </div>
          ) : null}

          {isPreviewMode ? (
            <div style={{ flex: '0 0 280px', display: 'flex', flexDirection: 'column', gap: tokens.spacing.sm }}>
              <h3 style={{ margin: 0 }}>Workflow Summary</h3>
              <div><strong>Name:</strong> {workflow.name}</div>
              <div><strong>Compliance Standard:</strong> {workflow.compliance_standard}</div>
              <div><strong>Steps:</strong> {workflow.workflow_definition.nodes.length}</div>
              <div><strong>Connections:</strong> {workflow.workflow_definition.edges.length}</div>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
};
