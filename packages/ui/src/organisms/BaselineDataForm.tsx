import React, { useState, useEffect, useCallback } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Papa from 'papaparse';
import { useBaselineSubmit, BuildingBaselineSubmit } from '../hooks/useBaselineSubmit';
import { Button } from '../atoms/Button';
import { Input } from '../atoms/Input';
import { Card } from '../molecules/Card';

// Validation schemas
const floorPressureSetpointSchema = z.object({
  floor_id: z.string().min(1, 'Floor ID is required').max(50),
  pressure_pa: z.number().min(20, 'Pressure must be ≥20 Pa (AS 1851-2012)').max(80, 'Pressure must be ≤80 Pa (AS 1851-2012)'),
});

const fanSpecificationSchema = z.object({
  fan_id: z.string().min(1, 'Fan ID is required'),
  model: z.string().optional(),
  capacity_cfm: z.number().min(0).optional(),
  static_pressure_pa: z.number().min(0).optional(),
  motor_hp: z.number().min(0).optional(),
});

const damperSpecificationSchema = z.object({
  damper_id: z.string().min(1, 'Damper ID is required'),
  type: z.string().optional(),
  size_mm: z.string().optional(),
  actuator_type: z.string().optional(),
});

const baselinePressureMeasurementSchema = z.object({
  floor_id: z.string().min(1, 'Floor ID is required').max(50),
  door_configuration: z.string().min(1, 'Door configuration is required').max(50),
  pressure_pa: z.number().min(20, 'Pressure must be ≥20 Pa').max(80, 'Pressure must be ≤80 Pa'),
  measured_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
});

const baselineVelocityMeasurementSchema = z.object({
  doorway_id: z.string().min(1, 'Doorway ID is required').max(100),
  velocity_ms: z.number().min(1.0, 'Velocity must be ≥1.0 m/s (AS 1851-2012)'),
  measured_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
});

const baselineDoorForceMeasurementSchema = z.object({
  door_id: z.string().min(1, 'Door ID is required').max(100),
  force_newtons: z.number().max(110, 'Force must be ≤110 N (AS 1851-2012)'),
  measured_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
});

const formSchema = z.object({
  // Design Criteria
  floor_pressure_setpoints: z.array(floorPressureSetpointSchema).optional(),
  door_force_limit_newtons: z.number().min(50).max(110).optional(),
  air_velocity_target_ms: z.number().min(1.0).optional(),
  fan_specifications: z.array(fanSpecificationSchema).optional(),
  damper_specifications: z.array(damperSpecificationSchema).optional(),
  relief_air_strategy: z.string().max(50).optional(),
  ce_logic_diagram_path: z.string().optional(),
  
  // Commissioning Baselines
  pressure_measurements: z.array(baselinePressureMeasurementSchema).optional(),
  velocity_measurements: z.array(baselineVelocityMeasurementSchema).optional(),
  door_force_measurements: z.array(baselineDoorForceMeasurementSchema).optional(),
});

type FormData = z.infer<typeof formSchema>;

export interface BaselineDataFormProps {
  buildingId: string;
  onSuccess?: (response: any) => void;
  onError?: (error: Error) => void;
  initialData?: Partial<FormData>;
}

