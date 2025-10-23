import type { Meta, StoryObj } from '@storybook/react';
import { BaselineDataForm } from '../organisms/BaselineDataForm';

const meta: Meta<typeof BaselineDataForm> = {
  title: 'Organisms/BaselineDataForm',
  component: BaselineDataForm,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'Multi-step wizard for entering stair pressurization baseline data with CSV upload and validation.',
      },
    },
  },
  argTypes: {
    buildingId: {
      control: 'text',
      description: 'UUID of the building for baseline data submission',
    },
    onSuccess: {
      action: 'success',
      description: 'Callback fired when baseline data is successfully submitted',
    },
    onError: {
      action: 'error',
      description: 'Callback fired when baseline data submission fails',
    },
    initialData: {
      control: 'object',
      description: 'Initial form data to populate the form',
    },
  },
};

export default meta;
type Story = StoryObj<typeof BaselineDataForm>;

// Mock data for stories
const mockInitialData = {
  floor_pressure_setpoints: [
    { floor_id: 'floor_1', pressure_pa: 45 },
    { floor_id: 'floor_2', pressure_pa: 50 },
    { floor_id: 'floor_3', pressure_pa: 48 },
  ],
  door_force_limit_newtons: 110,
  air_velocity_target_ms: 1.2,
  fan_specifications: [
    { fan_id: 'fan_1', model: 'ABC-123', capacity_cfm: 5000 },
    { fan_id: 'fan_2', model: 'XYZ-456', capacity_cfm: 3000 },
  ],
  damper_specifications: [
    { damper_id: 'damper_1', type: 'fire', size_mm: '600x400' },
    { damper_id: 'damper_2', type: 'smoke', size_mm: '300x300' },
  ],
  relief_air_strategy: 'Automatic relief dampers',
  ce_logic_diagram_path: '/diagrams/ce-logic-v1.pdf',
  pressure_measurements: [
    {
      floor_id: 'floor_1',
      door_configuration: 'all_doors_open',
      pressure_pa: 42,
      measured_date: '2024-01-15',
    },
    {
      floor_id: 'floor_1',
      door_configuration: 'all_doors_closed',
      pressure_pa: 48,
      measured_date: '2024-01-15',
    },
  ],
  velocity_measurements: [
    {
      doorway_id: 'stair_door_1',
      velocity_ms: 1.1,
      measured_date: '2024-01-15',
    },
    {
      doorway_id: 'main_entrance',
      velocity_ms: 1.3,
      measured_date: '2024-01-15',
    },
  ],
  door_force_measurements: [
    {
      door_id: 'stair_door_1',
      force_newtons: 95,
      measured_date: '2024-01-15',
    },
    {
      door_id: 'fire_door_2',
      force_newtons: 88,
      measured_date: '2024-01-15',
    },
  ],
};

const invalidData = {
  floor_pressure_setpoints: [
    { floor_id: 'floor_1', pressure_pa: 15 }, // Invalid: below 20 Pa
    { floor_id: 'floor_2', pressure_pa: 85 }, // Invalid: above 80 Pa
  ],
  door_force_limit_newtons: 120, // Invalid: above 110 N
  air_velocity_target_ms: 0.8, // Invalid: below 1.0 m/s
  pressure_measurements: [
    {
      floor_id: 'floor_1',
      door_configuration: 'all_doors_open',
      pressure_pa: 10, // Invalid: below 20 Pa
      measured_date: '2024-01-15',
    },
  ],
  velocity_measurements: [
    {
      doorway_id: 'stair_door_1',
      velocity_ms: 0.5, // Invalid: below 1.0 m/s
      measured_date: '2024-01-15',
    },
  ],
  door_force_measurements: [
    {
      door_id: 'stair_door_1',
      force_newtons: 150, // Invalid: above 110 N
      measured_date: '2024-01-15',
    },
  ],
};

export const Default: Story = {
  args: {
    buildingId: '123e4567-e89b-12d3-a456-426614174000',
  },
};

export const WithInitialData: Story = {
  args: {
    buildingId: '123e4567-e89b-12d3-a456-426614174000',
    initialData: mockInitialData,
  },
  parameters: {
    docs: {
      description: {
        story: 'Form pre-populated with sample baseline data showing a complete configuration.',
      },
    },
  },
};

