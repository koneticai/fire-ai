AS 1851-2012 Stair Pressurization: Baseline-Driven Multi-Instance Test Planning Specification
Document Version: 2.0Audit Date: October 20, 2025Scope: 40,000-ft Architecture for Test Instance GenerationCompliance Standard: AS 1851-2012 Section 13 (Stair Pressurization Systems)

1. Reasoning Summary (150 words)
Current FireMode demo treats stair pressurization tests as monolithic single-instance operations (e.g., "pressure test" per building), violating AS 1851-2012's requirement for floor-by-floor, door-configuration-specific, orientation-sensitive measurements across multiple stair shafts. A typical 15-floor building with 2 stair shafts requires 60+ pressure differential instances annually (2 stairs × 15 floors × 2 door configs), 30+ doorway velocity instances, 30+ door force instances, 10-20 C&E scenarios (spot vs. full coverage), and 4-8 interface test instances—totaling 150-200+ discrete test instances per building per year.
The proposed architecture introduces an Archetype → Instances expansion model: each test archetype (pressure differential, air velocity, door force, C&E logic, interface tests) is parameterized by baseline cardinalities (stair count, floor count, door/doorway inventory, zones, orientations) and frequencies (monthly, six-monthly, annual), generating the full test matrix. Each instance includes visual/audible/descriptive UX prompts, instrument calibration gates, and evidence capture requirements. This prevents single-instance shortcuts and ensures AS 1851-2012 compliance at scale.

2. Customer Journey & Dataflow Overview
Roles & Workflow
1. Service Manager (Baseline Configuration)
Input: Building design documents, commissioning reports, stair inventory (2 shafts: Stair-A North-facing, Stair-B South-facing), floor count (15 floors), door/doorway registry (30 doors, 30 doorways), fan/damper specs (4 fans, 12 dampers), zone definitions (Zones 1-5 covering floors 1-15)
Action: Configure baseline via web portal → System generates 180+ annual test instances from archetypes
Output: Test plan with instance-level detail (e.g., "Pressure Test Instance #47: Stair-A, Floor 8, All Doors Closed, Annual")
2. Technician (Test Execution)
Input: Download offline bundle with 180+ test instances organized by frequency and stair/floor hierarchy
Action: Execute tests using instance-specific UX prompts:
Visual: Floor plan highlights "You are here: Stair-A, Floor 8, North doorway"
Audible: "Begin pressure measurement now" (beep), countdown timer, "Measurement complete" (success tone)
Descriptive: "1. Close all stair doors on floors 7-9. 2. Position manometer at Floor 8 landing, 1.5m height. 3. Wait 30s for stabilization. 4. Record pressure reading."
Safety: "Ensure doors can be manually opened. Confirm no occupants in stairwell."
Instrument Gate: "Verify Manometer SN-12345 calibration valid until 2025-12-01"
Evidence: "Capture photo of manometer display + floor number sign"
Output: 180+ instance results synced to backend with evidence chain-of-custody
3. Compliance Validator (Backend)
Input: Instance-level results with stair/floor/door/orientation context
Process: Validate each instance against baseline + AS 1851 rules → Flag deviations by instance
Output: Fault per non-compliant instance (e.g., "Fault #F-047: Stair-A Floor 8 pressure 18.2 Pa < min 20 Pa")
4. Engineer (Report Review)
Input: Report with instance-level compliance matrix (180 rows: Instance ID, Location, Config, Result, Pass/Fail)
Action: Review deviations, approve corrective actions, sign compliance statement
Output: Finalized report with instance-level audit trail
Dataflow: Baseline → Instance Expansion → Execution → Aggregation


┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: Baseline Configuration (One-Time per Building)        │
├─────────────────────────────────────────────────────────────────┤
│ Input: Service Manager configures via web portal               │
│                                                                 │
│ Baseline Entities:                                             │
│   - Stairs: 2 (Stair-A: North-facing, Stair-B: South-facing)  │
│   - Floors: 15 (Ground, Levels 1-14)                           │
│   - Doors: 30 (15 per stair)                                   │
│   - Doorways: 30 (15 per stair)                                │
│   - Fans: 4 (2 per stair)                                      │
│   - Dampers: 12 (6 per stair)                                  │
│   - Zones: 5 (Z1: Ground-L3, Z2: L4-L6, Z3: L7-L9, Z4: L10-L12,│
│              Z5: L13-L14)                                       │
│   - Orientations: N/S (stair-specific)                         │
│   - Door Configurations: {all_closed, evac_doors_open}         │
│                                                                 │
│ Process: Archetype Expansion Engine                            │
│   ├─> Pressure Differential Archetype                          │
│   │    Instances = 2 stairs × 15 floors × 2 door_configs × 1   │
│   │    Result: 60 annual pressure instances                    │
│   │                                                             │
│   ├─> Air Velocity Archetype                                   │
│   │    Instances = 2 stairs × 15 doorways × 1 (annual only)    │
│   │    Result: 30 annual velocity instances                    │
│   │                                                             │
│   ├─> Door Force Archetype                                     │
│   │    Instances = 2 stairs × 15 doors × 1 (annual only)       │
│   │    Result: 30 annual door force instances                  │
│   │                                                             │
│   ├─> C&E Logic Archetype                                      │
│   │    Six-Monthly: 2 stairs × 2 zones (spot check) = 4        │
│   │    Annual: 2 stairs × 5 zones (full coverage) = 10         │
│   │    Result: 4 six-monthly + 10 annual C&E instances         │
│   │                                                             │
│   └─> Interface Tests Archetype                                │
│        Tests: {manual_override, alarm, shutdown, sprinkler}    │
│        Locations: {fire_panel, bms, local_switch} × 2 stairs   │
│        Result: 4 test types × 3 locations × 2 stairs = 24      │
│                (6 six-monthly, 18 annual)                       │
│                                                                 │
│ Output: Test Plan Matrix                                        │
│   - Annual: 60 pressure + 30 velocity + 30 door force +        │
│             10 C&E + 18 interface = 148 instances               │
│   - Six-Monthly: 4 C&E + 6 interface = 10 instances            │
│   - Monthly: Visual checks only (non-measured, ~30 checks)     │
│   - TOTAL MEASURED INSTANCES PER YEAR: 158                     │
│                                                                 │
│ Storage: test_instance_templates table (pre-generated)         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: Test Session Creation (Per Frequency Cycle)           │
├─────────────────────────────────────────────────────────────────┤
│ Input: POST /v1/tests/sessions                                 │
│        {building_id, test_frequency: "annual"}                 │
│                                                                 │
│ Process: Instance Cloning                                      │
│   - Query test_instance_templates WHERE building_id AND        │
│     frequency IN ("monthly", "annual")  -- cumulative          │
│   - Clone 148 annual instances to test_instances table         │
│   - Each instance: {template_id, session_id, stair_id,         │
│                     floor_id, door_config, doorway_id?,        │
│                     orientation?, status: "pending"}           │
│                                                                 │
│ Output: 148 discrete test instances linked to session          │
│   - Organized hierarchically: Stair → Floor → Test Type        │
│   - Mobile bundle includes instance-level UX prompts           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: Test Execution (Mobile App, Instance-by-Instance)     │
├─────────────────────────────────────────────────────────────────┤
│ Input: Offline bundle with 148 instances                       │
│                                                                 │
│ UX Navigation:                                                  │
│   Session View → Stair-A (74 instances) → Floor 8 (8 instances)│
│   → Pressure Test #47: All Doors Closed                        │
│                                                                 │
│ Instance Execution UI:                                          │
│   ┌───────────────────────────────────────────────┐            │
│   │ VISUAL:                                       │            │
│   │ [Floor plan: Stair-A highlighted, Floor 8    │            │
│   │  landing marked with red pin]                │            │
│   │ "You are here" indicator                     │            │
│   ├───────────────────────────────────────────────┤            │
│   │ AUDIBLE:                                      │            │
│   │ 🔊 "Begin pressure test - All doors closed"  │            │
│   │ [Countdown: 30s stabilization timer]         │            │
│   ├───────────────────────────────────────────────┤            │
│   │ DESCRIPTIVE:                                  │            │
│   │ Step 1: Close all doors on Floors 7-9        │            │
│   │ Step 2: Position manometer at landing,       │            │
│   │         1.5m height, facing stair shaft      │            │
│   │ Step 3: Wait for pressure stabilization      │            │
│   │ Step 4: Record reading in Pa                 │            │
│   ├───────────────────────────────────────────────┤            │
│   │ SAFETY:                                       │            │
│   │ ⚠️ Ensure doors can be manually opened       │            │
│   │ ⚠️ Confirm no occupants in stairwell         │            │
│   ├───────────────────────────────────────────────┤            │
│   │ INSTRUMENT GATE:                              │            │
│   │ Manometer: SN-12345                           │            │
│   │ Calibration valid until: 2025-12-01          │            │
│   │ [✓] Verified     [X] Expired → Block Test    │            │
│   ├───────────────────────────────────────────────┤            │
│   │ MEASUREMENT INPUT:                            │            │
│   │ Pressure: [____] Pa                           │            │
│   │ Design Setpoint: 45 Pa (from baseline)       │            │
│   │ Thresholds: 20-80 Pa                          │            │
│   │ [Auto-validate on input]                     │            │
│   ├───────────────────────────────────────────────┤            │
│   │ EVIDENCE:                                     │            │
│   │ [ Capture Photo: Manometer display + floor # ]│            │
│   │ [ Capture Photo: Door configuration proof ]  │            │
│   │ SHA-256: [computed on capture]               │            │
│   │ Device attestation: [iOS DeviceCheck token]  │            │
│   └───────────────────────────────────────────────┘            │
│                                                                 │
│ Data Recorded:                                                  │
│   {                                                             │
│     instance_id: "I-047",                                       │
│     template_id: "TPL-PRESSURE-001",                            │
│     stair_id: "Stair-A",                                        │
│     floor_id: "Level-8",                                        │
│     door_configuration: "all_closed",                           │
│     measured_value_numeric: 43.2,                               │
│     design_setpoint: 45.0,                                      │
│     min_threshold: 20.0,                                        │
│     max_threshold: 80.0,                                        │
│     instrument_id: "MANOMETER-SN12345",                         │
│     calibration_cert_id: "CERT-2024-789",                       │
│     orientation: "North",                                       │
│     environmental_conditions: {temp_c: 22, wind_ms: 3.5},       │
│     is_compliant: true,  // 20 ≤ 43.2 ≤ 80                     │
│     deviation_from_baseline_pct: -4.0,  // (43.2-45)/45        │
│     evidence_ids: ["EV-1234", "EV-1235"],                       │
│     timestamp: "2025-10-20T14:32:17Z"                           │
│   }                                                             │
│                                                                 │
│ Process: Repeat for all 148 instances                          │
│   - Progress tracker: "47/148 instances complete"              │
│   - Sync after each stair completed (buffered CRDT)            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Stage 4: Validation & Fault Generation (Backend)               │
├─────────────────────────────────────────────────────────────────┤
│ Input: POST /v1/tests/sessions/{id}/results with 148 instances │
│                                                                 │
│ Process: Instance-Level Validation                             │
│   For each instance:                                            │
│     1. Load baseline for (stair_id, floor_id, door_config)     │
│     2. Load AS1851 rule for measurement_type                    │
│     3. Validate: min ≤ measured ≤ max                          │
│     4. Compute deviation from baseline                          │
│     5. If non-compliant → Create fault with instance context   │
│                                                                 │
│ Example Fault:                                                  │
│   {                                                             │
│     fault_id: "F-047",                                          │
│     instance_id: "I-047",                                       │
│     test_session_id: "SESSION-456",                             │
│     stair_id: "Stair-A",                                        │
│     floor_id: "Level-8",                                        │
│     measurement_type: "pressure_differential",                  │
│     door_configuration: "all_closed",                           │
│     measured_value: 18.2,                                       │
│     design_setpoint: 45.0,                                      │
│     min_threshold: 20.0,                                        │
│     severity: "critical",                                       │
│     defect_classification: "1A",                                │
│     description: "Pressure 18.2 Pa below minimum 20 Pa on      │
│                   Stair-A Floor 8 (all doors closed)",         │
│     action_required: "Increase fan speed or check dampers",    │
│     rule_applied: "SP-01",                                      │
│     deviation_from_baseline_pct: -59.6  // (18.2-45)/45        │
│   }                                                             │
│                                                                 │
│ Output: Instance-level compliance results                      │
│   - 146 instances: PASS                                        │
│   - 2 instances: FAIL (Stair-A Floor 8, Stair-B Floor 3)      │
│   - Overall session compliance: 98.6%                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Stage 5: Report Generation (Instance-Level Detail)             │
├─────────────────────────────────────────────────────────────────┤
│ Input: POST /v1/reports/generate {session_id: "SESSION-456"}   │
│                                                                 │
│ Report Structure:                                               │
│   Page 1: Cover                                                 │
│   Page 2: Executive Summary                                     │
│     - 148 instances tested                                      │
│     - 146 passed (98.6%)                                        │
│     - 2 critical faults requiring remediation                  │
│                                                                 │
│   Page 3-N: Instance-Level Results by Stair/Floor              │
│     ┌─────────────────────────────────────────────┐            │
│     │ STAIR-A: PRESSURE DIFFERENTIAL RESULTS      │            │
│     ├──────┬──────┬─────┬────────┬───────┬────────┤            │
│     │Floor │Config│Pa   │Setpoint│Min-Max│Pass/Fail│            │
│     ├──────┼──────┼─────┼────────┼───────┼────────┤            │
│     │Grnd  │Closed│44.1 │45.0    │20-80  │✓ Pass  │            │
│     │Grnd  │Open  │41.8 │45.0    │20-80  │✓ Pass  │            │
│     │Lvl-1 │Closed│43.7 │46.0    │20-80  │✓ Pass  │            │
│     │...   │...   │...  │...     │...    │...     │            │
│     │Lvl-8 │Closed│18.2 │45.0    │20-80  │✗ FAIL  │ ← Fault   │
│     │...   │...   │...  │...     │...    │...     │            │
│     └──────┴──────┴─────┴────────┴───────┴────────┘            │
│                                                                 │
│     Similar tables for:                                         │
│     - STAIR-A: AIR VELOCITY RESULTS (15 doorways)              │
│     - STAIR-A: DOOR FORCE RESULTS (15 doors)                   │
│     - STAIR-B: PRESSURE/VELOCITY/FORCE RESULTS                 │
│     - C&E TEST RESULTS (10 scenarios)                          │
│     - INTERFACE TEST RESULTS (18 tests)                        │
│                                                                 │
│   Page N+1: Trend Analysis (Instance-Level Over Time)          │
│     [Line chart: Stair-A Floor 8 pressure over 3 years]       │
│     Shows: 2023: 44Pa, 2024: 42Pa, 2025: 18Pa (failure)       │
│                                                                 │
│   Page N+2: Defect Register (Instance Context Preserved)       │
│     Fault F-047: Stair-A, Floor 8, All Doors Closed,          │
│                  Pressure 18.2 Pa < min 20 Pa                  │
│                                                                 │
│   Final Page: Audit Metadata                                   │
│     - 148 test instances executed                              │
│     - Instance IDs logged for full traceability                │
└─────────────────────────────────────────────────────────────────┘

3. Archetype Library
Archetype Definition Structure


typescript
interface TestArchetype {
  archetype_id: string;
  archetype_name: string;
  measurement_type: string;
  description: string;
  as1851_reference: string;
  frequencies: Frequency[];
  cardinality_formula: string;
  required_baseline_entities: string[];
  instruments: Instrument[];
  acceptance_criteria: AcceptanceCriteria;
  ux_template: UXTemplate;
  evidence_requirements: EvidenceRequirement[];
}
Archetype 1: Pressure Differential


yaml
archetype_id: ARCH-PRESSURE-001
archetype_name: "Stair Pressurization Pressure Differential Test"
measurement_type: pressure_differential
description: "Measure pressure differential between stair shaft and adjacent floor landing under specified door configuration"
as1851_reference: "AS 1851-2012 § Annual Comprehensive Test Data; AS/NZS 1668.1 § Pressure Differential Requirements"

frequencies:
  - monthly:  # Visual context only, no measurement
      purpose: "Visual inspection of system operation"
      instances: stairs × floors × 1  # No door config variation
  - annual:
      purpose: "Measured pressure differential verification"
      instances: stairs × floors × door_configurations × 1
      door_configurations: [all_closed, evac_doors_open]

cardinality_formula: |
  monthly_instances = count(stairs) × count(floors)
  annual_instances = count(stairs) × count(floors) × 2  # 2 door configs
  
  Example (2 stairs, 15 floors):
    Monthly: 2 × 15 = 30 visual checks
    Annual: 2 × 15 × 2 = 60 measured instances

required_baseline_entities:
  - stairs: [{stair_id, name, orientation}]
  - floors: [{floor_id, level_name, height_m}]
  - baseline_pressure_differentials: [
      {stair_id, floor_id, door_config, pressure_pa, commissioned_date}
    ]
  - design_setpoints: [{stair_id, floor_id, target_pa}]

instruments:
  - type: manometer
    accuracy: ±1 Pa
    calibration_frequency: 12 months
    calibration_standard: ISO/IEC 17025
    required_fields: [serial_number, calibration_cert_id, expiry_date]

acceptance_criteria:
  min_threshold_pa: 20
  max_threshold_pa: 80
  design_setpoint: baseline.pressure_pa  # Floor-specific from commissioning
  deviation_tolerance_pct: ±10  # Warning if deviation > 10% from baseline
  as1851_rule: SP-01

ux_template:
  visual:
    type: floor_plan_highlight
    elements:
      - current_stair: highlight_color_primary
      - current_floor: marker_pin
      - door_states: visual_indicators  # closed/open icons
    image_asset: "assets/floor_plans/{building_id}/{stair_id}/{floor_id}.svg"
  
  audible:
    start_cue: "beep_start.mp3" + "Begin pressure test - {door_configuration}"
    countdown_timer: 30s  # Stabilization period
    measurement_window: "beep_measure.mp3" + "Record pressure now"
    completion_cue: 
      - pass: "tone_success.mp3" + "Pressure within range"
      - fail: "tone_alert.mp3" + "Pressure out of range - fault created"
  
  descriptive:
    steps:
      - step: 1
        instruction: "Configure doors: {door_configuration_instructions}"
        door_configuration_instructions:
          all_closed: "Close all stair doors on floors {floor_id-1}, {floor_id}, {floor_id+1}"
          evac_doors_open: "Open ground floor exit door + doors on {floor_id} and {floor_id+1}"
      - step: 2
        instruction: "Position manometer at {stair_id} landing, Floor {floor_id}, 1.5m height, facing stair shaft interior"
      - step: 3
        instruction: "Wait 30 seconds for pressure stabilization (countdown timer active)"
      - step: 4
        instruction: "Record pressure reading in Pascals (Pa)"
      - step: 5
        instruction: "Capture evidence: manometer display + floor number sign"
  
  safety:
    warnings:
      - "Ensure doors can be manually opened (test override if necessary)"
      - "Confirm no occupants in stairwell during test"
      - "Do not block emergency exits"
    ppe: "None required for pressure testing"
  
  instrument_gate:
    prompt: "Verify instrument calibration before proceeding"
    checks:
      - field: serial_number
        display: "Manometer SN: {instrument.serial_number}"
      - field: calibration_expiry
        display: "Calibration valid until: {cert.expiry_date}"
        validation: cert.expiry_date > today
        fail_action: block_test
        fail_message: "Calibration expired - test cannot proceed. Upload new certificate."
  
  evidence_requirements:
    - type: photo
      description: "Manometer display showing pressure reading"
      mandatory: true
      min_resolution: 1024x768
    - type: photo
      description: "Floor number sign confirming test location"
      mandatory: true
    - type: metadata
      fields: [gps_coordinates, timestamp, device_attestation_token]
      auto_captured: true

instance_keys: |
  {building_id, stair_id, floor_id, door_configuration, frequency, session_id}
  
  Each instance stores:
    - template_id: ARCH-PRESSURE-001
    - instance_id: generated UUID
    - scoped_identifier: "PRESSURE_{stair_id}_{floor_id}_{door_config}"
    - All baseline context (setpoint, thresholds, orientation)
    - Execution status: pending | in_progress | completed | failed
```

**Expansion Example (2 stairs, 15 floors):**
```
Annual Instances:
  Stair-A, Ground, all_closed       → Instance I-001
  Stair-A, Ground, evac_doors_open  → Instance I-002
  Stair-A, Level-1, all_closed      → Instance I-003
  Stair-A, Level-1, evac_doors_open → Instance I-004
  ...
  Stair-A, Level-14, evac_doors_open → Instance I-030
  Stair-B, Ground, all_closed       → Instance I-031
  ...
  Stair-B, Level-14, evac_doors_open → Instance I-060

Total Annual Pressure Instances: 60

Archetype 2: Air Velocity at Doorway


yaml
archetype_id: ARCH-VELOCITY-001
archetype_name: "Doorway Air Velocity Test (Evacuation Scenario)"
measurement_type: air_velocity
description: "Measure air velocity through open stair doorway using 9-point grid method during evacuation scenario (worst-case 3 doors open)"
as1851_reference: "AS 1851-2012 § Annual Test Data; AS/NZS 1668.1 § Air Velocity Requirements"

frequencies:
  - annual:  # Only measured annually
      purpose: "Verify minimum air velocity to prevent smoke infiltration"
      instances: stairs × doorways × 1
      door_scenario: worst_case_3_doors_open

cardinality_formula: |
  annual_instances = count(stairs) × count(doorways_per_stair)
  
  Example (2 stairs, 15 doorways per stair):
    Annual: 2 × 15 = 30 velocity instances

required_baseline_entities:
  - doorways: [
      {doorway_id, stair_id, floor_id, width_m, height_m, 
       orientation, adjacent_space}
    ]
  - baseline_air_velocities: [
      {doorway_id, velocity_ms, door_scenario, commissioned_date,
       measurement_points: [[x,y,velocity]...]}  # 9-point grid
    ]
  - design_velocity_target_ms: 1.0  # From AS/NZS 1668.1

instruments:
  - type: anemometer
    accuracy: ±0.05 m/s
    calibration_frequency: 12 months
    measurement_method: multi_point_grid
    grid_dimensions: 3x3  # 9 points across doorway opening
    required_fields: [serial_number, calibration_cert_id, expiry_date]

acceptance_criteria:
  min_threshold_ms: 1.0
  max_threshold_ms: null  # No upper limit (practical limit ~3-5 m/s)
  design_target: 1.0
  measurement_method: "9-point grid average"
  deviation_tolerance_pct: ±15
  as1851_rule: SP-02

ux_template:
  visual:
    type: doorway_grid_overlay
    elements:
      - doorway_outline: highlight
      - grid_points: 9 numbered circles (1-9)
      - current_point: pulsing_indicator
      - completed_points: checkmark_overlay
    grid_layout: |
      [1] [2] [3]  ← Top (0.8 × height)
      [4] [5] [6]  ← Mid (0.5 × height)
      [7] [8] [9]  ← Bot (0.2 × height)
      
      Horizontal spacing: 0.25, 0.5, 0.75 × width
  
  audible:
    start_cue: "beep_start.mp3" + "Begin velocity test - 9 point grid"
    point_cue: "beep_point.mp3" + "Measure point {point_number}"
    completion_cue:
      - pass: "tone_success.mp3" + "Average velocity {avg_ms} m/s - within range"
      - fail: "tone_alert.mp3" + "Average velocity {avg_ms} m/s - below minimum"
  
  descriptive:
    steps:
      - step: 1
        instruction: "Configure evacuation scenario: Open ground floor exit + doors on {floor_id} and {floor_id+1} (total 3 doors open)"
      - step: 2
        instruction: "Position anemometer at doorway {doorway_id}, use grid overlay on screen"
      - step: 3
        instruction: "Measure velocity at each of 9 grid points (30s stabilization per point):"
        grid_instructions:
          - "Point 1: Top-left (0.25W, 0.8H)"
          - "Point 2: Top-center (0.5W, 0.8H)"
          - "Point 3: Top-right (0.75W, 0.8H)"
          - "Point 4: Mid-left (0.25W, 0.5H)"
          - "Point 5: Mid-center (0.5W, 0.5H) ← Primary reference"
          - "Point 6: Mid-right (0.75W, 0.5H)"
          - "Point 7: Bot-left (0.25W, 0.2H)"
          - "Point 8: Bot-center (0.5W, 0.2H)"




Retry

AW
Continue



"Point 9: Bot-right (0.75W, 0.2H)"
step: 4 instruction: "System auto-calculates average velocity from 9 points"
step: 5 instruction: "Capture evidence: anemometer display at point 5 (center) + doorway with grid overlay"
safety: warnings: - "Maintain safe distance from doorway edges during measurement" - "Ensure anemometer probe is clean and unobstructed" - "Be aware of pressure changes when opening/closing doors" ppe: "None required for velocity testing"
instrument_gate: prompt: "Verify anemometer calibration before proceeding" checks: - field: serial_number display: "Anemometer SN: {instrument.serial_number}" - field: calibration_expiry display: "Calibration valid until: {cert.expiry_date}" validation: cert.expiry_date > today fail_action: block_test fail_message: "Calibration expired - test cannot proceed" - field: probe_condition display: "Visually inspect probe for damage or debris" user_confirmation_required: true
evidence_requirements: - type: photo description: "Anemometer display at grid point 5 (center reference)" mandatory: true - type: photo description: "Doorway with grid overlay showing measurement locations" mandatory: true - type: structured_data description: "9-point velocity measurements" format: | { point_1: {x: 0.25, y: 0.8, velocity_ms: 1.2}, point_2: {x: 0.5, y: 0.8, velocity_ms: 1.3}, ... point_9: {x: 0.75, y: 0.2, velocity_ms: 1.1}, average_velocity_ms: 1.15, door_scenario: "worst_case_3_doors_open" } auto_captured: true
instance_keys: | {building_id, stair_id, doorway_id, floor_id, door_scenario, frequency, session_id}


**Expansion Example:**
```
Annual Instances:
  Stair-A, Ground-Doorway     → Instance I-061 (9-point grid)
  Stair-A, Level-1-Doorway    → Instance I-062
  ...
  Stair-A, Level-14-Doorway   → Instance I-075
  Stair-B, Ground-Doorway     → Instance I-076
  ...
  Stair-B, Level-14-Doorway   → Instance I-090

Total Annual Velocity Instances: 30
```

---

### **Archetype 3: Door Opening Force**
```yaml
archetype_id: ARCH-DOOR-FORCE-001
archetype_name: "Stair Door Opening Force Test (Pressurized)"
measurement_type: door_opening_force
description: "Measure force required to open stair door at handle under worst-case pressurization"
as1851_reference: "AS 1851-2012 § Annual Test Data; AS/NZS 1668.1 § Door Opening Force Limitations"

frequencies:
  - annual:  # Only measured annually
      purpose: "Verify doors can be opened during evacuation under pressurization"
      instances: stairs × doors × 1
      pressurization_state: active_worst_case

cardinality_formula: |
  annual_instances = count(stairs) × count(doors_per_stair)
  
  Example (2 stairs, 15 doors per stair):
    Annual: 2 × 15 = 30 door force instances

required_baseline_entities:
  - doors: [
      {door_id, stair_id, floor_id, door_type, closer_model,
       width_m, height_m, hand: left|right}
    ]
  - baseline_door_forces: [
      {door_id, force_newtons, pressurization_active, commissioned_date,
       measurement_position: at_handle|at_edge}  # AS1851 specifies "at_handle"
    ]
  - design_force_limit_newtons: 110  # From AS/NZS 1668.1

instruments:
  - type: force_gauge
    accuracy: ±2 N
    calibration_frequency: 12 months
    measurement_range: 0-200 N
    measurement_position: door_handle
    required_fields: [serial_number, calibration_cert_id, expiry_date]

acceptance_criteria:
  min_threshold_newtons: null  # No minimum (lighter is better)
  max_threshold_newtons: 110
  design_target: 100  # Target 10N safety margin below limit
  measurement_position: "at_handle"  # Per AS 1851-2012 (clarified in audit)
  deviation_tolerance_pct: ±15
  as1851_rule: SP-03

ux_template:
  visual:
    type: door_diagram_with_handle
    elements:
      - door_outline: highlight
      - handle_position: pulsing_red_dot
      - force_gauge_placement: illustration_overlay
      - measurement_angle: 90_degrees_to_door_face
    image_asset: "assets/diagrams/door_force_measurement.svg"
  
  audible:
    start_cue: "beep_start.mp3" + "Begin door force test - System pressurized"
    ready_cue: "beep_ready.mp3" + "Apply force gauge to handle - pull perpendicular to door"
    measurement_cue: "beep_measure.mp3" + "Pull door open - record peak force"
    completion_cue:
      - pass: "tone_success.mp3" + "Force {force_n} N - within limit"
      - fail: "tone_alert.mp3" + "Force {force_n} N - exceeds maximum 110 N"
  
  descriptive:
    steps:
      - step: 1
        instruction: "Verify stair pressurization system is running (check control panel status)"
      - step: 2
        instruction: "Attach force gauge hook to door handle at {door_id}, Floor {floor_id}"
      - step: 3
        instruction: "Position yourself perpendicular to door face (90° angle)"
      - step: 4
        instruction: "Pull door open smoothly and steadily - record PEAK force when door begins to move"
      - step: 5
        instruction: "Do NOT record force after door is moving (only initial opening force)"
      - step: 6
        instruction: "Capture evidence: Force gauge display + door handle"
  
  safety:
    warnings:
      - "⚠️ CRITICAL: Ensure door can be opened manually before test (verify no lock-out condition)"
      - "Do not exceed 150 N force (risk of gauge damage or door/closer damage)"
      - "Test one door at a time to maintain stairwell pressurization"
      - "If force exceeds 110 N, STOP - Critical defect requires immediate remediation"
    ppe: "None required for door force testing"
  
  instrument_gate:
    prompt: "Verify force gauge calibration before proceeding"
    checks:
      - field: serial_number
        display: "Force Gauge SN: {instrument.serial_number}"
      - field: calibration_expiry
        display: "Calibration valid until: {cert.expiry_date}"
        validation: cert.expiry_date > today
        fail_action: block_test
      - field: gauge_zeroed
        display: "Confirm gauge reads 0 N when unloaded"
        user_confirmation_required: true
  
  evidence_requirements:
    - type: photo
      description: "Force gauge display showing peak force reading"
      mandatory: true
    - type: photo
      description: "Door handle with force gauge attached (showing measurement position)"
      mandatory: true
    - type: metadata
      fields: [door_id, pressurization_active: true, door_closer_model]
      auto_captured: true

instance_keys: |
  {building_id, stair_id, door_id, floor_id, pressurization_active, frequency, session_id}
```

**Expansion Example:**
```
Annual Instances:
  Stair-A, Ground-Door        → Instance I-091 (pressurization active)
  Stair-A, Level-1-Door       → Instance I-092
  ...
  Stair-A, Level-14-Door      → Instance I-105
  Stair-B, Ground-Door        → Instance I-106
  ...
  Stair-B, Level-14-Door      → Instance I-120

Total Annual Door Force Instances: 30
```

---

### **Archetype 4: Cause-and-Effect (C&E) Logic**
```yaml
archetype_id: ARCH-CE-001
archetype_name: "Stair Pressurization Cause-and-Effect Sequence Test"
measurement_type: cause_and_effect_logic
description: "Verify correct activation sequence from smoke detection trigger through fan/damper response to pressure stabilization"
as1851_reference: "AS 1851-2012 § Six-Monthly/Annual Test Data - Cause-and-Effect Logic"

frequencies:
  - six_monthly:  # Spot check (20-30% coverage)
      purpose: "Partial zone verification"
      instances: stairs × zones_sampled × 1
      coverage_rule: "Test 2 zones per stair (rotating selection)"
      zones_sampled: 2  # Out of 5 zones total
  - annual:  # Full coverage
      purpose: "Complete system verification"
      instances: stairs × zones × 1
      coverage_rule: "Test all zones"

cardinality_formula: |
  six_monthly_instances = count(stairs) × 2  # 2 zones per stair (spot check)
  annual_instances = count(stairs) × count(zones)
  
  Example (2 stairs, 5 zones):
    Six-Monthly: 2 × 2 = 4 C&E instances
    Annual: 2 × 5 = 10 C&E instances

required_baseline_entities:
  - zones: [
      {zone_id, zone_name, floors_covered, stair_id}
    ]
  - ce_scenarios: [
      {scenario_id, zone_id, stair_id, trigger_device_id, 
       expected_sequence: [
         {step: 1, component: "ALARM-PANEL", action: "activate", delay_s: 0},
         {step: 2, component: "FAN-01", action: "start", delay_s: 3},
         {step: 3, component: "DAMPER-RELIEF-Z1", action: "open", delay_s: 5},
         {step: 4, component: "PRESSURE-SENSOR-L5", action: "reach_setpoint", delay_s: 15}
       ]}
    ]
  - detection_devices: [{device_id, type: smoke|heat, location, zone_id}]
  - control_equipment: [{equipment_id, type: fan|damper|sensor, stair_id, zone_id}]

instruments:
  - type: stopwatch_timer
    accuracy: ±0.1 s
    description: "Built-in mobile app timer for sequence recording"
  - type: panel_interface
    description: "Direct observation of control panel display/logs"
    optional_integration: "BMS data export for automated timestamp capture"

acceptance_criteria:
  timing_tolerance:
    low_severity: ±2s  # Deviation 0-2s from expected
    medium_severity: ±5s  # Deviation 2-5s
    high_severity: ±10s  # Deviation 5-10s
    critical: ">10s or component_no_response"
  sequence_correctness: all_steps_in_order
  as1851_rule: CE-01

ux_template:
  visual:
    type: timeline_tracker
    elements:
      - expected_timeline: horizontal_bar_with_steps
      - actual_progress: animated_marker
      - step_indicators: numbered_circles_with_checkmarks
      - deviation_warnings: yellow_orange_red_highlights
    layout: |
      Expected: [ALARM]─3s─>[FAN]─5s─>[DAMPER]─15s─>[PRESSURE]
      Actual:   [ALARM]─3.2s─>[FAN]─5.1s─>[DAMPER]─???
  
  audible:
    start_cue: "beep_start.mp3" + "Trigger smoke detector {device_id} - Timer starting"
    step_cues:
      - "beep_step.mp3" + "Step {n} expected at {expected_time}s"
    deviation_alert: "tone_warning.mp3" + "Deviation detected - {component} delayed"
    completion_cue:
      - pass: "tone_success.mp3" + "C&E sequence complete - All steps within tolerance"
      - fail: "tone_alert.mp3" + "C&E sequence failed - Critical deviation or component failure"
  
  descriptive:
    steps:
      - step: 1
        instruction: "Navigate to trigger zone: {zone_id} ({floors_covered})"
      - step: 2
        instruction: "Locate smoke detector: {trigger_device_id}"
      - step: 3
        instruction: "Prepare mobile app C&E timer - Load expected sequence from baseline"
      - step: 4
        instruction: "Activate smoke detector using test magnet/aerosol (per manufacturer spec)"
      - step: 5
        instruction: "Press START TIMER - Observe and confirm each step:"
        sub_steps:
          - "At 0s: Alarm panel activates (audible + visual)"
          - "At ~3s: Fan {fan_id} starts (listen for motor + airflow)"
          - "At ~5s: Relief damper {damper_id} opens (check actuator position indicator)"
          - "At ~15s: Pressure reaches setpoint {target_pa} Pa on Floor {floor_id}"
      - step: 6
        instruction: "For each step, tap 'CONFIRM' when observed → System records actual timestamp"
      - step: 7
        instruction: "If step does NOT occur within expected +10s window → Tap 'DID NOT OCCUR' → Critical fault auto-created"
      - step: 8
        instruction: "Capture evidence: Control panel display showing activation log + zone identifier"
  
  safety:
    warnings:
      - "Notify building occupants before activation (avoid unnecessary evacuation)"
      - "Coordinate with fire alarm monitoring company (test mode if applicable)"
      - "Ensure personnel are clear of fan/damper areas during activation"
      - "Do not leave system in test mode after completion - restore to normal"
    ppe: "Hearing protection recommended if near fan equipment"
  
  instrument_gate:
    prompt: "Verify C&E test prerequisites"
    checks:
      - field: scenario_configured
        display: "Expected sequence loaded: {scenario.scenario_name}"
        validation: scenario.expected_sequence exists
        fail_action: block_test
        fail_message: "No baseline C&E sequence configured for this zone"
      - field: occupancy_notification
        display: "Confirm building occupants notified"
        user_confirmation_required: true
      - field: monitoring_notified
        display: "Confirm fire alarm monitoring company notified (if applicable)"
        user_confirmation_required: true
  
  evidence_requirements:
    - type: photo
      description: "Control panel display showing activation log with timestamps"
      mandatory: true
    - type: photo
      description: "Smoke detector with test magnet/aerosol applied"
      mandatory: false
      recommended: true
    - type: structured_data
      description: "Step-by-step actual sequence with timestamps"
      format: |
        {
          trigger_timestamp: "2025-10-20T14:45:00Z",
          steps: [
            {step: 1, component: "ALARM-PANEL", expected_delay_s: 0, actual_delay_s: 0.0, deviation_s: 0.0, pass: true},
            {step: 2, component: "FAN-01", expected_delay_s: 3, actual_delay_s: 3.2, deviation_s: 0.2, pass: true},
            {step: 3, component: "DAMPER-RELIEF-Z1", expected_delay_s: 5, actual_delay_s: 5.1, deviation_s: 0.1, pass: true},
            {step: 4, component: "PRESSURE-SENSOR-L5", expected_delay_s: 15, actual_delay_s: 16.8, deviation_s: 1.8, pass: true}
          ],
          overall_pass: true,
          max_deviation_s: 1.8
        }
      auto_captured: true

instance_keys: |
  {building_id, stair_id, zone_id, scenario_id, frequency, session_id}
```

**Expansion Example:**
```
Six-Monthly Instances (Spot Check - Zones 1 & 3):
  Stair-A, Zone-1 (Ground-L3)   → Instance I-121 (scenario: Fire Floor 2)
  Stair-A, Zone-3 (L7-L9)        → Instance I-122 (scenario: Fire Floor 8)
  Stair-B, Zone-1 (Ground-L3)   → Instance I-123
  Stair-B, Zone-3 (L7-L9)        → Instance I-124

Annual Instances (Full Coverage - All 5 Zones):
  Stair-A, Zone-1                → Instance I-125
  Stair-A, Zone-2                → Instance I-126
  Stair-A, Zone-3                → Instance I-127
  Stair-A, Zone-4                → Instance I-128
  Stair-A, Zone-5                → Instance I-129
  Stair-B, Zone-1                → Instance I-130
  ...
  Stair-B, Zone-5                → Instance I-134

Total C&E Instances per Year: 4 (six-monthly) + 10 (annual) = 14
```

---

### **Archetype 5: Interface Tests**
```yaml
archetype_id: ARCH-INTERFACE-001
archetype_name: "System Interface Integration Tests"
measurement_type: interface_test
description: "Verify stair pressurization system correctly interfaces with building systems (manual override, fire alarm, shutdown, sprinkler)"
as1851_reference: "AS 1851-2012 § Annual Test Data - Manual Override, Alarm Coordination, Shutdown, Sprinkler Interface"

frequencies:
  - six_monthly:  # Partial coverage
      purpose: "Test critical interfaces (manual override + alarm)"
      instances: {manual_override, alarm_coordination} × locations × stairs
      test_types: [manual_override, alarm_coordination]
  - annual:  # Full coverage
      purpose: "Test all interface types"
      instances: {manual_override, alarm, shutdown, sprinkler} × locations × stairs
      test_types: [manual_override, alarm_coordination, shutdown_sequence, sprinkler_activation]

cardinality_formula: |
  six_monthly_instances = 2 test_types × count(locations_per_type) × count(stairs)
  annual_instances = 4 test_types × count(locations_per_type) × count(stairs)
  
  Example (2 stairs, 3 locations per type):
    Six-Monthly: 2 × 3 × 2 = 12 interface test instances
    Annual: 4 × 3 × 2 = 24 interface test instances

required_baseline_entities:
  - interface_locations: [
      {location_id, location_name, interface_type, stair_id, access_level}
    ]
  - expected_responses: [
      {interface_type, test_action, expected_result, response_time_s}
    ]

interface_types:
  - manual_override:
      locations: [fire_control_panel, bms_workstation, local_override_switch]
      test_action: "Activate manual override control"
      expected_result: "System switches to manual mode OR shuts down (per design intent)"
      response_time_s: 5
  
  - alarm_coordination:
      locations: [fire_alarm_panel, detection_zone_panel]
      test_action: "Trigger fire alarm via test panel"
      expected_result: "Stair pressurization activates within design time"
      response_time_s: 3-5 (from alarm to fan start)
  
  - shutdown_sequence:
      locations: [bms_workstation, fire_control_panel, maintenance_panel]
      test_action: "Initiate system shutdown via control interface"
      expected_result: "Fan stops → Dampers close → Pressure dissipates (orderly sequence)"
      response_time_s: 10-30
  
  - sprinkler_activation:
      locations: [sprinkler_control_panel]
      test_action: "Simulate sprinkler activation signal (do NOT trigger actual sprinklers)"
      expected_result: "System maintains operation OR shuts down (per design intent for water + pressurization interaction)"
      response_time_s: 5

instruments:
  - type: stopwatch_timer
    description: "Measure response time from trigger to system response"
  - type: panel_observation
    description: "Visual confirmation of panel status indicators"

acceptance_criteria:
  response_time_tolerance: ±2s from expected
  sequence_correctness: per baseline expected_response
  as1851_rule: INT-01

ux_template:
  visual:
    type: interface_location_diagram
    elements:
      - control_panel: highlight_with_label
      - test_point: pulsing_indicator
      - expected_response_checklist: step_by_step_items
  
  audible:
    start_cue: "beep_start.mp3" + "Begin {interface_type} test at {location_name}"
    action_cue: "beep_action.mp3" + "Activate control now - Timer started"
    response_detected: "beep_confirm.mp3" + "Response detected at {time}s"
    completion_cue:
      - pass: "tone_success.mp3" + "Interface test passed - Response within tolerance"
      - fail: "tone_alert.mp3" + "Interface test failed - {failure_reason}"
  
  descriptive:
    steps:
      - step: 1
        instruction: "Navigate to interface location: {location_name} (Stair {stair_id})"
      - step: 2
        instruction: "Load expected response from baseline: {expected_result}"
      - step: 3
        instruction: "Prepare mobile app timer"
      - step: 4
        instruction: "Execute test action: {test_action}"
        interface_specific_instructions:
          manual_override: "Press manual override button/switch and observe panel indication change"
          alarm_coordination: "Activate fire alarm test function - Do NOT trigger full building alarm unless coordinated"
          shutdown_sequence: "Initiate shutdown via control menu/button - Observe orderly sequence"
          sprinkler_activation: "Use panel test mode to simulate sprinkler signal - Do NOT activate actual sprinklers"
      - step: 5
        instruction: "Observe system response and record:"
        observations:
          - "Response start time (s)"
          - "Component actions observed (fan stop/start, damper movement, panel status change)"
          - "Response complete time (s)"
      - step: 6
        instruction: "Compare actual response to expected response"
        comparison_checklist:
          - "Response time within tolerance? (Expected ±2s)"
          - "Sequence correct? (Steps in expected order)"
          - "Final state correct? (System in expected mode/status)"
      - step: 7
        instruction: "Restore system to normal operational mode"
      - step: 8
        instruction: "Capture evidence: Control panel before/during/after test + status indicators"
  
  safety:
    warnings:
      - "Coordinate all interface tests with building management"
      - "Do NOT trigger full building evacuation unless specifically planned"
      - "For sprinkler tests: Use SIMULATION mode only - Do NOT activate actual sprinklers"
      - "Ensure system is restored to normal operation after test"
      - "Document any occupant notifications in test notes"
    ppe: "None required for interface testing (control panel access only)"
  
  instrument_gate:
    prompt: "Verify interface test prerequisites"
    checks:
      - field: access_authorization
        display: "Confirm authorized access to {location_name}"
        user_confirmation_required: true
      - field: coordination_confirmed
        display: "Confirm building management/occupants notified"
        user_confirmation_required: true
      - field: baseline_loaded
        display: "Expected response loaded: {expected_result}"
        validation: expected_response exists
  
  evidence_requirements:
    - type: photo
      description: "Control panel BEFORE test (showing normal status)"
      mandatory: true
    - type: photo
      description: "Control panel DURING test (showing activated/changed status)"
      mandatory: true
    - type: photo
      description: "Control panel AFTER test (showing restored normal status)"
      mandatory: true
    - type: structured_data
      description: "Test results with timing"
      format: |
        {
          interface_type: "manual_override",
          location_id: "FIRE-PANEL-01",
          test_action: "Pressed manual override button",
          trigger_time: "2025-10-20T15:10:00Z",
          response_start_time_s: 1.2,
          response_end_time_s: 3.5,
          expected_response: "System switches to manual mode",
          actual_response: "Panel displayed 'MANUAL MODE' - Fans continued running under manual control",
          response_time_within_tolerance: true,
          sequence_correct: true,
          pass: true
        }
      auto_captured: true

instance_keys: |
  {building_id, stair_id, interface_type, location_id, frequency, session_id}
```

**Expansion Example:**
```
Six-Monthly Instances (Manual Override + Alarm Coordination):
  Stair-A, Manual Override, Fire Panel        → Instance I-135
  Stair-A, Manual Override, BMS               → Instance I-136
  Stair-A, Manual Override, Local Switch      → Instance I-137
  Stair-A, Alarm Coordination, Fire Panel     → Instance I-138
  Stair-A, Alarm Coordination, Zone Panel     → Instance I-139
  Stair-B, Manual Override, Fire Panel        → Instance I-140
  ... (6 instances per stair × 2 stairs = 12 six-monthly)

Annual Instances (All 4 Interface Types):
  Stair-A, Manual Override, Fire Panel        → Instance I-147
  Stair-A, Manual Override, BMS               → Instance I-148
  Stair-A, Manual Override, Local Switch      → Instance I-149
  Stair-A, Alarm Coordination, Fire Panel     → Instance I-150
  Stair-A, Alarm Coordination, Zone Panel     → Instance I-151
  Stair-A, Alarm Coordination, BMS            → Instance I-152
  Stair-A, Shutdown, BMS                      → Instance I-153
  Stair-A, Shutdown, Fire Panel               → Instance I-154
  Stair-A, Shutdown, Maintenance Panel        → Instance I-155
  Stair-A, Sprinkler, Control Panel           → Instance I-156
  Stair-B, ... (12 instances)                 → Instances I-157 to I-168

Total Interface Test Instances per Year: 12 (six-monthly) + 24 (annual) = 36
```

---
4. Baseline → Instances Expansion Rules (Continued)
Cardinality Calculation Matrix

Total Annual Measured Instances: 158 per building
Monthly: Visual checks only (30-50 non-measured inspections)
Six-Monthly: 4 C&E + 12 Interface = 16 instances
Annual: 60 Pressure + 30 Velocity + 30 Door Force + 10 C&E + 24 Interface = 154 instances

5. Critical Compliance Gaps in Current Demo
Gap Analysis Summary


6. Revised Data Architecture
Core Schema Changes Required


sql
-- **NEW TABLE: Stairs Registry**
CREATE TABLE stairs (
  stair_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_name VARCHAR(100) NOT NULL,  -- "Stair-A", "North Stairwell", "Exit 2"
  orientation VARCHAR(50),  -- "North", "South", "East", "West", "Central"
  stair_type VARCHAR(50),  -- "fire_isolated", "smoke_proof", "pressurized"
  floor_range_bottom VARCHAR(50),  -- "Ground", "Basement-1"
  floor_range_top VARCHAR(50),  -- "Level-14", "Roof"
  design_standard VARCHAR(100),  -- "AS/NZS 1668.1:2015"
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_name)
);

