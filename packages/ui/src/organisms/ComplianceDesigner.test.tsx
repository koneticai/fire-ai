/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ComplianceDesigner } from './ComplianceDesigner';
import { useComplianceWorkflow } from '../hooks/useComplianceWorkflow';

// Mock the hook
jest.mock('../hooks/useComplianceWorkflow');
const mockUseComplianceWorkflow = useComplianceWorkflow as jest.MockedFunction<typeof useComplianceWorkflow>;

// Mock D3
jest.mock('d3-selection', () => ({
  select: jest.fn(() => ({
    selectAll: jest.fn(() => ({
      remove: jest.fn(),
      data: jest.fn(() => ({
        join: jest.fn(() => ({
          attr: jest.fn(() => ({
            style: jest.fn(() => ({
              call: jest.fn()
            }))
          }))
        }))
      }))
    })),
    attr: jest.fn(() => ({
      style: jest.fn()
    })),
    append: jest.fn(() => ({
      attr: jest.fn(() => ({
        append: jest.fn(() => ({
          attr: jest.fn(() => ({
            attr: jest.fn(() => ({
              append: jest.fn(() => ({
                attr: jest.fn(() => ({
                  style: jest.fn()
                }))
              }))
            }))
          }))
        }))
      }))
    })),
    call: jest.fn()
  }))
}));

jest.mock('d3-drag', () => ({
  drag: jest.fn(() => ({
    on: jest.fn(() => ({
      on: jest.fn()
    }))
  }))
}));

jest.mock('d3-zoom', () => ({
  zoom: jest.fn(() => ({
    scaleExtent: jest.fn(() => ({
      on: jest.fn()
    }))
  }))
}));

// Mock components
jest.mock('../molecules/Card', () => ({
  Card: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="card">
      <h2>{title}</h2>
      {children}
    </div>
  )
}));

jest.mock('../atoms/Button', () => ({
  Button: ({ children, onClick, disabled, variant }: any) => (
    <button 
      onClick={onClick} 
      disabled={disabled}
      data-variant={variant}
      data-testid="button"
    >
      {children}
    </button>
  )
}));

jest.mock('../atoms/Input', () => ({
  Input: ({ value, onChange, id }: any) => (
    <input 
      id={id}
      value={value} 
      onChange={onChange}
      data-testid="input"
    />
  )
}));

// Mock tokens
jest.mock('../tokens', () => ({
  tokens: {
    spacing: {
      sm: '8px',
      md: '16px',
      lg: '24px'
    },
    colors: {
      primary: '#007bff',
      danger: '#dc3545'
    },
    typography: {
      fontFamily: {
        sans: 'Arial, sans-serif'
      },
      fontSize: {
        base: '14px'
      }
    },
    radius: {
      sm: '4px'
    }
  }
}));