export const WithValidationErrors: Story = {
  args: {
    buildingId: '123e4567-e89b-12d3-a456-426614174000',
    initialData: invalidData,
  },
  parameters: {
    docs: {
      description: {
        story: 'Form with invalid data showing AS 1851-2012 validation errors. Values outside acceptable ranges will be highlighted.',
      },
    },
  },
};

export const EmptyForm: Story = {
  args: {
    buildingId: '123e4567-e89b-12d3-a456-426614174000',
    initialData: {
      floor_pressure_setpoints: [],
      fan_specifications: [],
      damper_specifications: [],
      pressure_measurements: [],
      velocity_measurements: [],
      door_force_measurements: [],
    },
  },
  parameters: {
    docs: {
      description: {
        story: 'Empty form showing the initial state with no data entered.',
      },
    },
  },
};

export const CSVUploadExample: Story = {
  args: {
    buildingId: '123e4567-e89b-12d3-a456-426614174000',
  },
  parameters: {
    docs: {
      description: {
        story: 'Form showing CSV upload functionality. Upload a CSV file with columns: type, floor_id, door_configuration, pressure_pa, doorway_id, velocity_ms, door_id, force_newtons, measured_date.',
      },
    },
  },
};

// Mock CSV content for testing
const csvContent = `type,floor_id,door_configuration,pressure_pa,doorway_id,velocity_ms,door_id,force_newtons,measured_date
pressure,floor_1,all_doors_open,42,,,2024-01-15
pressure,floor_1,all_doors_closed,48,,,2024-01-15
pressure,floor_2,all_doors_open,45,,,2024-01-15
pressure,floor_2,all_doors_closed,52,,,2024-01-15
velocity,,,stair_door_1,1.1,,2024-01-15
velocity,,,main_entrance,1.3,,2024-01-15
door_force,,,,stair_door_1,95,2024-01-15
door_force,,,,fire_door_2,88,2024-01-15`;

export const CSVUploadInstructions: Story = {
  args: {
    buildingId: '123e4567-e89b-12d3-a456-426614174000',
  },
  render: (args) => (
    <div className="p-6">
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-2">CSV Upload Instructions</h3>
        <p className="text-blue-800 text-sm mb-3">
          To upload baseline measurements via CSV, create a file with the following columns:
        </p>
        <ul className="text-blue-800 text-sm list-disc list-inside space-y-1 mb-3">
          <li><strong>type</strong>: "pressure", "velocity", or "door_force"</li>
          <li><strong>floor_id</strong>: Floor identifier (for pressure measurements)</li>
          <li><strong>door_configuration</strong>: "all_doors_open" or "all_doors_closed" (for pressure measurements)</li>
          <li><strong>pressure_pa</strong>: Pressure in Pascals (20-80 Pa range)</li>
          <li><strong>doorway_id</strong>: Doorway identifier (for velocity measurements)</li>
          <li><strong>velocity_ms</strong>: Velocity in m/s (≥1.0 m/s)</li>
          <li><strong>door_id</strong>: Door identifier (for force measurements)</li>
          <li><strong>force_newtons</strong>: Force in Newtons (≤110 N)</li>
          <li><strong>measured_date</strong>: Date in YYYY-MM-DD format</li>
        </ul>
        <details className="text-blue-800 text-sm">
          <summary className="cursor-pointer font-medium">Example CSV Content</summary>
          <pre className="mt-2 p-2 bg-white border rounded text-xs overflow-x-auto">
            {csvContent}
          </pre>
        </details>
      </div>
      <BaselineDataForm {...args} />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Form with CSV upload instructions and example content.',
      },
    },
  },
};

export const AccessibilityDemo: Story = {
  args: {
    buildingId: '123e4567-e89b-12d3-a456-426614174000',
    initialData: mockInitialData,
  },
  parameters: {
    docs: {
      description: {
        story: 'Form demonstrating accessibility features including ARIA labels, keyboard navigation, and screen reader support.',
      },
    },
  },
  play: async ({ canvasElement }) => {
    // This would contain accessibility testing interactions
    // For now, it's a placeholder for future accessibility testing
  },
};