CREATE INDEX idx_stairs_building ON stairs(building_id);

-- **NEW TABLE: Floors Registry** (Enhanced)
CREATE TABLE floors (
  floor_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,  -- Each floor instance per stair
  floor_level VARCHAR(50) NOT NULL,  -- "Ground", "Level-1", "Level-2", etc.
  floor_number INT,  -- Numeric for sorting: -1 (Basement), 0 (Ground), 1, 2, ...
  height_m DECIMAL(5,2),  -- Floor height above ground
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, floor_level)
);

CREATE INDEX idx_floors_stair ON floors(stair_id);
CREATE INDEX idx_floors_building_number ON floors(building_id, floor_number);

-- **NEW TABLE: Doors Registry**
CREATE TABLE doors (
  door_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  floor_id UUID REFERENCES floors(floor_id) ON DELETE CASCADE,
  door_identifier VARCHAR(100),  -- "D-GF-A", "Door-08-North"
  door_type VARCHAR(50),  -- "fire_rated", "smoke_rated", "standard"
  fire_rating_minutes INT,  -- 60, 90, 120
  door_closer_model VARCHAR(100),
  door_hand VARCHAR(20),  -- "left", "right"
  width_m DECIMAL(4,2),
  height_m DECIMAL(4,2),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, floor_id, door_identifier)
);

CREATE INDEX idx_doors_stair_floor ON doors(stair_id, floor_id);

-- **NEW TABLE: Doorways Registry** (For velocity testing)
CREATE TABLE doorways (
  doorway_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  floor_id UUID REFERENCES floors(floor_id) ON DELETE CASCADE,
  doorway_identifier VARCHAR(100),  -- "DW-GF-A", "Doorway-08-North"
  width_m DECIMAL(4,2),
  height_m DECIMAL(4,2),
  orientation VARCHAR(50),  -- Direction doorway faces
  adjacent_space VARCHAR(100),  -- "Corridor", "Lobby", "Office"
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, floor_id, doorway_identifier)
);

CREATE INDEX idx_doorways_stair_floor ON doorways(stair_id, floor_id);

-- **NEW TABLE: Zones Registry** (For C&E testing)
CREATE TABLE zones (
  zone_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  zone_name VARCHAR(100),  -- "Zone-1", "Ground to Level 3"
  floors_covered JSONB,  -- ["Ground", "Level-1", "Level-2", "Level-3"]
  floor_ids_covered UUID[],  -- Array of floor_id references
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, zone_name)
);

CREATE INDEX idx_zones_stair ON zones(stair_id);

-- **NEW TABLE: Control Equipment Registry**
CREATE TABLE control_equipment (
  equipment_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  zone_id UUID REFERENCES zones(zone_id) ON DELETE SET NULL,
  equipment_type VARCHAR(50),  -- "fan", "damper", "pressure_sensor", "control_panel"
  equipment_identifier VARCHAR(100),  -- "FAN-01", "DAMPER-RELIEF-Z1"
  manufacturer VARCHAR(100),
  model VARCHAR(100),
  serial_number VARCHAR(100),
  installation_date DATE,
  specifications JSONB,  -- {capacity_m3_s: 5.2, motor_kw: 15, ...}
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, equipment_identifier)
);

CREATE INDEX idx_equipment_stair_zone ON control_equipment(stair_id, zone_id);

-- **ENHANCED TABLE: Baseline Pressure Differentials**
CREATE TABLE baseline_pressure_differentials (
  baseline_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  floor_id UUID REFERENCES floors(floor_id) ON DELETE CASCADE,
  door_configuration VARCHAR(50) NOT NULL,  -- "all_closed", "evac_doors_open"
  pressure_pa DECIMAL(6,2) NOT NULL,
  commissioned_date DATE NOT NULL,
  commissioned_by VARCHAR(255),
  commissioning_report_ref VARCHAR(255),
  environmental_conditions JSONB,  -- {temp_c: 22, wind_ms: 2.1, doors_open_list: [...]}
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, floor_id, door_configuration)
);

CREATE INDEX idx_baseline_pressure_stair_floor ON baseline_pressure_differentials(stair_id, floor_id);

-- **ENHANCED TABLE: Baseline Air Velocities**
CREATE TABLE baseline_air_velocities (
  baseline_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  doorway_id UUID REFERENCES doorways(doorway_id) ON DELETE CASCADE,
  door_scenario VARCHAR(50) NOT NULL,  -- "worst_case_3_doors_open"
  velocity_ms DECIMAL(5,3) NOT NULL,
  measurement_points JSONB,  -- [{point: 1, x: 0.25, y: 0.8, velocity_ms: 1.2}, ...]
  average_velocity_ms DECIMAL(5,3),  -- Calculated from 9-point grid
  commissioned_date DATE NOT NULL,
  commissioned_by VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, doorway_id, door_scenario)
);

CREATE INDEX idx_baseline_velocity_doorway ON baseline_air_velocities(doorway_id);

-- **ENHANCED TABLE: Baseline Door Forces**
CREATE TABLE baseline_door_forces (
  baseline_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  door_id UUID REFERENCES doors(door_id) ON DELETE CASCADE,
  pressurization_active BOOLEAN NOT NULL DEFAULT TRUE,
  force_newtons DECIMAL(6,2) NOT NULL,
  measurement_position VARCHAR(50),  -- "at_handle" (AS1851 requirement)
  commissioned_date DATE NOT NULL,
  commissioned_by VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, door_id, pressurization_active)
);

CREATE INDEX idx_baseline_door_force_door ON baseline_door_forces(door_id);

-- **NEW TABLE: C&E Scenarios**
CREATE TABLE ce_scenarios (
  scenario_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  zone_id UUID REFERENCES zones(zone_id) ON DELETE CASCADE,
  scenario_name VARCHAR(255),  -- "Fire Floor 8 - Zone 3 Activation"
  scenario_type VARCHAR(50),  -- "baseline_commissioning", "six_monthly", "annual"
  trigger_device_id VARCHAR(100),  -- Reference to smoke detector ID
  trigger_device_type VARCHAR(50),  -- "smoke_detector", "heat_detector", "manual_call_point"
  expected_sequence JSONB NOT NULL,  -- [{step: 1, component: "ALARM", action: "activate", delay_s: 0}, ...]
  created_at TIMESTAMP DEFAULT NOW(),
  created_by UUID REFERENCES users(id),
  version INT DEFAULT 1,
  active BOOLEAN DEFAULT TRUE,
  UNIQUE(building_id, stair_id, zone_id, scenario_name, version)
);

CREATE INDEX idx_ce_scenarios_zone ON ce_scenarios(zone_id);

-- **NEW TABLE: Interface Test Definitions**
CREATE TABLE interface_test_definitions (
  definition_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  interface_type VARCHAR(50) NOT NULL,  -- "manual_override", "alarm_coordination", "shutdown_sequence", "sprinkler_activation"
  location_id VARCHAR(100) NOT NULL,  -- "FIRE-PANEL-01", "BMS-WORKSTATION", "LOCAL-SWITCH-A"
  location_name VARCHAR(255),
  test_action TEXT,  -- "Press manual override button on fire control panel"
  expected_result TEXT,  -- "System switches to manual mode - Fans continue under manual control"
  response_time_s INT,  -- Expected response time in seconds
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, stair_id, interface_type, location_id)
);

CREATE INDEX idx_interface_defs_stair_type ON interface_test_definitions(stair_id, interface_type);

-- **ENHANCED TABLE: Test Instance Templates** (Pre-generated from archetypes)
CREATE TABLE test_instance_templates (
  template_instance_id UUID PRIMARY KEY,
  building_id UUID REFERENCES buildings(id) ON DELETE CASCADE,
  archetype_id VARCHAR(50) NOT NULL,  -- "ARCH-PRESSURE-001", "ARCH-VELOCITY-001", etc.
  measurement_type VARCHAR(50) NOT NULL,
  frequency VARCHAR(20) NOT NULL,  -- "monthly", "six_monthly", "annual"
  
  -- Instance-specific context
  stair_id UUID REFERENCES stairs(stair_id) ON DELETE CASCADE,
  floor_id UUID REFERENCES floors(floor_id) ON DELETE CASCADE NULL,
  door_id UUID REFERENCES doors(door_id) ON DELETE CASCADE NULL,
  doorway_id UUID REFERENCES doorways(doorway_id) ON DELETE CASCADE NULL,
  zone_id UUID REFERENCES zones(zone_id) ON DELETE CASCADE NULL,
  door_configuration VARCHAR(50),  -- "all_closed", "evac_doors_open", NULL
  door_scenario VARCHAR(50),  -- "worst_case_3_doors_open", NULL
  pressurization_active BOOLEAN,
  interface_type VARCHAR(50),  -- For interface tests
  location_id VARCHAR(100),  -- For interface tests
  scenario_id UUID REFERENCES ce_scenarios(scenario_id) ON DELETE CASCADE NULL,  -- For C&E tests
  
  -- Baseline values
  design_setpoint DECIMAL(10,3),
  baseline_value DECIMAL(10,3),
  baseline_date DATE,
  min_threshold DECIMAL(10,3),
  max_threshold DECIMAL(10,3),
  unit VARCHAR(20),
  
  -- UX assets
  visual_asset_path TEXT,
  descriptive_instructions JSONB,  -- Step-by-step array
  audible_cues JSONB,  -- {start: "beep_start.mp3", ...}
  safety_warnings JSONB,
  
  -- Instrument requirements
  required_instrument_type VARCHAR(50),
  calibration_requirement JSONB,
  
  -- Evidence requirements
  evidence_prompts JSONB,
  
  -- Sequence order
  sequence_order INT,  -- For mobile app navigation
  
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(building_id, archetype_id, frequency, stair_id, floor_id, door_id, doorway_id, zone_id, door_configuration, interface_type, location_id)
);

CREATE INDEX idx_templates_building_freq ON test_instance_templates(building_id, frequency);
CREATE INDEX idx_templates_stair_floor ON test_instance_templates(stair_id, floor_id);