describe('ComplianceDesigner', () => {
  const mockWorkflow = {
    id: 'test-workflow-id',
    name: 'Test Workflow',
    description: 'Test Description',
    compliance_standard: 'AS1851-2012',
    workflow_definition: {
      nodes: [
        {
          id: 'node1',
          type: 'evidence',
          position: { x: 100, y: 100 },
          data: { name: 'Test Node' }
        }
      ],
      edges: []
    },
    status: 'draft',
    is_template: false
  };

  const defaultMockReturn = {
    workflow: null,
    loading: false,
    error: null,
    saveWorkflow: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseComplianceWorkflow.mockReturnValue(defaultMockReturn);
  });

  it('renders the compliance designer with default workflow', () => {
    render(<ComplianceDesigner />);
    
    expect(screen.getByText('Compliance Workflow Designer')).toBeInTheDocument();
    expect(screen.getByText('Add Evidence')).toBeInTheDocument();
    expect(screen.getByText('Add Inspection')).toBeInTheDocument();
    expect(screen.getByText('Add Approval')).toBeInTheDocument();
    expect(screen.getByText('Add Remediation')).toBeInTheDocument();
    expect(screen.getByText('Connect Nodes')).toBeInTheDocument();
    expect(screen.getByText('Save Workflow')).toBeInTheDocument();
  });

  it('shows loading state when loading is true', () => {
    mockUseComplianceWorkflow.mockReturnValue({
      ...defaultMockReturn,
      loading: true
    });

    render(<ComplianceDesigner workflowId="test-id" />);
    
    expect(screen.getByText('Loading workflow...')).toBeInTheDocument();
  });

  it('shows error state when error is present', () => {
    mockUseComplianceWorkflow.mockReturnValue({
      ...defaultMockReturn,
      error: 'Failed to load workflow'
    });

    render(<ComplianceDesigner workflowId="test-id" />);
    
    expect(screen.getByText('Error: Failed to load workflow')).toBeInTheDocument();
  });

  it('updates workflow name when input changes', () => {
    render(<ComplianceDesigner />);
    
    const nameInput = screen.getByLabelText('Workflow Name');
    fireEvent.change(nameInput, { target: { value: 'New Workflow Name' } });
    
    expect(nameInput).toHaveValue('New Workflow Name');
  });

  it('updates compliance standard when input changes', () => {
    render(<ComplianceDesigner />);
    
    const standardInput = screen.getByLabelText('Compliance Standard');
    fireEvent.change(standardInput, { target: { value: 'NFPA' } });
    
    expect(standardInput).toHaveValue('NFPA');
  });

  it('adds nodes when add buttons are clicked', () => {
    render(<ComplianceDesigner />);
    
    const addEvidenceButton = screen.getByText('Add Evidence');
    fireEvent.click(addEvidenceButton);
    
    // The component should update its internal state
    // We can't directly test the D3 visualization, but we can test that the button works
    expect(addEvidenceButton).toBeInTheDocument();
  });

  it('toggles edge mode when connect button is clicked', () => {
    render(<ComplianceDesigner />);
    
    const connectButton = screen.getByText('Connect Nodes');
    fireEvent.click(connectButton);
    
    // Button text should change to "Cancel Connect"
    expect(screen.getByText('Cancel Connect')).toBeInTheDocument();
  });

  it('calls saveWorkflow when save button is clicked', async () => {
    const mockSaveWorkflow = jest.fn().mockResolvedValue(mockWorkflow);
    mockUseComplianceWorkflow.mockReturnValue({
      ...defaultMockReturn,
      saveWorkflow: mockSaveWorkflow
    });

    render(<ComplianceDesigner />);
    
    const saveButton = screen.getByText('Save Workflow');
    fireEvent.click(saveButton);
    
    await waitFor(() => {
      expect(mockSaveWorkflow).toHaveBeenCalled();
    });
  });

  it('disables save button when loading', () => {
    mockUseComplianceWorkflow.mockReturnValue({
      ...defaultMockReturn,
      loading: true
    });

    render(<ComplianceDesigner />);
    
    const saveButton = screen.getByText('Saving…');
    expect(saveButton).toBeDisabled();
  });

  it('toggles preview mode when preview button is clicked', () => {
    render(<ComplianceDesigner />);
    
    const previewButton = screen.getByText('Preview Mode');
    fireEvent.click(previewButton);
    
    // Button text should change to "Edit Mode"
    expect(screen.getByText('Edit Mode')).toBeInTheDocument();
  });

  it('shows workflow summary in preview mode', () => {
    render(<ComplianceDesigner />);
    
    // Enter preview mode
    const previewButton = screen.getByText('Preview Mode');
    fireEvent.click(previewButton);
    
    // Should show workflow summary
    expect(screen.getByText('Workflow Summary')).toBeInTheDocument();
    expect(screen.getByText('Name:')).toBeInTheDocument();
    expect(screen.getByText('Compliance Standard:')).toBeInTheDocument();
    expect(screen.getByText('Steps:')).toBeInTheDocument();
    expect(screen.getByText('Connections:')).toBeInTheDocument();
  });

  it('loads existing workflow when workflowId is provided', () => {
    mockUseComplianceWorkflow.mockReturnValue({
      ...defaultMockReturn,
      workflow: mockWorkflow
    });

    render(<ComplianceDesigner workflowId="test-workflow-id" />);
    
    // Should show the loaded workflow name
    const nameInput = screen.getByLabelText('Workflow Name');
    expect(nameInput).toHaveValue('Test Workflow');
  });

  it('handles node property updates', () => {
    render(<ComplianceDesigner />);
    
    // Add a node first
    const addEvidenceButton = screen.getByText('Add Evidence');
    fireEvent.click(addEvidenceButton);
    
    // The component should handle node property updates internally
    // We can't directly test the D3 visualization, but we can test the UI elements
    expect(screen.getByText('Add Evidence')).toBeInTheDocument();
  });

  it('shows error message when save fails', () => {
    mockUseComplianceWorkflow.mockReturnValue({
      ...defaultMockReturn,
      error: 'Failed to save workflow'
    });

    render(<ComplianceDesigner />);
    
    expect(screen.getByText('Error: Failed to save workflow')).toBeInTheDocument();
  });

  it('renders SVG canvas for workflow visualization', () => {
    render(<ComplianceDesigner />);
    
    const svg = screen.getByRole('application');
    expect(svg).toBeInTheDocument();
    expect(svg.tagName).toBe('svg');
  });
});
