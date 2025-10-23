import { useState, useCallback } from 'react';
import { z } from 'zod';
// Validation schemas
const floorPressureSetpointSchema = z.object({
    floor_id: z.string().min(1).max(50),
    pressure_pa: z.number().min(20).max(80),
});
const fanSpecificationSchema = z.object({
    fan_id: z.string().min(1),
    model: z.string().optional(),
    capacity_cfm: z.number().min(0).optional(),
    static_pressure_pa: z.number().min(0).optional(),
    motor_hp: z.number().min(0).optional(),
});
const damperSpecificationSchema = z.object({
    damper_id: z.string().min(1),
    type: z.string().optional(),
    size_mm: z.string().optional(),
    actuator_type: z.string().optional(),
});
const buildingConfigurationSchema = z.object({
    floor_pressure_setpoints: z.record(z.string(), z.number().min(20).max(80)).optional(),
    door_force_limit_newtons: z.number().min(50).max(110).optional(),
    air_velocity_target_ms: z.number().min(1.0).optional(),
    fan_specifications: z.array(fanSpecificationSchema).optional(),
    damper_specifications: z.array(damperSpecificationSchema).optional(),
    relief_air_strategy: z.string().max(50).optional(),
    ce_logic_diagram_path: z.string().optional(),
    manual_override_locations: z.array(z.object({
        location_id: z.string().min(1),
        description: z.string().min(1),
        floor: z.string().optional(),
        coordinates: z.object({
            lat: z.number(),
            lng: z.number(),
        }).optional(),
    })).optional(),
    interfacing_systems: z.array(z.object({
        system_id: z.string().min(1),
        system_type: z.string().min(1),
        interface_type: z.string().min(1),
        description: z.string().optional(),
    })).optional(),
});
const baselinePressureMeasurementSchema = z.object({
    floor_id: z.string().min(1).max(50),
    door_configuration: z.string().min(1).max(50),
    pressure_pa: z.number().min(20).max(80),
    measured_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
});
const baselineVelocityMeasurementSchema = z.object({
    doorway_id: z.string().min(1).max(100),
    velocity_ms: z.number().min(1.0),
    measured_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
});
const baselineDoorForceMeasurementSchema = z.object({
    door_id: z.string().min(1).max(100),
    force_newtons: z.number().max(110),
    measured_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
});
const buildingBaselineSubmitSchema = z.object({
    building_configuration: buildingConfigurationSchema.optional(),
    pressure_measurements: z.array(baselinePressureMeasurementSchema).optional(),
    velocity_measurements: z.array(baselineVelocityMeasurementSchema).optional(),
    door_force_measurements: z.array(baselineDoorForceMeasurementSchema).optional(),
});
export function useBaselineSubmit({ buildingId, onSuccess, onError, autoSave = true, autoSaveKey = 'baseline-draft', }) {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastResponse, setLastResponse] = useState(null);
    const validateData = useCallback((data) => {
        try {
            buildingBaselineSubmitSchema.parse(data);
            return { isValid: true, errors: [] };
        }
        catch (err) {
            if (err instanceof z.ZodError) {
                return {
                    isValid: false,
                    errors: err.errors.map((e) => `${e.path.join('.')}: ${e.message}`),
                };
            }
            return {
                isValid: false,
                errors: ['Unknown validation error'],
            };
        }
    }, []);
    const saveDraft = useCallback((data) => {
        if (autoSave) {
            try {
                localStorage.setItem(autoSaveKey, JSON.stringify(data));
            }
            catch (err) {
                console.warn('Failed to save draft to localStorage:', err);
            }
        }
    }, [autoSave, autoSaveKey]);
    const loadDraft = useCallback(() => {
        if (autoSave) {
            try {
                const draft = localStorage.getItem(autoSaveKey);
                return draft ? JSON.parse(draft) : null;
            }
            catch (err) {
                console.warn('Failed to load draft from localStorage:', err);
                return null;
            }
        }
        return null;
    }, [autoSave, autoSaveKey]);
    const clearDraft = useCallback(() => {
        if (autoSave) {
            try {
                localStorage.removeItem(autoSaveKey);
            }
            catch (err) {
                console.warn('Failed to clear draft from localStorage:', err);
            }
        }
    }, [autoSave, autoSaveKey]);
    const submitBaseline = useCallback(async (data) => {
        setIsLoading(true);
        setError(null);
        try {
            // Validate data before submission
            const validation = validateData(data);
            if (!validation.isValid) {
                throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
            }
            // Get auth token (assuming it's stored in localStorage or similar)
            const token = localStorage.getItem('auth_token');
            if (!token) {
                throw new Error('Authentication token not found');
            }
            const response = await fetch(`/api/v1/buildings/${buildingId}/baseline`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
            }
            const result = await response.json();
            setLastResponse(result);
            // Clear draft on successful submission
            if (result.success) {
                clearDraft();
            }
            onSuccess?.(result);
            return result;
        }
        catch (err) {
            const error = err instanceof Error ? err : new Error('Unknown error occurred');
            setError(error);
            onError?.(error);
            throw error;
        }
        finally {
            setIsLoading(false);
        }
    }, [buildingId, validateData, clearDraft, onSuccess, onError]);
    return {
        submitBaseline,
        isLoading,
        error,
        lastResponse,
        validateData,
        saveDraft,
        loadDraft,
        clearDraft,
    };
}