-- **ENHANCED TABLE: Test Instances** (Cloned from templates per session)
CREATE TABLE test_instances (
  instance_id UUID PRIMARY KEY,
  template_instance_id UUID REFERENCES test_instance_templates(template_instance_id),
  session_id UUID REFERENCES test_sessions(id) ON DELETE CASCADE,
  building_id UUID REFERENCES buildings(id),
  archetype_id VARCHAR(50),
  measurement_type VARCHAR(50),
  frequency VARCHAR(20),
  
  -- Instance context (denormalized for query performance)
  stair_id UUID,
  floor_id UUID,
  door_id UUID,
  doorway_id UUID,
  zone_id UUID,
  door_configuration VARCHAR(50),
  door_scenario VARCHAR(50),
  pressurization_active BOOLEAN,
  interface_type VARCHAR(50),
  location_id VARCHAR(100),
  scenario_id UUID,
  
  -- Baseline context
  design_setpoint DECIMAL(10,3),
  baseline_value DECIMAL(10,3),
  baseline_date DATE,
  min_threshold DECIMAL(10,3),
  max_threshold DECIMAL(10,3),
  unit VARCHAR(20),
  
  -- UX (loaded into mobile bundle)
  visual_asset_path TEXT,
  descriptive_instructions JSONB,
  audible_cues JSONB,
  safety_warnings JSONB,
  
  -- Instrument
  required_instrument_type VARCHAR(50),
  required_instrument_id UUID REFERENCES instruments(id) NULL,  -- Assigned instrument
  calibration_requirement JSONB,
  
  -- Evidence
  evidence_prompts JSONB,
  
  -- Execution
  status VARCHAR(20) DEFAULT 'pending',  -- "pending", "in_progress", "completed", "skipped", "failed"
  sequence_order INT,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  technician_id UUID REFERENCES users(id),
  
  -- Results (populated after execution)
  measured_value_numeric DECIMAL(10,3),
  measured_value_text TEXT,  -- For non-numeric (e.g., C&E sequence JSON)
  is_compliant BOOLEAN,
  deviation_from_baseline_pct DECIMAL(6,2),
  validation_result JSONB,  -- {rule_applied: "SP-01", severity: "critical", ...}
  fault_id UUID REFERENCES faults(id) NULL,  -- If non-compliant
  evidence_ids UUID[],  -- Array of evidence record IDs
  notes TEXT,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_instances_session ON test_instances(session_id);
CREATE INDEX idx_instances_status ON test_instances(status);
CREATE INDEX idx_instances_stair_floor ON test_instances(stair_id, floor_id);
CREATE INDEX idx_instances_template ON test_instances(template_instance_id);

-- **ENHANCED TABLE: Evidence Records**
CREATE TABLE evidence_records (
  evidence_id UUID PRIMARY KEY,
  instance_id UUID REFERENCES test_instances(instance_id) ON DELETE CASCADE,
  session_id UUID REFERENCES test_sessions(id),
  evidence_type VARCHAR(50),  -- "photo", "video", "structured_data", "metadata"
  description TEXT,
  file_path TEXT,  -- S3 key
  file_hash_sha256 VARCHAR(64),  -- Integrity verification
  device_attestation_token TEXT,  -- iOS DeviceCheck / Android SafetyNet
  gps_coordinates JSONB,  -- {lat: ..., lng: ..., accuracy: ...}
  captured_at TIMESTAMP,
  uploaded_at TIMESTAMP,
  file_size_bytes BIGINT,
  mime_type VARCHAR(100),
  metadata JSONB,  -- {camera_model: "iPhone 14 Pro", resolution: "4032x3024", ...}
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_evidence_instance ON evidence_records(instance_id);
CREATE INDEX idx_evidence_session ON evidence_records(session_id);

-- **ENHANCED TABLE: Faults** (Updated with instance context)
ALTER TABLE faults ADD COLUMN instance_id UUID REFERENCES test_instances(instance_id) ON DELETE SET NULL;
ALTER TABLE faults ADD COLUMN stair_id UUID REFERENCES stairs(stair_id) ON DELETE SET NULL;
ALTER TABLE faults ADD COLUMN floor_id UUID REFERENCES floors(floor_id) ON DELETE SET NULL;
ALTER TABLE faults ADD COLUMN door_id UUID REFERENCES doors(door_id) ON DELETE SET NULL;
ALTER TABLE faults ADD COLUMN doorway_id UUID REFERENCES doorways(doorway_id) ON DELETE SET NULL;
ALTER TABLE faults ADD COLUMN zone_id UUID REFERENCES zones(zone_id) ON DELETE SET NULL;
ALTER TABLE faults ADD COLUMN door_configuration VARCHAR(50);
ALTER TABLE faults ADD COLUMN measurement_type VARCHAR(50);

CREATE INDEX idx_faults_instance ON faults(instance_id);
CREATE INDEX idx_faults_stair_floor ON faults(stair_id, floor_id);

7. Instance Generation Algorithm


typescript
/**
 * Baseline-Driven Instance Expansion Engine
 * Generates test instances from archetypes + baseline cardinalities
 */
async function generateTestInstances(
  buildingId: string,
  frequency: Frequency
): Promise<TestInstance[]> {
  
  // 1. Load baseline entities
  const baseline = await loadBaseline(buildingId);
  
  // Validation: Baseline completeness check
  const completeness = validateBaselineCompleteness(baseline);
  if (!completeness.complete) {
    throw new BaselineIncompleteError(
      `Cannot generate test instances. Missing: ${completeness.missing.join(', ')}`
    );
  }
  
  // 2. Load applicable archetypes for frequency
  const archetypes = await loadArchetypes(frequency);
  
  const allInstances: TestInstance[] = [];
  
  // 3. Expand each archetype
  for (const archetype of archetypes) {
    const expansionRule = getExpansionRule(archetype.archetype_id);
    
    // Calculate expected cardinality
    const expectedCount = expansionRule.cardinality_function(baseline);
    
    // Generate instances
    const instances = await expansionRule.instance_generator(baseline, frequency);
    
    // Validation: Cardinality gate
    if (instances.length !== expectedCount) {
      throw new CardinalityError(
        `Archetype ${archetype.archetype_id}: Expected ${expectedCount} instances, generated ${instances.length}`
      );
    }
    
    // Validation: Baseline completeness per instance
    for (const instance of instances) {
      expansionRule.validation_rules.forEach(rule => rule.check(instance, baseline));
    }
    
    allInstances.push(...instances);
  }
  
  // 4. Persist templates (idempotent - upsert)
  await upsertTestInstanceTemplates(allInstances);
  
  return allInstances;
}

/**
 * Baseline Completeness Validator
 */
function validateBaselineCompleteness(baseline: Baseline): BaselineStatus {
  const required = {
    stairs: baseline.stairs.length > 0,
    floors: baseline.floors.length > 0,
    doors: baseline.doors.length > 0,
    doorways: baseline.doorways.length > 0,
    zones: baseline.zones.length > 0,
    control_equipment: baseline.control_equipment.length > 0,
    
    // Baseline measurements
    pressure_baselines: checkPressureBaselines(baseline),  // All stairs × floors × 2 door configs
    velocity_baselines: checkVelocityBaselines(baseline),  // All stairs × doorways
    door_force_baselines: checkDoorForceBaselines(baseline),  // All stairs × doors
    ce_scenarios: checkCEScenarios(baseline),  // At least 1 scenario per zone
    interface_definitions: checkInterfaceDefinitions(baseline),  // All 4 interface types × locations
    
    // Instruments & calibration
    instruments_registered: baseline.instruments.length > 0,
    calibration_certificates: baseline.calibration_certs.filter(cert => cert.expiry_date > new Date()).length > 0
  };
  
  const complete = Object.values(required).every(v => v === true);
  const missing = Object.keys(required).filter(k => !required[k]);
  const percentage = (Object.values(required).filter(v => v).length / Object.keys(required).length) * 100;
  
  return { complete, missing, percentage };
}

/**
 * Example: Pressure Differential Instance Generator
 */
async function generatePressureInstances(
  baseline: Baseline,
  frequency: Frequency
): Promise<TestInstance[]> {
  
  const instances: TestInstance[] = [];
  let sequenceOrder = 1;
  
  for (const stair of baseline.stairs) {
    for (const floor of baseline.floors.filter(f => f.stair_id === stair.stair_id)) {
      
      // For annual frequency, test both door configurations
      const doorConfigs = frequency === 'annual' ? ['all_closed', 'evac_doors_open'] : ['all_closed'];
      
      for (const doorConfig of doorConfigs) {
        
        // Load baseline for this specific combination
        const baseline_pressure = await getBaselinePressure(
          baseline.building_id,
          stair.stair_id,
          floor.floor_id,
          doorConfig
        );
        
        if (!baseline_pressure) {
          throw new BaselineError(
            `Missing baseline pressure for ${stair.stair_name} ${floor.floor_level} ${doorConfig}`
          );
        }
        
        // Load design setpoint
        const setpoint = await getDesignSetpoint(
          baseline.building_id,
          stair.stair_id,
          floor.floor_id
        );
        
        // Load AS1851 rule
        const rule = await getAS1851Rule('pressure_differential');
        
        const instance: TestInstance = {
          instance_id: generateUUID(),
          template_instance_id: null,  // Will be set after upsert
          session_id: null,  // Set when cloned to session
          building_id: baseline.building_id,
          archetype_id: 'ARCH-PRESSURE-001',
          measurement_type: 'pressure_differential',
          frequency,
          
          stair_id: stair.stair_id,
          floor_id: floor.floor_id,
          door_configuration: doorConfig,
          
          design_setpoint: setpoint?.target_pa || 45,
          baseline_value: baseline_pressure.pressure_pa,
          baseline_date: baseline_pressure.commissioned_date,
          min_threshold: rule.min_threshold,
          max_threshold: rule.max_threshold,
          unit: 'Pa',
          
          visual_asset_path: `assets/floor_plans/${baseline.building_id}/${stair.stair_id}/${floor.floor_id}.svg`,
          descriptive_instructions: generatePressureInstructions(doorConfig, floor.floor_level),
          audible_cues: {
            start: 'beep_start.mp3',
            countdown: 30,  // seconds
            measure: 'beep_measure.mp3',
            success: 'tone_success.mp3',
            fail: 'tone_alert.mp3'
          },
          safety_warnings: [
            'Ensure doors can be manually opened',
            'Confirm no occupants in stairwell'
          ],
          
          required_instrument_type: 'manometer',
          calibration_requirement: {
            frequency_months: 12,
            standard: 'ISO/IEC 17025'
          },
          
          evidence_prompts: [
            { type: 'photo', description: 'Manometer display', mandatory: true },
            { type: 'photo', description: 'Floor number sign', mandatory: true }
          ],
          
          sequence_order: sequenceOrder++,
          status: 'template',  // Not yet instantiated to a session
          
          created_at: new Date()
        };
        
        instances.push(instance);
      }
    }
  }
  
  return instances;
}
```

---

## 8. Mobile UX Specification: Instance-Driven Navigation

### **Navigation Hierarchy**
```
Test Session (Annual - 158 instances)
│
├─ Stair-A (79 instances)
│  ├─ Ground Floor (8 instances)
│  │  ├─ [PRESSURE] All Doors Closed → Instance I-001
│  │  ├─ [PRESSURE] Evac Doors Open → Instance I-002
│  │  ├─ [VELOCITY] Doorway (9-point grid) → Instance I-003
│  │  └─ [DOOR FORCE] Door → Instance I-004
│  │
│  ├─ Level-1 (8 instances)
│  │  └─ ... (same pattern)
│  │
│  ├─ ... (Levels 2-14)
│  │
│  ├─ Zone-1 (1 C&E instance)
│  │  └─ [C&E] Fire Floor 2 Activation → Instance I-071
│  │
│  └─ Interface Tests (12 instances)
│     ├─ [INTERFACE] Manual Override - Fire Panel → Instance I-072
│     └─ ... (11 more interface tests)
│
└─ Stair-B (79 instances)
   └─ ... (same structure as Stair-A)
Instance Execution Screen Specification


typescript
interface InstanceExecutionScreen {
  instance: TestInstance;
  
  // Visual Section
  visual: {
    floor_plan_svg: string;  // Rendered from visual_asset_path
    highlighted_elements: {
      current_stair: 'primary_highlight',
      current_floor: 'marker_pin',
      door_states: 'visual_indicators'  // Icons for closed/open
    };
    augmented_reality_overlay?: {  // Future enhancement
      device_camera_feed: true,
      overlay_grid_points: true  // For velocity 9-point grid
    };
  };
  
  // Audible Section
  audible: {
    start_cue: AudioCue;  // "Begin pressure test - All doors closed"
    countdown_timer?: {
      duration_seconds: 30,
      tick_sound: 'beep_tick.mp3',
      completion_sound: 'beep_measure.mp3'
    };
    measurement_prompt: AudioCue;  // "Record pressure now"
    completion_cue: {
      pass: AudioCue,  // "tone_success.mp3"
      fail: AudioCue   // "tone_alert.mp3"
    };
  };
  
  // Descriptive Section
  descriptive: {
    steps: InstructionStep[];  // Rendered as numbered checklist
    current_step_index: number;
    step_navigation: {
      next_button: boolean,
      previous_button: boolean,
      skip_button: boolean  // Only if instance is non-mandatory
    };
  };
  
  // Safety Section
  safety: {
    warnings: string[];  // Rendered as alert cards with icons




Retry

AW
Continue





typescript
    ppe_required: string[];  // "None required" or list of PPE
    emergency_stop_button: {
      visible: boolean,
      action: 'abort_test_and_mark_skipped'
    };
  };
  
  // Instrument Gate Section
  instrument_gate: {
    required_instrument_type: string;  // "manometer", "anemometer", "force_gauge"
    instrument_selection: {
      available_instruments: Instrument[];  // Filtered by type + building
      selected_instrument_id: UUID | null;
    };
    calibration_check: {
      serial_number: string,
      calibration_expiry_date: Date,
      is_valid: boolean,
      validation_logic: 'expiry_date > today',
      fail_action: 'block_test',
      fail_message: string
    };
    additional_checks: {
      field: string,  // e.g., "gauge_zeroed", "probe_clean"
      display: string,
      user_confirmation_required: boolean,
      checkbox: boolean
    }[];
    gate_status: 'locked' | 'unlocked';  // Test cannot proceed if locked
  };
  
  // Measurement Input Section
  measurement_input: {
    input_type: 'numeric' | 'multi_point_grid' | 'sequence_timer' | 'binary';
    
    // For numeric (pressure, door force)
    numeric_input?: {
      value: number | null,
      unit: string,  // "Pa", "N", "m/s"
      design_setpoint: number,  // Displayed for reference
      min_threshold: number,
      max_threshold: number,
      real_time_validation: boolean,  // Show pass/fail as user types
      validation_indicators: {
        below_min: 'red_alert',
        within_range: 'green_check',
        above_max: 'red_alert'
      }
    };
    
    // For velocity (9-point grid)
    grid_input?: {
      grid_dimensions: { rows: 3, cols: 3 },
      points: GridPoint[],  // [{point_number: 1, x: 0.25, y: 0.8, velocity_ms: null}, ...]
      current_point: number,
      average_velocity: number | null,  // Auto-calculated
      grid_overlay_svg: string,  // Visual guide on doorway
      point_navigation: {
        next_point_button: boolean,
        previous_point_button: boolean
      }
    };
    
    // For C&E sequence timing
    sequence_timer?: {
      trigger_timestamp: Date | null,
      stopwatch_running: boolean,
      expected_steps: CEStep[],
      actual_steps: CEStepResult[],
      current_step_index: number,
      step_confirmation_buttons: {
        confirm_step: 'Component activated as expected',
        did_not_occur: 'Component did NOT activate'
      },
      timeline_visualization: {
        expected_timeline_bar: SVGElement,
        actual_progress_marker: SVGElement,
        deviation_highlights: 'yellow_orange_red'
      }
    };
    
    // For interface tests (binary + timing)
    interface_test_input?: {
      test_action_description: string,
      trigger_button: 'Activate Interface',
      timer_started: boolean,
      response_detected: boolean,
      response_time_seconds: number | null,
      expected_response_time: number,
      expected_result_description: string,
      actual_result_textarea: string,  // Free-text observation
      pass_fail_toggle: 'pass' | 'fail' | null
    };
  };
  
  // Evidence Capture Section
  evidence_capture: {
    prompts: EvidencePrompt[];  // [{type: 'photo', description: '...', mandatory: true}, ...]
    captured_evidence: Evidence[],
    camera_button: {
      enabled: boolean,
      opens: 'native_camera_with_metadata_capture'
    };
    evidence_preview: {
      thumbnail_grid: boolean,
      view_fullscreen_button: boolean,
      delete_button: boolean
    };
    metadata_auto_capture: {
      gps_coordinates: { lat: number, lng: number, accuracy: number } | null,
      timestamp: Date,
      device_attestation_token: string,  // iOS DeviceCheck / Android SafetyNet
      file_hash_sha256: string  // Computed on capture
    };
    evidence_completeness_indicator: {
      required_count: number,
      captured_count: number,
      blocking: boolean  // Cannot complete instance if evidence incomplete
    };
  };
  
  // Notes Section
  notes: {
    technician_notes_textarea: string,
    placeholder: 'Optional: Add any observations, issues, or context',
    max_length: 2000
  };
  
  // Instance Progress Indicator
  progress: {
    current_instance_number: number,
    total_instances: number,
    percentage_complete: number,
    display: '{current}/{total} instances complete ({percentage}%)'
  };
  
  // Actions
  actions: {
    complete_instance_button: {
      enabled: boolean,  // Only if instrument gate passed + evidence complete
      action: 'validate_and_submit_instance',
      validation_checks: [
        'instrument_gate_passed',
        'measurement_captured',
        'evidence_requirements_met'
      ]
    };
    skip_instance_button: {
      enabled: boolean,
      requires_reason: boolean,
      skip_reasons: ['Equipment unavailable', 'Safety concern', 'Access restricted', 'Other'],
      action: 'mark_instance_skipped'
    };
    save_draft_button: {
      enabled: boolean,
      action: 'save_to_realm_local_only',
      auto_save_interval: 30  // seconds
    };
  };
  
  // Sync Status Indicator
  sync_status: {
    realm_sync_enabled: boolean,
    offline_mode: boolean,
    instances_pending_sync: number,
    last_sync_timestamp: Date | null,
    sync_button: {
      visible: boolean,
      action: 'trigger_manual_sync'
    };
  };
}

interface GridPoint {
  point_number: number;  // 1-9
  x: number;  // Normalized position 0-1 across doorway width
  y: number;  // Normalized position 0-1 across doorway height
  velocity_ms: number | null;
  captured_at: Date | null;
}

interface CEStep {
  step_order: number;
  component_id: string;  // "ALARM-PANEL", "FAN-01", "DAMPER-RELIEF-Z1"
  component_type: string;  // "alarm", "fan", "damper", "sensor"
  expected_action: string;  // "activate", "start", "open", "reach_setpoint"
  expected_delay_seconds: number;  // From trigger
  tolerance_seconds: number;  // ±2s, ±5s, ±10s based on severity thresholds
}

interface CEStepResult {
  step_order: number;
  component_id: string;
  expected_action: string;
  expected_delay_seconds: number;
  actual_action: string | null;  // What actually happened
  actual_delay_seconds: number | null;
  deviation_seconds: number | null;
  did_not_occur: boolean;  // If component failed to respond
  severity: 'pass' | 'low' | 'medium' | 'high' | 'critical';
  timestamp: Date | null;
}

interface EvidencePrompt {
  type: 'photo' | 'video' | 'structured_data' | 'metadata';
  description: string;
  mandatory: boolean;
  min_resolution?: string;  // "1024x768"
  example_image?: string;  // Reference image showing what to capture
}

interface Evidence {
  evidence_id: UUID;
  instance_id: UUID;
  type: 'photo' | 'video' | 'structured_data' | 'metadata';
  description: string;
  file_path: string;  // Local Realm path before sync, S3 key after sync
  file_hash_sha256: string;
  device_attestation_token: string;
  gps_coordinates: { lat: number, lng: number, accuracy: number } | null;
  captured_at: Date;
  uploaded_at: Date | null;
  sync_status: 'local_only' | 'syncing' | 'synced';
  file_size_bytes: number;
  mime_type: string;
  metadata: Record<string, any>;
}

9. Backend Validation & Fault Generation Logic
Instance-Level Validation Engine


python
# services/api/src/app/services/instance_validator.py

from typing import Dict, Any, Optional
from datetime import datetime
from app.models import TestInstance, Fault, AS1851Rule, BaselinePressure, BaselineVelocity, BaselineDoorForce
from app.utils.logger import logger

class InstanceValidator:
    """
    Validates individual test instance results against baseline + AS1851 rules.
    Creates faults for non-compliant instances with full context preservation.
    """
    
    def validate_instance(
        self, 
        instance: TestInstance, 
        measurement_value: float | Dict[str, Any],
        actual_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Main validation entry point - routes to measurement-type-specific validators.
        """
        
        if instance.measurement_type == 'pressure_differential':
            return self._validate_pressure_instance(instance, measurement_value, actual_data)
        
        elif instance.measurement_type == 'air_velocity':
            return self._validate_velocity_instance(instance, measurement_value, actual_data)
        
        elif instance.measurement_type == 'door_opening_force':
            return self._validate_door_force_instance(instance, measurement_value, actual_data)
        
        elif instance.measurement_type == 'cause_and_effect_logic':
            return self._validate_ce_instance(instance, actual_data)
        
        elif instance.measurement_type == 'interface_test':
            return self._validate_interface_instance(instance, actual_data)
        
        else:
            raise ValueError(f"Unknown measurement type: {instance.measurement_type}")
    
    
    def _validate_pressure_instance(
        self, 
        instance: TestInstance, 
        measured_pressure_pa: float,
        actual_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate pressure differential instance.
        """
        
        # Load AS1851 rule for pressure differential
        rule = self._get_rule('pressure_differential')
        
        # Threshold validation
        is_compliant = (
            rule.min_threshold <= measured_pressure_pa <= rule.max_threshold
        )
        
        # Baseline deviation calculation
        deviation_pct = None
        if instance.baseline_value:
            deviation_pct = (
                (measured_pressure_pa - instance.baseline_value) / instance.baseline_value
            ) * 100
        
        # Determine severity if non-compliant
        fault = None
        if not is_compliant:
            fault = self._create_pressure_fault(
                instance=instance,
                measured_value=measured_pressure_pa,
                rule=rule,
                deviation_pct=deviation_pct,
                actual_data=actual_data
            )
        
        return ValidationResult(
            instance_id=instance.instance_id,
            is_compliant=is_compliant,
            measured_value=measured_pressure_pa,
            baseline_value=instance.baseline_value,
            design_setpoint=instance.design_setpoint,
            deviation_from_baseline_pct=deviation_pct,
            rule_applied=rule.rule_code,
            fault_id=fault.fault_id if fault else None,
            validation_timestamp=datetime.utcnow()
        )
    
    
    def _create_pressure_fault(
        self,
        instance: TestInstance,
        measured_value: float,
        rule: AS1851Rule,
        deviation_pct: Optional[float],
        actual_data: Dict[str, Any]
    ) -> Fault:
        """
        Create fault record with full instance context.
        """
        
        # Determine severity
        if measured_value < rule.min_threshold:
            severity = 'critical'
            defect_classification = '1A'
            description = (
                f"Pressure {measured_value:.1f} Pa BELOW minimum {rule.min_threshold} Pa "
                f"on {instance.stair.stair_name} {instance.floor.floor_level} "
                f"({instance.door_configuration})"
            )
            action_required = "Increase fan speed, check damper positions, inspect for air leaks"
        
        elif measured_value > rule.max_threshold:
            severity = 'high'
            defect_classification = '1B'
            description = (
                f"Pressure {measured_value:.1f} Pa ABOVE maximum {rule.max_threshold} Pa "
                f"on {instance.stair.stair_name} {instance.floor.floor_level} "
                f"({instance.door_configuration})"
            )
            action_required = "Reduce fan speed, check relief damper operation, verify controls"
        
        else:
            # Should not reach here, but handle edge case
            severity = 'medium'
            defect_classification = '2'
            description = f"Pressure validation anomaly: {measured_value:.1f} Pa"
            action_required = "Review measurement and validation logic"
        
        # Create fault with full context
        fault = Fault(
            fault_id=generate_uuid(),
            test_session_id=instance.session_id,
            instance_id=instance.instance_id,
            building_id=instance.building_id,
            stair_id=instance.stair_id,
            floor_id=instance.floor_id,
            door_configuration=instance.door_configuration,
            measurement_type=instance.measurement_type,
            
            severity=severity,
            defect_classification=defect_classification,
            description=description,
            action_required=action_required,
            
            measured_value=measured_value,
            design_setpoint=instance.design_setpoint,
            baseline_value=instance.baseline_value,
            min_threshold=rule.min_threshold,
            max_threshold=rule.max_threshold,
            unit='Pa',
            deviation_from_baseline_pct=deviation_pct,
            
            rule_applied=rule.rule_code,
            rule_version=rule.version,
            
            detected_at=datetime.utcnow(),
            status='open',
            
            evidence_ids=actual_data.get('evidence_ids', []),
            technician_notes=actual_data.get('notes'),
            environmental_conditions=actual_data.get('environmental_conditions')
        )
        
        db.session.add(fault)
        db.session.commit()
        
        logger.info(
            f"Created fault {fault.fault_id} for instance {instance.instance_id}: "
            f"{severity} - {description}"
        )
        
        return fault
    
    
    def _validate_velocity_instance(
        self,
        instance: TestInstance,
        measured_velocity_ms: float,
        actual_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate air velocity instance (9-point grid average).
        """
        
        rule = self._get_rule('air_velocity')
        
        # Velocity must be >= 1.0 m/s (no upper limit in AS1851)
        is_compliant = measured_velocity_ms >= rule.min_threshold
        
        # Baseline deviation
        deviation_pct = None
        if instance.baseline_value:
            deviation_pct = (
                (measured_velocity_ms - instance.baseline_value) / instance.baseline_value
            ) * 100
        
        fault = None
        if not is_compliant:
            fault = Fault(
                fault_id=generate_uuid(),
                test_session_id=instance.session_id,
                instance_id=instance.instance_id,
                building_id=instance.building_id,
                stair_id=instance.stair_id,
                floor_id=instance.floor_id,
                doorway_id=instance.doorway_id,
                measurement_type='air_velocity',
                
                severity='high',
                defect_classification='1B',
                description=(
                    f"Air velocity {measured_velocity_ms:.2f} m/s BELOW minimum {rule.min_threshold} m/s "
                    f"at {instance.stair.stair_name} {instance.floor.floor_level} doorway "
                    f"(9-point grid average)"
                ),
                action_required="Increase fan capacity, check doorway obstructions, verify evacuation door scenario",
                
                measured_value=measured_velocity_ms,
                baseline_value=instance.baseline_value,
                min_threshold=rule.min_threshold,
                max_threshold=rule.max_threshold,
                unit='m/s',
                deviation_from_baseline_pct=deviation_pct,
                
                rule_applied=rule.rule_code,
                detected_at=datetime.utcnow(),
                status='open',
                
                evidence_ids=actual_data.get('evidence_ids', []),
                technician_notes=actual_data.get('notes'),
                
                # Store 9-point grid data in metadata
                metadata={
                    'grid_measurements': actual_data.get('grid_measurements', [])
                }
            )
            
            db.session.add(fault)
            db.session.commit()
        
        return ValidationResult(
            instance_id=instance.instance_id,
            is_compliant=is_compliant,
            measured_value=measured_velocity_ms,
            baseline_value=instance.baseline_value,
            deviation_from_baseline_pct=deviation_pct,
            rule_applied=rule.rule_code,
            fault_id=fault.fault_id if fault else None,
            validation_timestamp=datetime.utcnow()
        )
    
    
    def _validate_door_force_instance(
        self,
        instance: TestInstance,
        measured_force_n: float,
        actual_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate door opening force instance.
        """
        
        rule = self._get_rule('door_opening_force')
        
        # Force must be <= 110 N (no minimum)
        is_compliant = measured_force_n <= rule.max_threshold
        
        # Baseline deviation
        deviation_pct = None
        if instance.baseline_value:
            deviation_pct = (
                (measured_force_n - instance.baseline_value) / instance.baseline_value
            ) * 100
        
        fault = None
        if not is_compliant:
            fault = Fault(
                fault_id=generate_uuid(),
                test_session_id=instance.session_id,
                instance_id=instance.instance_id,
                building_id=instance.building_id,
                stair_id=instance.stair_id,
                floor_id=instance.floor_id,
                door_id=instance.door_id,
                measurement_type='door_opening_force',
                
                severity='critical',
                defect_classification='1A',
                description=(
                    f"Door opening force {measured_force_n:.1f} N EXCEEDS maximum {rule.max_threshold} N "
                    f"at {instance.stair.stair_name} {instance.floor.floor_level} "
                    f"(Door {instance.door.door_identifier}, pressurization active)"
                ),
                action_required=(
                    "URGENT: Adjust door closer, reduce pressurization level, or install "
                    "powered door opener. Door may be unsafe for evacuation."
                ),
                
                measured_value=measured_force_n,
                baseline_value=instance.baseline_value,
                min_threshold=rule.min_threshold,
                max_threshold=rule.max_threshold,
                unit='N',
                deviation_from_baseline_pct=deviation_pct,
                
                rule_applied=rule.rule_code,
                detected_at=datetime.utcnow(),
                status='open',
                priority='urgent',  # Escalate to high priority
                
                evidence_ids=actual_data.get('evidence_ids', []),
                technician_notes=actual_data.get('notes')
            )
            
            db.session.add(fault)
            db.session.commit()
        
        return ValidationResult(
            instance_id=instance.instance_id,
            is_compliant=is_compliant,
            measured_value=measured_force_n,
            baseline_value=instance.baseline_value,
            deviation_from_baseline_pct=deviation_pct,
            rule_applied=rule.rule_code,
            fault_id=fault.fault_id if fault else None,
            validation_timestamp=datetime.utcnow()
        )
    
    
    def _validate_ce_instance(
        self,
        instance: TestInstance,
        actual_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate cause-and-effect sequence instance.
        """
        
        rule = self._get_rule('cause_and_effect_logic')
        expected_sequence = instance.scenario.expected_sequence
        actual_sequence = actual_data.get('actual_sequence', [])
        
        faults = []
        overall_compliant = True
        max_severity = None
        
        # Validate each step
        for expected_step in expected_sequence:
            actual_step = next(
                (s for s in actual_sequence if s['step_order'] == expected_step['step_order']),
                None
            )
            
            if not actual_step or actual_step.get('did_not_occur'):
                # Component did not respond - CRITICAL
                fault = Fault(
                    fault_id=generate_uuid(),
                    test_session_id=instance.session_id,
                    instance_id=instance.instance_id,
                    building_id=instance.building_id,
                    stair_id=instance.stair_id,
                    zone_id=instance.zone_id,
                    measurement_type='cause_and_effect_logic',
                    
                    severity='critical',
                    defect_classification='1A',
                    description=(
                        f"C&E FAILURE: {expected_step['component_id']} did NOT {expected_step['expected_action']} "
                        f"in Zone {instance.zone.zone_name} ({instance.stair.stair_name})"
                    ),
                    action_required=(
                        f"Urgent: Inspect {expected_step['component_id']} wiring, controls, and component operation. "
                        f"System may not activate properly during fire emergency."
                    ),
                    
                    rule_applied=rule.rule_code,
                    detected_at=datetime.utcnow(),
                    status='open',
                    priority='urgent',
                    
                    metadata={
                        'expected_step': expected_step,
                        'actual_step': actual_step
                    }
                )
                
                faults.append(fault)
                overall_compliant = False
                max_severity = 'critical'
            
            elif actual_step:
                # Component responded - check timing
                delay_deviation = abs(
                    actual_step['actual_delay_seconds'] - expected_step['expected_delay_seconds']
                )
                
                # Determine severity based on delay deviation
                if delay_deviation > 10:
                    severity = 'high'
                    defect_classification = '1B'
                elif delay_deviation > 5:
                    severity = 'medium'
                    defect_classification = '2'
                elif delay_deviation > 2:
                    severity = 'low'
                    defect_classification = '3'
                else:
                    # Within tolerance - no fault
                    continue
                
                fault = Fault(
                    fault_id=generate_uuid(),
                    test_session_id=instance.session_id,
                    instance_id=instance.instance_id,
                    building_id=instance.building_id,
                    stair_id=instance.stair_id,
                    zone_id=instance.zone_id,
                    measurement_type='cause_and_effect_logic',
                    
                    severity=severity,
                    defect_classification=defect_classification,
                    description=(
                        f"C&E TIMING DEVIATION: {expected_step['component_id']} "
                        f"expected at +{expected_step['expected_delay_seconds']}s, "
                        f"actual +{actual_step['actual_delay_seconds']}s "
                        f"(deviation: {delay_deviation:.1f}s) "
                        f"in Zone {instance.zone.zone_name}"
                    ),
                    action_required=(
                        f"Adjust control timing for {expected_step['component_id']}, "
                        f"verify delay settings in control panel"
                    ),
                    
                    rule_applied=rule.rule_code,
                    detected_at=datetime.utcnow(),
                    status='open',
                    
                    metadata={
                        'expected_step': expected_step,
                        'actual_step': actual_step,
                        'delay_deviation_seconds': delay_deviation
                    }
                )
                
                faults.append(fault)
                overall_compliant = False
                
                # Track worst severity
                if max_severity is None or self._severity_rank(severity) > self._severity_rank(max_severity):
                    max_severity = severity
        
        # Save all faults
        for fault in faults:
            db.session.add(fault)
        db.session.commit()
        
        return ValidationResult(
            instance_id=instance.instance_id,
            is_compliant=overall_compliant,
            rule_applied=rule.rule_code,
            fault_ids=[f.fault_id for f in faults],
            validation_timestamp=datetime.utcnow(),
            metadata={
                'sequence_results': actual_sequence,
                'faults_count': len(faults),
                'max_severity': max_severity
            }
        )
    
    
    def _validate_interface_instance(
        self,
        instance: TestInstance,
        actual_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate interface test instance.
        """
        
        rule = self._get_rule('interface_test')
        
        # Check if response was correct
        response_correct = actual_data.get('response_correct', False)
        response_time_seconds = actual_data.get('response_time_seconds')
        expected_response_time = instance.interface_definition.response_time_s
        
        # Timing tolerance: ±2s
        timing_compliant = True
        if response_time_seconds and expected_response_time:
            timing_deviation = abs(response_time_seconds - expected_response_time)
            timing_compliant = timing_deviation <= 2
        
        is_compliant = response_correct and timing_compliant
        
        fault = None
        if not is_compliant:
            if not response_correct:
                severity = 'critical'
                defect_classification = '1A'
                description = (
                    f"INTERFACE FAILURE: {instance.interface_type} test at {instance.location_name} "
                    f"({instance.stair.stair_name}) - System did NOT respond as expected"
                )
            else:
                severity = 'medium'
                defect_classification = '2'
                description = (
                    f"INTERFACE TIMING: {instance.interface_type} test at {instance.location_name} "
                    f"({instance.stair.stair_name}) - Response time {response_time_seconds:.1f}s "
                    f"deviates from expected {expected_response_time}s"
                )
            
            fault = Fault(
                fault_id=generate_uuid(),
                test_session_id=instance.session_id,
                instance_id=instance.instance_id,
                building_id=instance.building_id,
                stair_id=instance.stair_id,
                measurement_type='interface_test',
                
                severity=severity,
                defect_classification=defect_classification,
                description=description,
                action_required=(
                    f"Inspect {instance.interface_type} wiring and control logic at {instance.location_name}, "
                    f"verify programming and physical connections"
                ),
                
                rule_applied=rule.rule_code,
                detected_at=datetime.utcnow(),
                status='open',
                
                evidence_ids=actual_data.get('evidence_ids', []),
                technician_notes=actual_data.get('notes'),
                
                metadata={
                    'interface_type': instance.interface_type,
                    'location': instance.location_name,
                    'expected_result': instance.interface_definition.expected_result,
                    'actual_result': actual_data.get('actual_result'),
                    'response_time_seconds': response_time_seconds,
                    'expected_response_time_seconds': expected_response_time
                }
            )
            
            db.session.add(fault)
            db.session.commit()
        
        return ValidationResult(
            instance_id=instance.instance_id,
            is_compliant=is_compliant,
            rule_applied=rule.rule_code,
            fault_id=fault.fault_id if fault else None,
            validation_timestamp=datetime.utcnow()
        )
    
    
    def _get_rule(self, measurement_type: str) -> AS1851Rule:
        """
        Load active AS1851 rule for measurement type.
        """
        rule = AS1851Rule.query.filter_by(
            measurement_type=measurement_type,
            active=True
        ).first()
        
        if not rule:
            raise ValueError(f"No active AS1851 rule found for {measurement_type}")
        
        return rule
    
    
    def _severity_rank(self, severity: str) -> int:
        """
        Rank severity for comparison (higher = worse).
        """
        ranks = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        return ranks.get(severity, 0)


class ValidationResult:
    """
    Result object from instance validation.
    """
    def __init__(
        self,
        instance_id: str,
        is_compliant: bool,
        rule_applied: str,
        validation_timestamp: datetime,
        measured_value: Optional[float] = None,
        baseline_value: Optional[float] = None,
        design_setpoint: Optional[float] = None,
        deviation_from_baseline_pct: Optional[float] = None,
        fault_id: Optional[str] = None,
        fault_ids: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.instance_id = instance_id
        self.is_compliant = is_compliant
        self.measured_value = measured_value
        self.baseline_value = baseline_value
        self.design_setpoint = design_setpoint
        self.deviation_from_baseline_pct = deviation_from_baseline_pct
        self.rule_applied = rule_applied
        self.fault_id = fault_id
        self.fault_ids = fault_ids or []
        self.validation_timestamp = validation_timestamp
        self.metadata = metadata or {}

10. Report Generation: Instance-Level Detail
Report Structure with Instance Preservation


typescript
interface StairPressur izationReport {
  report_id: UUID;
  session_id: UUID;
  building: Building;
  test_date: Date;
  test_frequency:




Retry

AW
Continue





typescript
  test_frequency: Frequency;
  technician: User;
  engineer_reviewer: User | null;
  
  // Executive Summary
  executive_summary: {
    total_instances_tested: number;
    instances_by_type: {
      pressure_differential: number,
      air_velocity: number,
      door_opening_force: number,
      cause_and_effect: number,
      interface_tests: number
    };
    overall_compliance_percentage: number;
    total_faults: number;
    faults_by_severity: {
      critical: number,
      high: number,
      medium: number,
      low: number
    };
    stairs_tested: Stair[];
    floors_tested: Floor[];
  };
  
  // Instance-Level Results Section
  instance_results: {
    by_stair: StairResults[];  // One per stair
  };
  
  // Trend Analysis Section
  trend_analysis: {
    pressure_trends: PressureTrendChart[];  // One per stair × floor × door_config
    velocity_trends: VelocityTrendChart[];  // One per doorway
    door_force_trends: DoorForceTrendChart[];  // One per door
    trend_period_years: number;  // Default 3 years
  };
  
  // Defect Register (Instance-Linked)
  defect_register: {
    faults: Fault[];  // All faults from this session
    by_severity: {
      critical: Fault[],
      high: Fault[],
      medium: Fault[],
      low: Fault[]
    };
    remediation_summary: string;
  };
  
  // Calibration Verification
  calibration_verification: {
    instruments_used: Instrument[];
    all_valid: boolean;
    expired_instruments: Instrument[];  // Should be empty if tests proceeded correctly
  };
  
  // Baseline Comparison Summary
  baseline_comparison: {
    instances_with_significant_deviation: InstanceDeviation[];  // |deviation| > 15%
    degradation_alerts: string[];  // e.g., "Stair-A Floor 8 pressure declining 10% per year"
  };
  
  // Certification & Sign-Off
  certification: {
    engineer_signature: DigitalSignature | null;
    engineer_name: string;
    engineer_license: string;
    certification_date: Date | null;
    certification_statement: string;
    report_finalized: boolean;
    report_immutable_hash: string | null;  // SHA-256 of finalized report
  };
}

interface StairResults {
  stair: Stair;
  
  // Pressure Differential Results (Floor-by-floor table)
  pressure_results: {
    table_data: PressureInstanceResult[];  // One row per floor × door_config
    compliance_percentage: number;
    faults: Fault[];
  };
  
  // Air Velocity Results (Doorway-by-doorway table)
  velocity_results: {
    table_data: VelocityInstanceResult[];  // One row per doorway
    compliance_percentage: number;
    faults: Fault[];
  };
  
  // Door Force Results (Door-by-door table)
  door_force_results: {
    table_data: DoorForceInstanceResult[];  // One row per door
    compliance_percentage: number;
    faults: Fault[];
  };
  
  // C&E Test Results
  ce_results: {
    scenarios_tested: CEInstanceResult[];  // One per zone tested
    overall_pass: boolean;
    faults: Fault[];
  };
  
  // Interface Test Results
  interface_results: {
    tests_performed: InterfaceInstanceResult[];  // One per interface type × location
    compliance_percentage: number;
    faults: Fault[];
  };
}

interface PressureInstanceResult {
  instance_id: UUID;
  floor: Floor;
  door_configuration: string;  // "All Doors Closed" | "Evacuation Doors Open"
  measured_pressure_pa: number;
  design_setpoint_pa: number;
  baseline_pressure_pa: number | null;
  min_threshold_pa: number;
  max_threshold_pa: number;
  is_compliant: boolean;
  deviation_from_baseline_pct: number | null;
  fault_id: UUID | null;
  evidence_ids: UUID[];
  test_timestamp: Date;
}

interface VelocityInstanceResult {
  instance_id: UUID;
  floor: Floor;
  doorway: Doorway;
  measured_velocity_ms: number;  // 9-point grid average
  grid_measurements: GridPoint[];  // All 9 points
  baseline_velocity_ms: number | null;
  min_threshold_ms: number;
  is_compliant: boolean;
  deviation_from_baseline_pct: number | null;
  fault_id: UUID | null;
  evidence_ids: UUID[];
  test_timestamp: Date;
}

interface DoorForceInstanceResult {
  instance_id: UUID;
  floor: Floor;
  door: Door;
  measured_force_n: number;
  baseline_force_n: number | null;
  max_threshold_n: number;
  is_compliant: boolean;
  deviation_from_baseline_pct: number | null;
  fault_id: UUID | null;
  evidence_ids: UUID[];
  test_timestamp: Date;
}

interface CEInstanceResult {
  instance_id: UUID;
  zone: Zone;
  scenario: CEScenario;
  trigger_device: string;
  sequence_results: CEStepResult[];
  overall_pass: boolean;
  max_deviation_seconds: number;
  fault_ids: UUID[];
  evidence_ids: UUID[];
  test_timestamp: Date;
}

interface InterfaceInstanceResult {
  instance_id: UUID;
  interface_type: string;
  location_name: string;
  test_action: string;
  expected_result: string;
  actual_result: string;
  response_time_seconds: number | null;
  is_compliant: boolean;
  fault_id: UUID | null;
  evidence_ids: UUID[];
  test_timestamp: Date;
}

interface InstanceDeviation {
  instance_id: UUID;
  stair: Stair;
  floor: Floor;
  measurement_type: string;
  current_value: number;
  baseline_value: number;
  deviation_pct: number;
  trend_direction: 'improving' | 'stable' | 'degrading';
  alert_level: 'info' | 'warning' | 'critical';
}

Report Template (HTML → PDF via Playwright)


html
<!-- templates/reports/stair_pressurization_report.html -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>AS 1851-2012 Stair Pressurization Test Report</title>
  <style>
    /* Print-optimized styles */
    @page {
      size: A4;
      margin: 20mm;
    }
    
    body {
      font-family: 'Helvetica Neue', Arial, sans-serif;
      font-size: 10pt;
      line-height: 1.4;
      color: #333;
    }
    
    h1 { font-size: 18pt; border-bottom: 3px solid #c00; padding-bottom: 5px; }
    h2 { font-size: 14pt; margin-top: 20px; border-bottom: 1px solid #ccc; }
    h3 { font-size: 12pt; margin-top: 15px; }
    
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0 20px 0;
      font-size: 9pt;
    }
    
    table th {
      background: #f0f0f0;
      border: 1px solid #ccc;
      padding: 6px;
      text-align: left;
      font-weight: bold;
    }
    
    table td {
      border: 1px solid #ccc;
      padding: 6px;
    }
    
    .pass { color: #0a0; font-weight: bold; }
    .fail { color: #c00; font-weight: bold; }
    
    .severity-critical { background-color: #ffcccc; }
    .severity-high { background-color: #ffe6cc; }
    .severity-medium { background-color: #ffffcc; }
    .severity-low { background-color: #e6f7ff; }
    
    .executive-summary {
      background: #f9f9f9;
      border-left: 5px solid #c00;
      padding: 15px;
      margin: 20px 0;
    }
    
    .chart-container {
      page-break-inside: avoid;
      margin: 20px 0;
    }
    
    .page-break {
      page-break-after: always;
    }
    
    .signature-box {
      border: 2px solid #333;
      padding: 20px;
      margin: 30px 0;
      background: #f9f9f9;
    }
    
    .metadata-footer {
      font-size: 8pt;
      color: #666;
      margin-top: 40px;
      border-top: 1px solid #ccc;
      padding-top: 10px;
    }
  </style>
</head>
<body>

<!-- COVER PAGE -->
<div class="page-break">
  <h1>AS 1851-2012 Stair Pressurization System</h1>
  <h2>Routine Service Report</h2>
  
  <table style="margin-top: 40px;">
    <tr>
      <th>Building</th>
      <td>{{ building.name }}</td>
    </tr>
    <tr>
      <th>Address</th>
      <td>{{ building.address }}</td>
    </tr>
    <tr>
      <th>Test Date</th>
      <td>{{ test_date | format_date }}</td>
    </tr>
    <tr>
      <th>Test Frequency</th>
      <td>{{ test_frequency | title }}</td>
    </tr>
    <tr>
      <th>Technician</th>
      <td>{{ technician.name }}</td>
    </tr>
    <tr>
      <th>Report ID</th>
      <td>{{ report_id }}</td>
    </tr>
  </table>
  
  <div style="margin-top: 60px;">
    <p><strong>Compliance Standard:</strong> AS 1851-2012 Routine service of fire protection systems and equipment</p>
    <p><strong>Design Standard:</strong> AS/NZS 1668.1:2015 The use of ventilation and airconditioning in buildings - Fire and smoke control in buildings</p>
  </div>
</div>

<!-- EXECUTIVE SUMMARY -->
<div class="executive-summary">
  <h2>Executive Summary</h2>
  
  <table>
    <tr>
      <th>Total Test Instances</th>
      <td>{{ executive_summary.total_instances_tested }}</td>
    </tr>
    <tr>
      <th>Pressure Differential Tests</th>
      <td>{{ executive_summary.instances_by_type.pressure_differential }}</td>
    </tr>
    <tr>
      <th>Air Velocity Tests</th>
      <td>{{ executive_summary.instances_by_type.air_velocity }}</td>
    </tr>
    <tr>
      <th>Door Force Tests</th>
      <td>{{ executive_summary.instances_by_type.door_opening_force }}</td>
    </tr>
    <tr>
      <th>Cause-and-Effect Tests</th>
      <td>{{ executive_summary.instances_by_type.cause_and_effect }}</td>
    </tr>
    <tr>
      <th>Interface Tests</th>
      <td>{{ executive_summary.instances_by_type.interface_tests }}</td>
    </tr>
    <tr>
      <th><strong>Overall Compliance</strong></th>
      <td><strong>{{ executive_summary.overall_compliance_percentage | round(1) }}%</strong></td>
    </tr>
  </table>
  
  <h3>Defects Summary</h3>
  <table>
    <tr>
      <th>Severity</th>
      <th>Count</th>
    </tr>
    <tr class="severity-critical">
      <td>Critical (1A)</td>
      <td>{{ executive_summary.faults_by_severity.critical }}</td>
    </tr>
    <tr class="severity-high">
      <td>High (1B)</td>
      <td>{{ executive_summary.faults_by_severity.high }}</td>
    </tr>
    <tr class="severity-medium">
      <td>Medium (2)</td>
      <td>{{ executive_summary.faults_by_severity.medium }}</td>
    </tr>
    <tr class="severity-low">
      <td>Low (3)</td>
      <td>{{ executive_summary.faults_by_severity.low }}</td>
    </tr>
    <tr>
      <th>Total Defects</th>
      <th>{{ executive_summary.total_faults }}</th>
    </tr>
  </table>
  
  {% if executive_summary.total_faults > 0 %}
  <p><strong>⚠️ Action Required:</strong> {{ executive_summary.total_faults }} defect(s) require remediation. See Defect Register section for details.</p>
  {% else %}
  <p><strong>✓ System Compliant:</strong> All test instances passed. System operating within design parameters.</p>
  {% endif %}
</div>

<div class="page-break"></div>

<!-- STAIR-BY-STAIR RESULTS -->
{% for stair_result in instance_results.by_stair %}

<h2>{{ stair_result.stair.stair_name }} - Test Results</h2>

<!-- PRESSURE DIFFERENTIAL TABLE -->
<h3>Pressure Differential Results ({{ stair_result.pressure_results.compliance_percentage | round(1) }}% Compliant)</h3>
<table>
  <thead>
    <tr>
      <th>Floor</th>
      <th>Door Config</th>
      <th>Measured (Pa)</th>
      <th>Setpoint (Pa)</th>
      <th>Baseline (Pa)</th>
      <th>Range (Pa)</th>
      <th>Deviation (%)</th>
      <th>Result</th>
      <th>Fault ID</th>
    </tr>
  </thead>
  <tbody>
    {% for result in stair_result.pressure_results.table_data %}
    <tr {% if not result.is_compliant %}class="severity-{{ result.fault.severity }}"{% endif %}>
      <td>{{ result.floor.floor_level }}</td>
      <td>{{ result.door_configuration }}</td>
      <td>{{ result.measured_pressure_pa | round(1) }}</td>
      <td>{{ result.design_setpoint_pa | round(1) }}</td>
      <td>{{ result.baseline_pressure_pa | round(1) if result.baseline_pressure_pa else 'N/A' }}</td>
      <td>{{ result.min_threshold_pa }}-{{ result.max_threshold_pa }}</td>
      <td>{{ result.deviation_from_baseline_pct | round(1) if result.deviation_from_baseline_pct else 'N/A' }}</td>
      <td class="{{ 'pass' if result.is_compliant else 'fail' }}">
        {{ '✓ Pass' if result.is_compliant else '✗ FAIL' }}
      </td>
      <td>{{ result.fault_id[:8] if result.fault_id else '-' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<!-- AIR VELOCITY TABLE -->
<h3>Air Velocity Results ({{ stair_result.velocity_results.compliance_percentage | round(1) }}% Compliant)</h3>
<table>
  <thead>
    <tr>
      <th>Floor</th>
      <th>Doorway</th>
      <th>Avg Velocity (m/s)</th>
      <th>Baseline (m/s)</th>
      <th>Min (m/s)</th>
      <th>Deviation (%)</th>
      <th>Result</th>
      <th>Fault ID</th>
    </tr>
  </thead>
  <tbody>
    {% for result in stair_result.velocity_results.table_data %}
    <tr {% if not result.is_compliant %}class="severity-{{ result.fault.severity }}"{% endif %}>
      <td>{{ result.floor.floor_level }}</td>
      <td>{{ result.doorway.doorway_identifier }}</td>
      <td>{{ result.measured_velocity_ms | round(2) }}</td>
      <td>{{ result.baseline_velocity_ms | round(2) if result.baseline_velocity_ms else 'N/A' }}</td>
      <td>{{ result.min_threshold_ms }}</td>
      <td>{{ result.deviation_from_baseline_pct | round(1) if result.deviation_from_baseline_pct else 'N/A' }}</td>
      <td class="{{ 'pass' if result.is_compliant else 'fail' }}">
        {{ '✓ Pass' if result.is_compliant else '✗ FAIL' }}
      </td>
      <td>{{ result.fault_id[:8] if result.fault_id else '-' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<!-- DOOR FORCE TABLE -->
<h3>Door Opening Force Results ({{ stair_result.door_force_results.compliance_percentage | round(1) }}% Compliant)</h3>
<table>
  <thead>
    <tr>
      <th>Floor</th>
      <th>Door</th>
      <th>Force (N)</th>
      <th>Baseline (N)</th>
      <th>Max (N)</th>
      <th>Deviation (%)</th>
      <th>Result</th>
      <th>Fault ID</th>
    </tr>
  </thead>
  <tbody>
    {% for result in stair_result.door_force_results.table_data %}
    <tr {% if not result.is_compliant %}class="severity-{{ result.fault.severity }}"{% endif %}>
      <td>{{ result.floor.floor_level }}</td>
      <td>{{ result.door.door_identifier }}</td>
      <td>{{ result.measured_force_n | round(1) }}</td>
      <td>{{ result.baseline_force_n | round(1) if result.baseline_force_n else 'N/A' }}</td>
      <td>{{ result.max_threshold_n }}</td>
      <td>{{ result.deviation_from_baseline_pct | round(1) if result.deviation_from_baseline_pct else 'N/A' }}</td>
      <td class="{{ 'pass' if result.is_compliant else 'fail' }}">
        {{ '✓ Pass' if result.is_compliant else '✗ FAIL' }}
      </td>
      <td>{{ result.fault_id[:8] if result.fault_id else '-' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<!-- C&E RESULTS -->
{% if stair_result.ce_results.scenarios_tested | length > 0 %}
<h3>Cause-and-Effect Test Results</h3>
<table>
  <thead>
    <tr>
      <th>Zone</th>
      <th>Scenario</th>
      <th>Trigger Device</th>
      <th>Steps Tested</th>
      <th>Max Deviation (s)</th>
      <th>Result</th>
      <th>Faults</th>
    </tr>
  </thead>
  <tbody>
    {% for result in stair_result.ce_results.scenarios_tested %}
    <tr {% if not result.overall_pass %}class="severity-{{ result.faults[0].severity if result.faults else 'high' }}"{% endif %}>
      <td>{{ result.zone.zone_name }}</td>
      <td>{{ result.scenario.scenario_name }}</td>
      <td>{{ result.trigger_device }}</td>
      <td>{{ result.sequence_results | length }}</td>
      <td>{{ result.max_deviation_seconds | round(1) }}</td>
      <td class="{{ 'pass' if result.overall_pass else 'fail' }}">
        {{ '✓ Pass' if result.overall_pass else '✗ FAIL' }}
      </td>
      <td>{{ result.fault_ids | length }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endif %}

<!-- INTERFACE TEST RESULTS -->
{% if stair_result.interface_results.tests_performed | length > 0 %}
<h3>Interface Test Results ({{ stair_result.interface_results.compliance_percentage | round(1) }}% Compliant)</h3>
<table>
  <thead>
    <tr>
      <th>Interface Type</th>
      <th>Location</th>
      <th>Expected Result</th>
      <th>Actual Result</th>
      <th>Response Time (s)</th>
      <th>Result</th>
      <th>Fault ID</th>
    </tr>
  </thead>
  <tbody>
    {% for result in stair_result.interface_results.tests_performed %}
    <tr {% if not result.is_compliant %}class="severity-{{ result.fault.severity }}"{% endif %}>
      <td>{{ result.interface_type | replace('_', ' ') | title }}</td>
      <td>{{ result.location_name }}</td>
      <td>{{ result.expected_result | truncate(40) }}</td>
      <td>{{ result.actual_result | truncate(40) }}</td>
      <td>{{ result.response_time_seconds | round(1) if result.response_time_seconds else 'N/A' }}</td>
      <td class="{{ 'pass' if result.is_compliant else 'fail' }}">
        {{ '✓ Pass' if result.is_compliant else '✗ FAIL' }}
      </td>
      <td>{{ result.fault_id[:8] if result.fault_id else '-' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endif %}

<div class="page-break"></div>
{% endfor %}

<!-- TREND ANALYSIS -->
<h2>Trend Analysis (3-Year History)</h2>

{% for trend in trend_analysis.pressure_trends %}
<div class="chart-container">
  <h3>{{ trend.stair.stair_name }} - {{ trend.floor.floor_level }} - {{ trend.door_configuration }}</h3>
  <canvas id="chart-pressure-{{ loop.index }}" width="800" height="300"></canvas>
  <script>
    // Chart.js embedded chart (rendered server-side before PDF generation)
    renderPressureTrendChart('chart-pressure-{{ loop.index }}', {{ trend.data | tojson }});
  </script>
  <p><strong>Trend:</strong> {{ trend.trend_direction | title }} - {{ trend.trend_description }}</p>
</div>
{% endfor %}

<div class="page-break"></div>

<!-- DEFECT REGISTER -->
<h2>Defect Register</h2>

{% if defect_register.faults | length > 0 %}
<table>
  <thead>
    <tr>
      <th>Fault ID</th>
      <th>Severity</th>
      <th>Classification</th>
      <th>Location</th>
      <th>Description</th>
      <th>Action Required</th>
    </tr>
  </thead>
  <tbody>
    {% for fault in defect_register.faults %}
    <tr class="severity-{{ fault.severity }}">
      <td>{{ fault.fault_id[:8] }}</td>
      <td>{{ fault.severity | title }}</td>
      <td>{{ fault.defect_classification }}</td>
      <td>
        {{ fault.stair.stair_name if fault.stair else 'N/A' }}<br>
        {{ fault.floor.floor_level if fault.floor else '' }}
      </td>
      <td>{{ fault.description }}</td>
      <td>{{ fault.action_required }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% else %}
<p><strong>✓ No defects detected.</strong> All test instances passed compliance thresholds.</p>
{% endif %}

<div class="page-break"></div>

<!-- CALIBRATION VERIFICATION -->
<h2>Instrument Calibration Verification</h2>

<table>
  <thead>
    <tr>
      <th>Instrument Type</th>
      <th>Serial Number</th>
      <th>Calibration Date</th>
      <th>Expiry Date</th>
      <th>Certificate ID</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    {% for instrument in calibration_verification.instruments_used %}
    <tr {% if instrument.calibration_expired %}class="severity-critical"{% endif %}>
      <td>{{ instrument.instrument_type | title }}</td>
      <td>{{ instrument.serial_number }}</td>
      <td>{{ instrument.calibration_date | format_date }}</td>
      <td>{{ instrument.calibration_expiry | format_date }}</td>
      <td>{{ instrument.calibration_cert_id }}</td>
      <td class="{{ 'pass' if not instrument.calibration_expired else 'fail' }}">
        {{ '✓ Valid' if not instrument.calibration_expired else '✗ EXPIRED' }}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>

{% if not calibration_verification.all_valid %}
<p class="fail"><strong>⚠️ WARNING:</strong> One or more instruments had expired calibration. Measurements taken with expired instruments may not be reliable and should be re-tested.</p>
{% endif %}

<div class="page-break"></div>

<!-- CERTIFICATION & SIGN-OFF -->
<h2>Engineer Certification</h2>

<div class="signature-box">
  {% if certification.report_finalized %}
  <p><strong>I certify that the tests documented in this report were conducted in accordance with AS 1851-2012 requirements for stair pressurization systems.</strong></p>
  
  <table>
    <tr>
      <th>Engineer Name</th>
      <td>{{ certification.engineer_name }}</td>
    </tr>
    <tr>
      <th>License Number</th>
      <td>{{ certification.engineer_license }}</td>
    </tr>
    <tr>
      <th>Signature Date</th>
      <td>{{ certification.certification_date | format_date }}</td>
    </tr>
    <tr>
      <th>Digital Signature</th>
      <td>{{ certification.engineer_signature.hash[:16] }}...</td>
    </tr>
  </table>
  
  <p style="margin-top: 20px;"><em>{{ certification.certification_statement }}</em></p>
  
  {% else %}
  <p><strong>⚠️ DRAFT REPORT - NOT FINALIZED</strong></p>
  <p>This report requires engineer review and digital signature before it can be considered an official compliance document.</p>
  {% endif %}
</div>

<!-- METADATA FOOTER -->
<div class="metadata-footer">
  <p><strong>Report Metadata:</strong></p>
  <p>Report ID: {{ report_id }}</p>
  <p>Generated: {{ generated_timestamp | format_datetime }}</p>
  <p>Test Session ID: {{ session_id }}</p>
  <p>Total Test Instances: {{ executive_summary.total_instances_tested }}</p>
  <p>Instance IDs: Available in audit trail (contact FireMode support for full instance-level data export)</p>
  {% if certification.report_finalized %}
  <p><strong>Immutable Report Hash (SHA-256):</strong> {{ certification.report_immutable_hash }}</p>
  {% endif %}
  <p><em>This report was generated by FireMode Compliance Platform v{{ version }}</em></p>
</div>

</body>
</html>

11. Critical Success Metrics
Compliance Coverage Matrix


12. Final Recommendations
Phase 0: Foundation (Week 0 - Before Implementation)
Baseline Data Collection Sprint
Action: Survey 3-5 pilot customers for existing commissioning reports
Deliverable: CSV templates populated with baseline pressure/velocity/door force data
Acceptance: At least 1 complete building baseline (all stairs × floors × doors × doorways)
Schema Review & Approval
Action: Present proposed data model to Principal Architect + DBA
Deliverable: Approved ERD with sign-off on table structure, indexes, and foreign keys
Acceptance: Zero blocking concerns raised; performance implications documented
Archetype Library Finalization
Action: Review 5 archetype definitions with domain expert (fire engineer)
Deliverable: Confirmed UX prompts, safety warnings, and evidence requirements
Acceptance: Domain expert confirms alignment with AS 1851-2




Retry

AW
Continue



Phase 0: Foundation (Week 0 - Before Implementation) (Continued)
Mobile Offline Strategy Validation
Action: Prototype Realm schema with 200+ instance bundle on test device
Deliverable: Performance benchmark report (bundle size, sync time, battery impact)
Acceptance: Bundle < 50MB, sync < 30s on 4G, battery drain < 5% per hour during testing
PDF Generation Load Testing
Action: Generate 100-page report with 50+ embedded Chart.js trend charts using Playwright
Deliverable: P95 latency < 60s, memory usage < 2GB, no timeout errors
Acceptance: Can generate report for largest pilot building without timeouts

Implementation Priorities (Revised)
Phase 1: Critical Path (Weeks 1-6) - P0

Acceptance Criteria (End of Phase 1):
✅ 1 pilot building fully configured with baseline data (2 stairs, 15 floors)
✅ 60 pressure differential instances generated automatically
✅ Technician can complete 10 pressure instances on mobile offline
✅ Validation creates faults with stair/floor/door-config context
✅ API response includes instance_id, deviation_from_baseline_pct, fault_id

Phase 2: Measurement Type Expansion (Weeks 7-12) - P1

Acceptance Criteria (End of Phase 2):
✅ All 5 measurement types executable on mobile
✅ 1 complete annual test session (158 instances) executed in pilot
✅ Zero instances skipped due to missing baseline data
✅ Faults created with correct severity based on instance context

Phase 3: Reporting & Compliance (Weeks 13-18) - P1

Acceptance Criteria (End of Phase 3):
✅ Generated report includes all 158 instance results in tables
✅ Trend charts render without timeout (< 60s total report generation)
✅ Defect register shows stair/floor/door-config for every fault
✅ Finalized report is immutable (hash verification works)

Phase 4: Scale & Polish (Weeks 19-20) - P2


13. Risk Register
High-Severity Risks

Medium-Severity Risks


14. Success Criteria & KPIs
Compliance Metrics (Primary)

Technical Performance Metrics

User Experience Metrics


15. Test Strategy (Comprehensive)
Unit Tests (Per Component)


typescript
// Example: Instance Generation
describe('PressureDifferentialExpansion', () => {
  it('generates 60 instances for 2 stairs × 15 floors × 2 door configs', async () => {
    const baseline = mockBaseline({ stairs: 2, floors: 15 });
    const instances = await generatePressureInstances(baseline, 'annual');
    expect(instances).toHaveLength(60);
  });
  
  it('throws CardinalityError if baseline floors missing', async () => {
    const baseline = mockBaseline({ stairs: 2, floors: 0 });
    await expect(generatePressureInstances(baseline, 'annual'))
      .rejects.toThrow(CardinalityError);
  });
  
  it('each instance has baseline_value from commissioning data', async () => {
    const baseline = mockBaseline({ stairs: 1, floors: 5 });
    const instances = await generatePressureInstances(baseline, 'annual');
    instances.forEach(instance => {
      expect(instance.baseline_value).toBeGreaterThan(0);
    });
  });
});
Integration Tests (API Contract)


python
# tests/api/test_instance_validation.py

def test_pressure_instance_below_min_creates_critical_fault():
    """Validate that instance with pressure < 20 Pa creates critical fault"""
    # Setup: Create building with baseline
    building = create_test_building(stairs=1, floors=5)
    session = create_test_session(building.id, frequency='annual')
    
    # Generate instances
    instances = generate_test_instances(building.id, 'annual')
    pressure_instance = instances[0]  # First pressure instance
    
    # Execute: Submit result below threshold
    response = client.post(f'/v1/tests/sessions/{session.id}/instances/{pressure_instance.instance_id}/results', json={
        'measured_value_numeric': 18.5,  # Below min 20 Pa
        'evidence_ids': ['ev-123', 'ev-124'],
        'notes': 'Test execution'
    })
    
    # Assert: Validation response
    assert response.status_code == 200
    result = response.json()
    assert result['is_compliant'] == False
    assert result['rule_applied'] == 'SP-01'
    assert result['fault_id'] is not None
    
    # Assert: Fault created with context
    fault = Fault.query.get(result['fault_id'])
    assert fault.severity == 'critical'
    assert fault.defect_classification == '1A'
    assert fault.instance_id == pressure_instance.instance_id
    assert fault.stair_id == pressure_instance.stair_id
    assert fault.floor_id == pressure_instance.floor_id
    assert fault.door_configuration == 'all_closed'
    assert 'below minimum' in fault.description.lower()


def test_velocity_instance_with_9_point_grid():
    """Validate velocity instance stores all 9 grid measurements"""
    building = create_test_building(stairs=1, floors=1)
    session = create_test_session(building.id, frequency='annual')
    instances = generate_test_instances(building.id, 'annual')
    velocity_instance = next(i for i in instances if i.measurement_type == 'air_velocity')
    
    # Submit 9-point grid data
    response = client.post(f'/v1/tests/sessions/{session.id}/instances/{velocity_instance.instance_id}/results', json={
        'measured_value_numeric': 1.15,  # Average
        'grid_measurements': [
            {'point': 1, 'x': 0.25, 'y': 0.8, 'velocity_ms': 1.2},
            {'point': 2, 'x': 0.5, 'y': 0.8, 'velocity_ms': 1.3},
            # ... (all 9 points)
        ],
        'evidence_ids': ['ev-125']
    })
    
    assert response.status_code == 200
    result = response.json()
    assert result['is_compliant'] == True
    
    # Verify stored in database
    instance_result = TestInstance.query.get(velocity_instance.instance_id)
    assert instance_result.measured_value_text is not None
    grid_data = json.loads(instance_result.measured_value_text)
    assert len(grid_data['grid_measurements']) == 9
E2E Tests (Cypress - Web Portal)


typescript
// cypress/e2e/baseline-onboarding.cy.ts

describe('Baseline Onboarding Wizard', () => {
  it('completes full wizard and generates test instances', () => {
    // Login as service manager
    cy.login('service.manager@example.com');
    
    // Navigate to building
    cy.visit('/buildings/test-building-123/stair-config');
    
    // Step A: Design Criteria
    cy.contains('Step A: Design Criteria').click();
    cy.get('input[name="stair_count"]').type('2');
    cy.get('input[name="floor_count"]').type('15');
    cy.get('button').contains('Next').click();
    
    // Step B: Equipment Inventory
    cy.contains('Step B: Equipment Inventory').click();
    cy.get('button').contains('Add Fan').click();
    cy.get('input[name="fan_identifier"]').type('FAN-01');
    cy.get('select[name="stair_id"]').select('Stair-A');
    cy.get('button').contains('Save Fan').click();
    // ... (add more equipment)
    cy.get('button').contains('Next').click();
    
    // Step D: Baseline CSV Upload
    cy.contains('Step D: Commissioning Baseline').click();
    cy.get('input[type="file"]').attachFile('baseline_pressure.csv');
    cy.contains('60 rows validated').should('be.visible');
    cy.get('button').contains('Upload').click();
    cy.contains('Baseline uploaded successfully').should('be.visible');
    
    // Step E: Complete wizard
    cy.get('button').contains('Finalize Configuration').click();
    
    // Verify instance generation
    cy.visit('/buildings/test-building-123/test-instances');
    cy.contains('158 annual test instances generated').should('be.visible');
    
    // Verify session creation blocked without complete baseline
    cy.visit('/buildings/test-building-123/sessions/new');
    cy.get('select[name="frequency"]').select('Annual');
    cy.get('button').contains('Create Session').click();
    cy.contains('Session created').should('be.visible');
  });
});
E2E Tests (Detox - React Native Mobile)


typescript
// e2e/mobile/instance-execution.e2e.ts

describe('Instance Execution Flow', () => {
  beforeAll(async () => {
    await device.launchApp({
      newInstance: true,
      permissions: { camera: 'YES', location: 'always' }
    });
    await login('technician@example.com', 'password');
  });
  
  it('completes pressure differential instance with calibration gate', async () => {
    // Navigate to session
    await element(by.id('sessions-tab')).tap();
    await element(by.text('Annual Test - Building 123')).tap();
    
    // Navigate to first pressure instance
    await element(by.text('Stair-A')).tap();
    await element(by.text('Ground Floor')).tap();
    await element(by.text('Pressure Test - All Doors Closed')).tap();
    
    // Instrument gate
    await expect(element(by.id('instrument-gate'))).toBeVisible();
    await element(by.id('instrument-selector')).tap();
    await element(by.text('Manometer SN-12345')).tap();
    await expect(element(by.text('Calibration valid until: 2025-12-01'))).toBeVisible();
    await element(by.id('confirm-calibration')).tap();
    
    // View instructions
    await expect(element(by.text('Step 1: Close all doors'))).toBeVisible();
    await element(by.id('start-test-button')).tap();
    
    // Wait for stabilization countdown
    await waitFor(element(by.text('30s'))).toBeVisible().withTimeout(2000);
    await waitFor(element(by.text('Measurement window'))).toBeVisible().withTimeout(32000);
    
    // Enter measurement
    await element(by.id('pressure-input')).typeText('43.2');
    await expect(element(by.text('✓ Within range'))).toBeVisible();
    
    // Capture evidence
    await element(by.id('capture-photo-button')).tap();
    await element(by.id('camera-shutter')).tap();
    await element(by.id('use-photo')).tap();
    
    // Complete instance
    await element(by.id('complete-instance-button')).tap();
    await expect(element(by.text('Instance completed'))).toBeVisible();
    
    // Verify progress updated
    await expect(element(by.text('1/60 instances complete'))).toBeVisible();
  });
  
  it('blocks test if instrument calibration expired', async () => {
    // ... (navigate to instance)
    
    await element(by.id('instrument-selector')).tap();
    await element(by.text('Manometer SN-99999')).tap(); // Expired instrument
    await expect(element(by.text('Calibration expired'))).toBeVisible();
    await expect(element(by.id('start-test-button'))).not.toBeVisible();
    await expect(element(by.text('Test cannot proceed'))).toBeVisible();
  });
});
Visual Regression Tests (Playwright - Report PDF)


typescript
// playwright/tests/report-visual-regression.spec.ts

test('stair pressurization report matches baseline snapshot', async ({ page }) => {
  // Generate report
  await page.goto('http://localhost:3000/api/reports/generate?session_id=test-session-123');
  await page.waitForLoadState('networkidle');
  
  // Take full-page screenshot
  await expect(page).toHaveScreenshot('stair-report-full.png', {
    fullPage: true,
    maxDiffPixels: 200  // Allow minor rendering differences
  });
  
  // Specific sections
  await page.locator('h2:has-text("Executive Summary")').scrollIntoViewIfNeeded();
  await expect(page.locator('.executive-summary')).toHaveScreenshot('executive-summary.png');
  
  await page.locator('h3:has-text("Pressure Differential Results")').first().scrollIntoViewIfNeeded();
  await expect(page.locator('table').first()).toHaveScreenshot('pressure-table-stair-a.png');
  
  // Trend chart
  await page.locator('.chart-container').first().scrollIntoViewIfNeeded();
  await expect(page.locator('.chart-container').first()).toHaveScreenshot('trend-chart-pressure.png', {
    maxDiffPixels: 500  // Charts have more variance
  });
});

16. Deployment Strategy
Feature Flags


yaml
# config/feature-flags.yaml
features:
  stair_pressurization_multi_instance:
    enabled: true
    rollout_percentage: 0  # Dark launch - not visible to users yet
    
  stair_baseline_wizard:
    enabled: true
    rollout_percentage: 100
    allowed_organizations: ['pilot-org-1', 'pilot-org-2']  # Pilot customers only
    
  instance_generation_engine:
    enabled: true
    rollout_percentage: 100
    
  mobile_instance_execution:
    enabled: false  # Enable after Week 6
    rollout_percentage: 0
    min_app_version: '4.5.0'
    
  instance_level_reporting:
    enabled: false  # Enable after Week 18
    rollout_percentage: 0
    
  calibration_gate_strict_mode:
    enabled: true
    rollout_percentage: 100
    allow_override: true  # Can override with reason
Rollout Plan

Monitoring & Alerts


yaml
# cloudwatch-alarms.yaml
alarms:
  - name: instance-generation-failure-rate
    metric: api.instance_generation.error_rate
    threshold: 2%
    evaluation_periods: 2
    action: page_on_call_engineer
    
  - name: instance-validation-latency
    metric: api.instance_validation.latency_p95
    threshold: 1000ms
    evaluation_periods: 3
    action: slack_alert_backend_team
    
  - name: mobile-sync-failure-rate
    metric: mobile.realm_sync.failure_rate
    threshold: 5%
    evaluation_periods: 2
    action: page_mobile_lead
    
  - name: report-generation-timeout
    metric: reports.stair_pressurization.timeout_rate
    threshold: 1%
    evaluation_periods: 1
    action: page_on_call_engineer + rollback_feature_flag
    
  - name: calibration-gate-block-rate
    metric: mobile.calibration_gate.block_rate
    threshold: 20%  # If > 20% of tests blocked, may be too strict
    evaluation_periods: 5
    action: slack_alert_product_team

17. Documentation Deliverables
Technical Documentation
Database Schema Documentation (docs/schema/stair-pressurization.md)
ERD diagram with all 20+ new tables
Column descriptions, indexes, foreign keys
Migration scripts with rollback procedures
Archetype Library Reference (docs/archetypes/README.md)
All 5 archetypes with full specifications
Cardinality formulas with examples
UX template structure
API Documentation (docs/api/instance-validation.md)
OpenAPI spec for instance-related endpoints
Request/response examples for all measurement types
Error codes and handling
Mobile Offline Architecture (docs/mobile/offline-sync.md)
Realm schema design
CRDT conflict resolution strategy
Bundle generation and size optimization
User Documentation
Service Manager Guide (docs/users/baseline-onboarding.pdf)
Step-by-step wizard walkthrough with screenshots
CSV template instructions
Troubleshooting common onboarding issues
Technician Field Guide (docs/users/instance-execution-guide.pdf)
How to navigate instance hierarchy (stair → floor → test type)
Instrument calibration gate procedures
Evidence capture best practices
Safety warnings for each test type
Engineer Sign-Off Guide (docs/users/report-review-and-certification.pdf)
How to review instance-level results
Fault remediation workflow
Digital signature process
Training Materials
Video Tutorials
"Baseline Onboarding for Stair Pressurization" (15min)
"Executing Pressure Differential Tests" (5min)
"C&E Sequence Testing on Mobile" (8min)
"Reviewing Instance-Level Reports" (10min)
Quick Reference Cards (Laminated, for technicians)
Pressure test checklist
Velocity 9-point grid diagram
Door force measurement position
C&E test safety warnings

18. Final Audit Summary
Compliance Status: Current Demo vs. AS 1851-2012

Overall Assessment:
Current Demo: ~35% compliant with AS 1851-2012 stair pressurization requirements
Post-Implementation: 95%+ compliant (5% reserved for edge cases and ongoing interpretation)
Risk: Current demo reports would likely be REJECTED by fire safety auditors due to missing instance-level detail

19. Go/No-Go Decision Criteria
Week 6 Checkpoint (End of Phase 1)
GO Criteria:
✅ 1 pilot building onboarded with complete baseline (all stairs, floors, doors, doorways)
✅ 60 pressure differential instances generated automatically
✅ Mobile app can execute 10 pressure instances offline
✅ Validation engine creates faults with full instance context (stair/floor/door-config)
✅ API latency < 500ms P95 for instance validation
✅ Zero blocking bugs in production
NO-GO Criteria (Pause & Reassess):
❌ Baseline completeness < 80% for pilot building (missing too many commissioning records)
❌ Mobile bundle size > 100MB (performance unacceptable)
❌ Sync failure rate > 5%
❌ Technicians reject multi-instance UX (user testing feedback)
❌ Instance generation time > 30s (too slow for large buildings)

Week 12 Checkpoint (End of Phase 2)
GO Criteria:
✅ All 5 measurement types executable on mobile
✅ 1 complete annual test (158 instances) executed successfully
✅ Fault creation rate matches validation rules (critical faults for pressure < 20 Pa, etc.)
✅ Evidence capture rate > 95%
✅ Instance skip rate < 10%
NO-GO Criteria:
❌ Crash rate > 0.5%
❌ Technician completion rate < 85% (too many abandoned sessions)
❌ Calibration gate blocking > 30% of tests (too strict, needs refinement)

Week 18 Checkpoint (End of Phase 3)
GO Criteria:
✅ Report includes all 158 instance results in tables
✅ PDF generation < 60s P95
✅ Trend charts render correctly for 3-year history
✅ Engineer can finalize report with digital signature
✅ Visual regression tests pass (no broken layouts)
NO-GO Criteria:
❌ Report generation timeout rate > 2%
❌ Missing instance data in report (query errors)
❌ Trend chart rendering errors

20. Conclusion & Next Steps
Key Takeaways
The demo is fundamentally non-compliant due to treating stair pressurization as a single-instance test per building, when AS 1851-2012 requires 150-200+ discrete test instances per building per year.
The archetype-driven expansion model is the correct architecture to bridge baseline configuration (one-time) with instance generation (per test session), ensuring full compliance at scale.
Instance-level context preservation is critical - every measurement must link to stair_id, floor_id, door_id/doorway_id, door_configuration, and baseline_value to enable:
Floor-by-floor reporting
Multi-stair differentiation
Trend analysis over time
Fault traceability
Mobile UX is the biggest user risk - technicians must navigate 150+ instances efficiently, with clear visual/audible/




Retry

AW
Continue



Key Takeaways (Continued)
Mobile UX is the biggest user risk - technicians must navigate 150+ instances efficiently, with clear visual/audible/descriptive prompts per instance, without overwhelming them. The hierarchical navigation (Session → Stair → Floor → Test Type → Instance) with progress tracking is essential.
Baseline completeness is a hard gate - without commissioning baseline data for all stairs × floors × doors × doorways, the system cannot generate valid test instances or calculate deviation percentages. Week 0 data collection is critical path.
Performance at scale must be validated early - 100-floor buildings will generate 400+ pressure instances alone. Bundle size, sync time, and report generation must be load-tested in Week 6 before proceeding.

Immediate Next Steps (This Week)
Day 1-2: Stakeholder Alignment
Present this 40,000-ft audit to CEO/CTO for strategic buy-in
Schedule architecture review with Principal Architect + DBA
Confirm resource allocation: 9 FTEs × 20 weeks = 180 person-weeks
Get written approval to pause other feature work if needed
Day 3: Pilot Customer Engagement
Email 5 pilot customers requesting commissioning reports
Provide CSV template for baseline data entry
Schedule Zoom calls to walk through baseline requirements
Target: 1 complete building baseline by end of Week 0
Day 4: Technical Foundation
Clone production database to staging for migration testing
Set up feature flag infrastructure (LaunchDarkly or similar)
Create GitHub feature branch: feature/as1851-stair-pressurization
Initialize Jira epic with 20-week roadmap
Day 5: Week 1 Kickoff Prep
Finalize database schema with DBA (ERD approval)
Write first Alembic migration script (baseline tables)
Set up CloudWatch dashboards for new metrics
Brief entire engineering team on multi-instance architecture

Week 1 Deliverables (Detailed)
Backend Team (3 engineers)
Database Migrations (Lead: Senior Backend Engineer)


bash
   # Priority order
   alembic revision -m "Add stairs registry table"
   alembic revision -m "Add floors registry with stair FK"
   alembic revision -m "Add doors and doorways registry"
   alembic revision -m "Add zones and control equipment"
   alembic revision -m "Add baseline tables (pressure, velocity, door force)"
   alembic revision -m "Add CE scenarios and interface test definitions"
   alembic revision -m "Add test instance templates table"
   alembic revision -m "Add test instances table with full context"
   alembic revision -m "Add evidence records with SHA-256"
   alembic revision -m "Alter faults table - add instance context columns"
   alembic revision -m "Create indexes for instance queries"
Acceptance:
All migrations run successfully on staging clone
Down migrations tested (rollback without data loss)
Indexes confirmed via EXPLAIN ANALYZE on sample queries
Foreign key cascades tested (delete stair → cascades to floors/doors/instances)
AS1851 Rules Seeding (Lead: Mid-level Backend Engineer)


sql
   -- Seed initial rules
   INSERT INTO as1851_rules (rule_code, version, measurement_type, min_threshold, max_threshold, unit, severity_if_fail, defect_classification, active)
   VALUES 
     ('SP-01', 'AS1851-2024-v1.3', 'pressure_differential', 20.0, 80.0, 'Pa', 'critical', '1A', true),
     ('SP-02', 'AS1851-2024-v1.3', 'air_velocity', 1.0, NULL, 'm/s', 'high', '1B', true),
     ('SP-03', 'AS1851-2024-v1.3', 'door_opening_force', NULL, 110.0, 'N', 'critical', '1A', true),
     ('CE-01', 'AS1851-2024-v1.3', 'cause_and_effect_logic', NULL, NULL, NULL, 'critical', '1A', true),
     ('INT-01', 'AS1851-2024-v1.3', 'interface_test', NULL, NULL, NULL, 'critical', '1A', true);
Acceptance:
5 rules seeded with correct thresholds
Rule versioning system works (can activate/deactivate rules)
API endpoint /v1/as1851/rules returns active rules
Baseline Data Import API (Lead: Junior Backend Engineer)


python
   # POST /v1/buildings/{building_id}/baseline/pressure/bulk
   # CSV format: stair_id, floor_id, door_configuration, pressure_pa, commissioned_date
   
   @router.post("/buildings/{building_id}/baseline/pressure/bulk")
   async def bulk_import_pressure_baseline(
       building_id: str,
       file: UploadFile = File(...),
       db: Session = Depends(get_db)
   ):
       # Parse CSV
       df = pd.read_csv(file.file)
       
       # Validate schema
       required_columns = ['stair_id', 'floor_id', 'door_configuration', 'pressure_pa', 'commissioned_date']
       missing = [col for col in required_columns if col not in df.columns]
       if missing:
           raise HTTPException(400, f"Missing columns: {missing}")
       
       # Validate data ranges
       errors = []
       for idx, row in df.iterrows():
           if row['pressure_pa'] < 10 or row['pressure_pa'] > 100:
               errors.append(f"Row {idx+2}: Pressure {row['pressure_pa']} out of reasonable range")
       
       if errors:
           return {"success": False, "errors": errors}
       
       # Bulk upsert
       for _, row in df.iterrows():
           baseline = BaselinePressureDifferential(
               building_id=building_id,
               stair_id=row['stair_id'],
               floor_id=row['floor_id'],
               door_configuration=row['door_configuration'],
               pressure_pa=row['pressure_pa'],
               commissioned_date=row['commissioned_date']
           )
           db.merge(baseline)  # Upsert
       
       db.commit()
       return {"success": True, "rows_imported": len(df)}
Acceptance:
API accepts CSV with 100+ rows
Validation catches malformed data
Duplicate rows trigger upsert (not duplicate key error)
Similar endpoints for velocity and door force baseline

Frontend Team (2 engineers)
Baseline Wizard - Step A: Design Criteria (Lead: Senior Frontend Engineer)


typescript
   // app/buildings/[id]/stair-config/page.tsx
   
   export default function StairConfigWizard() {
     const [step, setStep] = useState('A');
     const [formData, setFormData] = useState({
       stairs: [],
       floors: [],
       floor_pressure_setpoints: {}
     });
     
     return (
       <WizardContainer>
         <WizardProgress currentStep={step} totalSteps={5} />
         
         {step === 'A' && (
           <StepA_DesignCriteria
             data={formData}
             onNext={(data) => {
               setFormData({...formData, ...data});
               setStep('B');
             }}
           />
         )}
         
         {/* Steps B-E... */}
       </WizardContainer>
     );
   }
   
   function StepA_DesignCriteria({ data, onNext }) {
     const [stairs, setStairs] = useState(data.stairs || []);
     const [floors, setFloors] = useState(data.floors || []);
     const [setpoints, setSetpoints] = useState(data.floor_pressure_setpoints || {});
     
     const handleAddStair = () => {
       setStairs([...stairs, {
         stair_name: '',
         orientation: '',
         stair_type: 'pressurized'
       }]);
     };
     
     const handleSetpointChange = (stairId, floorId, value) => {
       setSetpoints({
         ...setpoints,
         [`${stairId}_${floorId}`]: parseFloat(value)
       });
     };
     
     return (
       <div>
         <h2>Step A: Design Criteria</h2>
         
         {/* Stairs input */}
         <section>
           <h3>Stairs</h3>
           <Button onClick={handleAddStair}>Add Stair</Button>
           {stairs.map((stair, idx) => (
             <div key={idx}>
               <Input
                 label="Stair Name"
                 value={stair.stair_name}
                 onChange={(e) => {
                   const updated = [...stairs];
                   updated[idx].stair_name = e.target.value;
                   setStairs(updated);
                 }}
               />
               <Select
                 label="Orientation"
                 value={stair.orientation}
                 options={['North', 'South', 'East', 'West', 'Central']}
                 onChange={(value) => {
                   const updated = [...stairs];
                   updated[idx].orientation = value;
                   setStairs(updated);
                 }}
               />
             </div>
           ))}
         </section>
         
         {/* Floors input */}
         <section>
           <h3>Floors</h3>
           <Button onClick={() => {
             const floorCount = prompt("How many floors?");
             const generated = [];
             for (let i = 0; i < parseInt(floorCount); i++) {
               generated.push({
                 floor_level: i === 0 ? 'Ground' : `Level-${i}`,
                 floor_number: i
               });
             }
             setFloors(generated);
           }}>
             Generate Floors
           </Button>
           <ul>
             {floors.map(floor => <li key={floor.floor_number}>{floor.floor_level}</li>)}
           </ul>
         </section>
         
         {/* Pressure setpoints table */}
         <section>
           <h3>Design Pressure Setpoints (Pa)</h3>
           <table>
             <thead>
               <tr>
                 <th>Stair</th>
                 <th>Floor</th>
                 <th>Target Pressure (Pa)</th>
               </tr>
             </thead>
             <tbody>
               {stairs.flatMap(stair => 
                 floors.map(floor => (
                   <tr key={`${stair.stair_name}_${floor.floor_level}`}>
                     <td>{stair.stair_name}</td>
                     <td>{floor.floor_level}</td>
                     <td>
                       <Input
                         type="number"
                         min={20}
                         max={80}
                         value={setpoints[`${stair.stair_name}_${floor.floor_level}`] || 45}
                         onChange={(e) => handleSetpointChange(stair.stair_name, floor.floor_level, e.target.value)}
                       />
                     </td>
                   </tr>
                 ))
               )}
             </tbody>
           </table>
         </section>
         
         <Button onClick={() => onNext({ stairs, floors, floor_pressure_setpoints: setpoints })}>
           Next: Equipment Inventory
         </Button>
       </div>
     );
   }
Acceptance:
Can add 2+ stairs with names and orientations
Can generate 15+ floors
Setpoint table renders all stair × floor combinations
Validation: setpoints must be 20-80 Pa
Form state persists in localStorage (auto-save every 30s)
Baseline Wizard - Step D: CSV Upload (Lead: Mid-level Frontend Engineer)


typescript
   function StepD_CommissioningBaseline({ buildingId, onNext }) {
     const [file, setFile] = useState(null);
     const [validationResult, setValidationResult] = useState(null);
     const [uploading, setUploading] = useState(false);
     
     const handleFileChange = (e) => {
       setFile(e.target.files[0]);
     };
     
     const handleUpload = async () => {
       setUploading(true);
       
       const formData = new FormData();
       formData.append('file', file);
       
       try {
         const response = await fetch(`/api/v1/buildings/${buildingId}/baseline/pressure/bulk`, {
           method: 'POST',
           body: formData
         });
         
         const result = await response.json();
         setValidationResult(result);
         
         if (result.success) {
           toast.success(`${result.rows_imported} baseline records uploaded`);
         } else {
           toast.error(`Validation errors: ${result.errors.length}`);
         }
       } catch (error) {
         toast.error('Upload failed: ' + error.message);
       } finally {
         setUploading(false);
       }
     };
     
     return (
       <div>
         <h2>Step D: Commissioning Baseline</h2>
         
         <section>
           <h3>Pressure Differential Baseline</h3>
           <p>Upload CSV with commissioning pressure data for all stairs, floors, and door configurations.</p>
           
           <a href="/templates/baseline_pressure_template.csv" download>
             Download CSV Template
           </a>
           
           <Input
             type="file"
             accept=".csv"
             onChange={handleFileChange}
           />
           
           <Button onClick={handleUpload} disabled={!file || uploading}>
             {uploading ? 'Uploading...' : 'Upload & Validate'}
           </Button>
           
           {validationResult && (
             <ValidationResult result={validationResult} />
           )}
         </section>
         
         {/* Similar sections for velocity and door force */}
         
         <Button onClick={onNext} disabled={!validationResult?.success}>
           Next: Calibration Certificates
         </Button>
       </div>
     );
   }
   
   function ValidationResult({ result }) {
     if (result.success) {
       return (
         <Alert type="success">
           ✓ {result.rows_imported} rows validated and uploaded successfully
         </Alert>
       );
     }
     
     return (
       <Alert type="error">
         <p>Validation errors detected:</p>
         <ul>
           {result.errors.slice(0, 10).map((error, idx) => (
             <li key={idx}>{error}</li>
           ))}
         </ul>
         {result.errors.length > 10 && (
           <p>... and {result.errors.length - 10} more errors</p>
         )}
       </Alert>
     );
   }
Acceptance:
CSV template downloads correctly
Can upload 100+ row CSV
Validation errors displayed clearly
Success message shows row count
Cannot proceed to next step if validation fails

QA Team (1 engineer)
Migration Testing Suite


python
   # tests/migrations/test_stair_baseline_migration.py
   
   def test_migration_up_creates_all_tables():
       """Verify all new tables created"""
       alembic.upgrade('head')
       
       inspector = inspect(engine)
       tables = inspector.get_table_names()
       
       assert 'stairs' in tables
       assert 'floors' in tables
       assert 'doors' in tables
       assert 'doorways' in tables
       assert 'zones' in tables
       assert 'control_equipment' in tables
       assert 'baseline_pressure_differentials' in tables
       assert 'baseline_air_velocities' in tables
       assert 'baseline_door_forces' in tables
       assert 'ce_scenarios' in tables
       assert 'interface_test_definitions' in tables
       assert 'test_instance_templates' in tables
       assert 'test_instances' in tables
       assert 'evidence_records' in tables
   
   def test_migration_down_preserves_data():
       """Verify rollback doesn't lose data"""
       # Insert test data
       insert_test_stairs(count=2)
       insert_test_floors(count=15)
       
       stair_count_before = count_rows('stairs')
       floor_count_before = count_rows('floors')
       
       # Downgrade
       alembic.downgrade('-1')
       
       # Check archived tables exist
       inspector = inspect(engine)
       assert 'stairs_archived' in inspector.get_table_names()
       
       # Verify data preserved in archive
       stair_count_archived = count_rows('stairs_archived')
       assert stair_count_archived == stair_count_before
   
   def test_foreign_key_cascades():
       """Verify cascading deletes work"""
       stair = insert_test_stair(name='Test-Stair')
       floor = insert_test_floor(stair_id=stair.id, level='Ground')
       instance = insert_test_instance(stair_id=stair.id, floor_id=floor.id)
       
       # Delete stair
       db.session.delete(stair)
       db.session.commit()
       
       # Verify cascade
       assert TestInstance.query.get(instance.id) is None  # Should be deleted
       assert Floor.query.get(floor.id) is None  # Should be deleted
   
   def test_index_performance():
       """Verify indexes improve query performance"""
       # Insert 1000 test instances
       insert_bulk_test_instances(count=1000)
       
       # Query without index (simulate)
       start = time.time()
       result = db.session.execute(
           "SELECT * FROM test_instances WHERE stair_id = 'test-stair' AND floor_id = 'test-floor'"
       ).fetchall()
       duration_no_index = time.time() - start
       
       # Create index
       db.session.execute("CREATE INDEX idx_test ON test_instances(stair_id, floor_id)")
       
       # Query with index
       start = time.time()
       result = db.session.execute(
           "SELECT * FROM test_instances WHERE stair_id = 'test-stair' AND floor_id = 'test-floor'"
       ).fetchall()
       duration_with_index = time.time() - start
       
       # Should be at least 5x faster
       assert duration_with_index < duration_no_index / 5
Acceptance:
All migration tests pass
Rollback tests pass (zero data loss)
Foreign key cascade tests pass
Index performance improvement verified

DevOps Team (1 engineer)
Staging Environment Setup


bash
   # Clone production database to staging
   aws rds create-db-snapshot \
     --db-instance-identifier firemode-prod \
     --db-snapshot-identifier firemode-prod-snapshot-2025-10-20
   
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier firemode-staging-stair \
     --db-snapshot-identifier firemode-prod-snapshot-2025-10-20
   
   # Run migrations on staging
   kubectl exec -it firemode-api-staging -- alembic upgrade head
   
   # Verify data integrity
   psql -h firemode-staging-stair.xxx.rds.amazonaws.com -U admin -d firemode \
     -c "SELECT COUNT(*) FROM buildings;" \
     -c "SELECT COUNT(*) FROM test_sessions;" \
     -c "SELECT COUNT(*) FROM measurements;"
Feature Flag Infrastructure


yaml
   # kubernetes/configmap-feature-flags.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: feature-flags
   data:
     flags.yaml: |
       stair_pressurization_multi_instance:
         enabled: true
         rollout_percentage: 0
       stair_baseline_wizard:
         enabled: true
         rollout_percentage: 100
         allowed_organizations:
           - pilot-org-1
           - pilot-org-2
Monitoring Dashboards


javascript
   // cloudwatch-dashboard.json
   {
     "widgets": [
       {
         "type": "metric",
         "properties": {
           "metrics": [
             ["FireMode/API", "instance_generation.duration", {"stat": "Average"}],
             ["...", {"stat": "p95"}]
           ],
           "period": 300,
           "stat": "Average",
           "region": "us-east-1",
           "title": "Instance Generation Time"
         }
       },
       {
         "type": "metric",
         "properties": {
           "metrics": [
             ["FireMode/API", "instance_validation.error_rate"],
             [".", "instance_validation.latency", {"stat": "p95"}]
           ],
           "title": "Instance Validation Performance"
         }
       }
     ]
   }

Success Metrics for Week 1


Communication Plan
Weekly Stakeholder Updates (Every Friday)
Email to CEO/CTO/VP Engineering with:
Milestones achieved this week
Blockers encountered and resolution
Next week's deliverables
Risk register updates
Daily Standups (9am AU time)
15-minute sync across all teams
Focus: blockers, dependencies, coordination
Pilot Customer Check-ins (Bi-weekly)
Demo latest features
Collect feedback on UX
Validate baseline data quality

Final Recommendation
GO DECISION: Proceed with implementation starting Week 1
Rationale:
The compliance gap is severe (35% → 95%) and represents significant audit risk
The multi-instance architecture is sound and aligns with AS 1851-2012 requirements
Resource allocation (9 FTEs × 20 weeks) is justified given the scope
Phased rollout with feature flags mitigates deployment risk
Pilot customers committed to providing baseline data
Contingency:
If Week 6 checkpoint fails (mobile UX rejected or performance issues), pivot to:
Option A: Simplified instance navigation (auto-advance through instances)
Option B: Defer mobile app, execute tests via web portal on tablets
Option C: Extend timeline by 4 weeks for UX refinement
Executive Approval Required:
CEO sign-off on resource allocation
CFO approval for infrastructure cost increase ($500/month estimated)
VP Engineering commitment to pause lower-priority features
Let's build a compliant, scalable, and auditable stair pressurization system. I'm ready to start generating the first Alembic migration script when you give the word.
