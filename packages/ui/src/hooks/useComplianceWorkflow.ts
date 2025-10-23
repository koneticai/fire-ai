import { useState, useEffect, useCallback } from 'react';

export type ComplianceNodeType = 'evidence' | 'inspection' | 'approval' | 'remediation';

export interface ComplianceNode {
  id: string;
  type: ComplianceNodeType;
  position: { x: number; y: number };
  data: { name: string; description?: string };
}

export interface ComplianceEdge {
  id: string;
  from: string;
  to: string;
  condition?: string;
}

export interface WorkflowDefinition {
  nodes: ComplianceNode[];
  edges: ComplianceEdge[];
}

export interface ComplianceWorkflow {
  id?: string;
  name: string;
  description?: string;
  compliance_standard: string;
  workflow_definition: WorkflowDefinition;
  status?: 'draft' | 'active' | 'archived';
  is_template?: boolean;
  created_at?: string;
  updated_at?: string;
}

export const createWorkflowDraft = (): ComplianceWorkflow => ({
  name: 'Draft Compliance Workflow',
  description: '',
  compliance_standard: 'AS1851-2012',
  workflow_definition: { nodes: [], edges: [] },
  status: 'draft',
  is_template: false
});

interface UseComplianceWorkflowResult {
  workflow: ComplianceWorkflow | null;
  loading: boolean;
  error: string | null;
  fetchWorkflow: (id: string) => Promise<ComplianceWorkflow | null>;
  saveWorkflow: (payload: ComplianceWorkflow) => Promise<ComplianceWorkflow>;
  reset: () => void;
}

export const useComplianceWorkflow = (workflowId?: string): UseComplianceWorkflowResult => {
  const [workflow, setWorkflow] = useState<ComplianceWorkflow | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkflow = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/compliance/workflows/${id}`);
      if (!response.ok) {
        throw new Error('Failed to fetch workflow');
      }
      const data: ComplianceWorkflow = await response.json();
      setWorkflow(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const saveWorkflow = useCallback(async (payload: ComplianceWorkflow) => {
    setLoading(true);
    setError(null);

    const targetId = payload.id ?? workflowId;
    const url = targetId ? `/api/v1/compliance/workflows/${targetId}` : '/api/v1/compliance/workflows';
    const method = targetId ? 'PUT' : 'POST';

    const body = {
      name: payload.name,
      description: payload.description ?? '',
      compliance_standard: payload.compliance_standard,
      workflow_definition: payload.workflow_definition,
      status: payload.status ?? 'draft',
      is_template: payload.is_template ?? false
    };

    try {
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        throw new Error('Failed to save workflow');
      }

      const data: ComplianceWorkflow = await response.json();
      setWorkflow(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      throw err instanceof Error ? err : new Error(message);
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  const reset = useCallback(() => {
    setWorkflow(null);
    setError(null);
  }, []);

  useEffect(() => {
    if (!workflowId) return;
    void fetchWorkflow(workflowId);
  }, [workflowId, fetchWorkflow]);

  return {
    workflow,
    loading,
    error,
    fetchWorkflow,
    saveWorkflow,
    reset
  };
};