export function BaselineDataForm({ 
  buildingId, 
  onSuccess, 
  onError, 
  initialData 
}: BaselineDataFormProps) {
  const [activeTab, setActiveTab] = useState<'design' | 'baselines' | 'review'>('design');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvData, setCsvData] = useState<any[]>([]);
  const [csvError, setCsvError] = useState<string | null>(null);
  const [completeness, setCompleteness] = useState<number>(0);

  const {
    submitBaseline,
    isLoading,
    error,
    lastResponse,
    validateData,
    saveDraft,
    loadDraft,
    clearDraft,
  } = useBaselineSubmit({
    buildingId,
    onSuccess,
    onError,
  });

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
    reset,
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      floor_pressure_setpoints: [],
      fan_specifications: [],
      damper_specifications: [],
      pressure_measurements: [],
      velocity_measurements: [],
      door_force_measurements: [],
      ...initialData,
    },
  });

  const {
    fields: floorFields,
    append: appendFloor,
    remove: removeFloor,
  } = useFieldArray({
    control,
    name: 'floor_pressure_setpoints',
  });

  const {
    fields: fanFields,
    append: appendFan,
    remove: removeFan,
  } = useFieldArray({
    control,
    name: 'fan_specifications',
  });

  const {
    fields: damperFields,
    append: appendDamper,
    remove: removeDamper,
  } = useFieldArray({
    control,
    name: 'damper_specifications',
  });

  const {
    fields: pressureFields,
    append: appendPressure,
    remove: removePressure,
  } = useFieldArray({
    control,
    name: 'pressure_measurements',
  });

  const {
    fields: velocityFields,
    append: appendVelocity,
    remove: removeVelocity,
  } = useFieldArray({
    control,
    name: 'velocity_measurements',
  });

  const {
    fields: forceFields,
    append: appendForce,
    remove: removeForce,
  } = useFieldArray({
    control,
    name: 'door_force_measurements',
  });

  // Load draft on mount
  useEffect(() => {
    const draft = loadDraft();
    if (draft) {
      reset(draft);
    }
  }, [loadDraft, reset]);

  // Auto-save draft on form changes
  useEffect(() => {
    const subscription = watch((data) => {
      saveDraft(data as BuildingBaselineSubmit);
    });
    return () => subscription.unsubscribe();
  }, [watch, saveDraft]);

  // Calculate completeness
  useEffect(() => {
    const formData = watch();
    let total = 0;
    let completed = 0;

    // Design criteria
    if (formData.floor_pressure_setpoints?.length) completed++;
    total++;
    if (formData.door_force_limit_newtons) completed++;
    total++;
    if (formData.air_velocity_target_ms) completed++;
    total++;

    // Baselines
    if (formData.pressure_measurements?.length) completed++;
    total++;
    if (formData.velocity_measurements?.length) completed++;
    total++;
    if (formData.door_force_measurements?.length) completed++;
    total++;

    setCompleteness(total > 0 ? (completed / total) * 100 : 0);
  }, [watch]);

  const handleCsvUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setCsvFile(file);
    setCsvError(null);

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results: any) => {
        if (results.errors.length > 0) {
          setCsvError(`CSV parsing errors: ${results.errors.map((e: any) => e.message).join(', ')}`);
          return;
        }

        setCsvData(results.data);
        
        // Auto-populate form with CSV data
        const pressureData = results.data.filter((row: any) => row.type === 'pressure');
        const velocityData = results.data.filter((row: any) => row.type === 'velocity');
        const forceData = results.data.filter((row: any) => row.type === 'door_force');

        if (pressureData.length > 0) {
          setValue('pressure_measurements', pressureData.map((row: any) => ({
            floor_id: row.floor_id,
            door_configuration: row.door_configuration,
            pressure_pa: parseFloat(row.pressure_pa),
            measured_date: row.measured_date,
          })));
        }

        if (velocityData.length > 0) {
          setValue('velocity_measurements', velocityData.map((row: any) => ({
            doorway_id: row.doorway_id,
            velocity_ms: parseFloat(row.velocity_ms),
            measured_date: row.measured_date,
          })));
        }

        if (forceData.length > 0) {
          setValue('door_force_measurements', forceData.map((row: any) => ({
            door_id: row.door_id,
            force_newtons: parseFloat(row.force_newtons),
            measured_date: row.measured_date,
          })));
        }
      },
      error: (error: any) => {
        setCsvError(`CSV parsing failed: ${error.message}`);
      },
    });
  }, [setValue]);

  const onSubmit = async (data: FormData) => {
    try {
      const submissionData: BuildingBaselineSubmit = {
        building_configuration: {
          floor_pressure_setpoints: data.floor_pressure_setpoints?.reduce((acc, item) => {
            acc[item.floor_id] = item.pressure_pa;
            return acc;
          }, {} as Record<string, number>),
          door_force_limit_newtons: data.door_force_limit_newtons,
          air_velocity_target_ms: data.air_velocity_target_ms,
          fan_specifications: data.fan_specifications,
          damper_specifications: data.damper_specifications,
          relief_air_strategy: data.relief_air_strategy,
          ce_logic_diagram_path: data.ce_logic_diagram_path,
        },
        pressure_measurements: data.pressure_measurements,
        velocity_measurements: data.velocity_measurements,
        door_force_measurements: data.door_force_measurements,
      };

      await submitBaseline(submissionData);
    } catch (err) {
      console.error('Submission failed:', err);
    }
  };

  const renderDesignCriteria = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Design Criteria</h3>
      
      {/* Floor Pressure Setpoints */}
      <Card title="Floor Pressure Setpoints">
        {floorFields.map((field, index) => (
          <div key={field.id} className="grid grid-cols-3 gap-4 mb-4">
            <Input
              {...register(`floor_pressure_setpoints.${index}.floor_id`)}
              placeholder="Floor ID (e.g., floor_1)"
              aria-label={`Floor ID ${index + 1}`}
            />
            <Input
              {...register(`floor_pressure_setpoints.${index}.pressure_pa`, { valueAsNumber: true })}
              type="number"
              placeholder="Pressure (Pa)"
              aria-label={`Pressure ${index + 1}`}
            />
            <Button
              type="button"
              onClick={() => removeFloor(index)}
              variant="secondary"
            >
              Remove
            </Button>
            {errors.floor_pressure_setpoints?.[index] && (
              <div className="col-span-3 text-sm text-red-600">
                {errors.floor_pressure_setpoints[index]?.floor_id?.message || 
                 errors.floor_pressure_setpoints[index]?.pressure_pa?.message}
              </div>
            )}
          </div>
        ))}
        <Button
          type="button"
          onClick={() => appendFloor({ floor_id: '', pressure_pa: 0 })}
          variant="secondary"
        >
          Add Floor
        </Button>
      </Card>

      {/* Equipment Specifications */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Fan Specifications">
          {fanFields.map((field, index) => (
            <div key={field.id} className="space-y-2 mb-4">
              <Input
                {...register(`fan_specifications.${index}.fan_id`)}
                placeholder="Fan ID"
                aria-label={`Fan ID ${index + 1}`}
              />
              <Input
                {...register(`fan_specifications.${index}.model`)}
                placeholder="Model"
                aria-label={`Fan Model ${index + 1}`}
              />
              <Button
                type="button"
                onClick={() => removeFan(index)}
                variant="secondary"
              >
                Remove Fan
              </Button>
            </div>
          ))}
          <Button
            type="button"
            onClick={() => appendFan({ fan_id: '', model: '' })}
            variant="secondary"
          >
            Add Fan
          </Button>
        </Card>

        <Card title="Damper Specifications">
          {damperFields.map((field, index) => (
            <div key={field.id} className="space-y-2 mb-4">
              <Input
                {...register(`damper_specifications.${index}.damper_id`)}
                placeholder="Damper ID"
                aria-label={`Damper ID ${index + 1}`}
              />
              <Input
                {...register(`damper_specifications.${index}.type`)}
                placeholder="Type"
                aria-label={`Damper Type ${index + 1}`}
              />
              <Button
                type="button"
                onClick={() => removeDamper(index)}
                variant="secondary"
              >
                Remove Damper
              </Button>
            </div>
          ))}
          <Button
            type="button"
            onClick={() => appendDamper({ damper_id: '', type: '' })}
            variant="secondary"
          >
            Add Damper
          </Button>
        </Card>
      </div>

      {/* Additional Configuration */}
      <Card title="Additional Configuration">
        <div className="space-y-4">
          <Input
            {...register('door_force_limit_newtons', { valueAsNumber: true })}
            type="number"
            placeholder="Door Force Limit (N)"
            aria-label="Door Force Limit"
          />
          <Input
            {...register('air_velocity_target_ms', { valueAsNumber: true })}
            type="number"
            step="0.1"
            placeholder="Air Velocity Target (m/s)"
            aria-label="Air Velocity Target"
          />
          <Input
            {...register('relief_air_strategy')}
            placeholder="Relief Air Strategy"
            aria-label="Relief Air Strategy"
          />
          <Input
            {...register('ce_logic_diagram_path')}
            placeholder="C&E Logic Diagram Path"
            aria-label="C&E Logic Diagram Path"
          />
        </div>
      </Card>
    </div>
  );

  const renderCommissioningBaselines = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Commissioning Baselines</h3>
      
      {/* CSV Upload */}
      <Card title="Bulk Upload (CSV)">
        <div className="space-y-4">
          <input
            type="file"
            accept=".csv"
            onChange={handleCsvUpload}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            aria-label="Upload CSV file"
          />
          {csvError && (
            <div className="text-sm text-red-600" role="alert">
              {csvError}
            </div>
          )}
          {csvData.length > 0 && (
            <div className="text-sm text-green-600">
              Successfully loaded {csvData.length} records from CSV
            </div>
          )}
        </div>
      </Card>

      {/* Manual Entry Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pressure Measurements */}
        <Card title="Pressure Measurements">
          {pressureFields.map((field, index) => (
            <div key={field.id} className="space-y-2 mb-4">
              <Input
                {...register(`pressure_measurements.${index}.floor_id`)}
                placeholder="Floor ID"
                aria-label={`Pressure Floor ID ${index + 1}`}
              />
              <Input
                {...register(`pressure_measurements.${index}.door_configuration`)}
                placeholder="Door Config"
                aria-label={`Pressure Door Config ${index + 1}`}
              />
              <Input
                {...register(`pressure_measurements.${index}.pressure_pa`, { valueAsNumber: true })}
                type="number"
                placeholder="Pressure (Pa)"
                aria-label={`Pressure Value ${index + 1}`}
              />
              <Input
                {...register(`pressure_measurements.${index}.measured_date`)}
                type="date"
                aria-label={`Pressure Date ${index + 1}`}
              />
              <Button
                type="button"
                onClick={() => removePressure(index)}
                variant="secondary"
              >
                Remove
              </Button>
            </div>
          ))}
          <Button
            type="button"
            onClick={() => appendPressure({ 
              floor_id: '', 
              door_configuration: '', 
              pressure_pa: 0, 
              measured_date: new Date().toISOString().split('T')[0] 
            })}
            variant="secondary"
          >
            Add Pressure
          </Button>
        </Card>

        {/* Velocity Measurements */}
        <Card title="Velocity Measurements">
          {velocityFields.map((field, index) => (
            <div key={field.id} className="space-y-2 mb-4">
              <Input
                {...register(`velocity_measurements.${index}.doorway_id`)}
                placeholder="Doorway ID"
                aria-label={`Velocity Doorway ID ${index + 1}`}
              />
              <Input
                {...register(`velocity_measurements.${index}.velocity_ms`, { valueAsNumber: true })}
                type="number"
                step="0.1"
                placeholder="Velocity (m/s)"
                aria-label={`Velocity Value ${index + 1}`}
              />
              <Input
                {...register(`velocity_measurements.${index}.measured_date`)}
                type="date"
                aria-label={`Velocity Date ${index + 1}`}
              />
              <Button
                type="button"
                onClick={() => removeVelocity(index)}
                variant="secondary"
              >
                Remove
              </Button>
            </div>
          ))}
          <Button
            type="button"
            onClick={() => appendVelocity({ 
              doorway_id: '', 
              velocity_ms: 0, 
              measured_date: new Date().toISOString().split('T')[0] 
            })}
            variant="secondary"
          >
            Add Velocity
          </Button>
        </Card>

        {/* Door Force Measurements */}
        <Card title="Door Force Measurements">
          {forceFields.map((field, index) => (
            <div key={field.id} className="space-y-2 mb-4">
              <Input
                {...register(`door_force_measurements.${index}.door_id`)}
                placeholder="Door ID"
                aria-label={`Force Door ID ${index + 1}`}
              />
              <Input
                {...register(`door_force_measurements.${index}.force_newtons`, { valueAsNumber: true })}
                type="number"
                placeholder="Force (N)"
                aria-label={`Force Value ${index + 1}`}
              />
              <Input
                {...register(`door_force_measurements.${index}.measured_date`)}
                type="date"
                aria-label={`Force Date ${index + 1}`}
              />
              <Button
                type="button"
                onClick={() => removeForce(index)}
                variant="secondary"
              >
                Remove
              </Button>
            </div>
          ))}
          <Button
            type="button"
            onClick={() => appendForce({ 
              door_id: '', 
              force_newtons: 0, 
              measured_date: new Date().toISOString().split('T')[0] 
            })}
            variant="secondary"
          >
            Add Force
          </Button>
        </Card>
      </div>
    </div>
  );

  const renderReview = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Review & Submit</h3>
      
      {/* Completeness Indicator */}
      <Card title="Baseline Completeness">
        <div className="space-y-4">
          <div className="flex items-center space-x-4">
            <div className="flex-1 bg-gray-200 rounded-full h-4">
              <div 
                className="bg-blue-600 h-4 rounded-full transition-all duration-300"
                style={{ width: `${completeness}%` }}
                role="progressbar"
                aria-valuenow={completeness}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Baseline completeness: ${completeness.toFixed(1)}%`}
              />
            </div>
            <span className="text-sm font-medium">{completeness.toFixed(1)}%</span>
          </div>
          <p className="text-sm text-gray-600">
            {completeness === 100 
              ? "Baseline data is complete and ready for submission"
              : `${100 - completeness}% of required data is missing`
            }
          </p>
        </div>
      </Card>

      {/* Error Display */}
      {error && (
        <Card title="Submission Error">
          <div className="text-red-800" role="alert">
            <p className="text-sm">{error.message}</p>
          </div>
        </Card>
      )}

      {/* Success Display */}
      {lastResponse?.success && (
        <Card title="Submission Successful">
          <div className="text-green-800">
            <p className="text-sm">{lastResponse.message}</p>
            <p className="text-sm mt-1">
              Created {lastResponse.items_created} items, updated {lastResponse.items_updated} items
            </p>
          </div>
        </Card>
      )}

      {/* Submit Button */}
      <div className="flex justify-end space-x-4">
        <Button
          type="button"
          onClick={() => setActiveTab('baselines')}
          variant="secondary"
        >
          Back to Baselines
        </Button>
        <Button
          type="submit"
          disabled={isLoading || !isValid}
          aria-label={isLoading ? "Submitting baseline data..." : "Submit baseline data"}
        >
          {isLoading ? "Submitting..." : "Submit Baseline Data"}
        </Button>
      </div>
    </div>
  );

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-2">Stair Pressurization Baseline Data</h2>
        <p className="text-gray-600">
          Enter baseline data for AS 1851-2012 stair pressurization compliance testing.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 mb-8">
        {[
          { id: 'design', label: 'Design Criteria' },
          { id: 'baselines', label: 'Commissioning Baselines' },
          { id: 'review', label: 'Review & Submit' },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
            aria-current={activeTab === tab.id ? 'page' : undefined}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === 'design' && renderDesignCriteria()}
        {activeTab === 'baselines' && renderCommissioningBaselines()}
        {activeTab === 'review' && renderReview()}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-8">
        <Button
          type="button"
          onClick={() => {
            if (activeTab === 'baselines') setActiveTab('design');
            else if (activeTab === 'review') setActiveTab('baselines');
          }}
          variant="secondary"
          disabled={activeTab === 'design'}
        >
          Previous
        </Button>
        <Button
          type="button"
          onClick={() => {
            if (activeTab === 'design') setActiveTab('baselines');
            else if (activeTab === 'baselines') setActiveTab('review');
          }}
          disabled={activeTab === 'review'}
        >
          Next
        </Button>
      </div>
    </form>
  );
}