<!-- cb748dc3-8b3f-443c-8074-565a26efd869 3695637a-ecea-4e5a-b1a9-81b6d20c0fef -->
# Weeks 5-8 Implementation Plan: FireAI MVP Completion

## Overview

Complete the FireAI compliance platform MVP by implementing:

- **Week 5**: Mobile C&E (Cause-and-Effect) test execution with offline capability
- **Week 6**: Interface testing module (4 test types per AS 1851-2012)
- **Week 7**: Enhanced report generation with 3-year trends and analytics
- **Week 8**: Engineer sign-off workflow with digital signatures and compliance dashboard

**Architecture Decisions**:

- Mobile app: `/packages/mobile` (bare React Native, Realm, Automerge)
- C&E endpoints: New `/v1/ce-tests` API (separate from workflow designer)
- Notifications: AWS SES (email), Twilio (SMS), Firebase (push)
- Execution: Week 5 only, with complete roadmap for weeks 6-8

---

## WEEK 5: Mobile C&E Test Execution (EXECUTE THIS WEEK)

### Backend: C&E Test API Endpoints

**New Files to Create**:

1. **Database Migration**: `alembic/versions/006_add_ce_test_tables.py`

   - `ce_test_sessions` table (master records for C&E tests)
   - `ce_test_steps` table (individual step execution records)
   - `ce_test_deviations` table (timing/sequence deviations)
   - `ce_test_results` table (pass/fail outcomes)
   - Indexes on session_id, building_id, status, severity

2. **Models**: `src/app/models/ce_test.py`

   - `CETestSession` model (links to test_sessions, buildings)
   - `CETestStep` model (step execution with timing)
   - `CETestDeviation` model (deviation analysis)
   - `CETestResult` model (aggregated results)
   - Relationships to Evidence, Defects, ComplianceWorkflow

3. **Schemas**: `src/app/schemas/ce_test.py`

   - `CEScenarioRead` (expected sequence from workflow)
   - `CETestStepCreate` (record actual step execution)
   - `CETestStepRead` (step with timing data)
   - `CETestDeviationRead` (deviation analysis)
   - `CETestResultCreate` (submit complete test)
   - `CETestResultRead` (pass/fail with deviations)

4. **Router**: `src/app/routers/ce_tests.py`

   - `GET /v1/ce-tests/scenarios/{workflow_id}` - Download C&E scenario for offline
   - `POST /v1/ce-tests/sessions` - Create C&E test session
   - `POST /v1/ce-tests/sessions/{id}/steps` - Record step execution
   - `POST /v1/ce-tests/sessions/{id}/complete` - Submit results with CRDT
   - `GET /v1/ce-tests/sessions/{id}` - Get test session details
   - `GET /v1/ce-tests/sessions/{id}/deviations` - Get deviation analysis

5. **Service**: `src/app/services/ce_deviation_analyzer.py`

   - `analyze_sequence(expected, actual)` - Compare sequences
   - `calculate_timing_deviation(expected_time, actual_time)` - Timing analysis
   - `classify_severity(deviation_seconds)` - AS 1851-2012 classification
     - Critical (1A): Component failed to activate
     - High (1B): Delay >10 seconds
     - Medium (2): Delay 5-10 seconds
     - Low (3): Delay 2-5 seconds
   - `generate_fault_from_deviation(deviation)` - Auto-create defects
   - `merge_crdt_results(results_list)` - Conflict resolution

6. **Tests**: `tests/unit/test_ce_tests.py`

   - Test scenario download
   - Test step recording
   - Test deviation analysis
   - Test CRDT merge logic
   - Test fault generation

### Mobile: React Native C&E Test Runner

**New Directory Structure**: `/packages/mobile/`

```
packages/mobile/
├── package.json (React Native 0.74+, TypeScript)
├── metro.config.js
├── babel.config.js
├── tsconfig.json
├── ios/ (bare workflow)
├── android/ (bare workflow)
└── src/
    ├── screens/
    │   ├── CETestExecutionScreen.tsx (main container)
    │   ├── CETestListScreen.tsx (available tests)
    │   └── CETestResultsScreen.tsx (review before submit)
    ├── components/
    │   ├── StepTimer.tsx (countdown/elapsed time)
    │   ├── SequenceRecorder.tsx (record actual events)
    │   ├── DeviationDetector.tsx (real-time comparison)
    │   └── EvidenceCapture.tsx (photo per step)
    ├── services/
    │   ├── CETestSyncService.ts (CRDT sync manager)
    │   ├── OfflineStorageService.ts (Realm DB)
    │   └── BackgroundTimerService.ts (accurate timing)
    ├── realm/
    │   └── schemas.ts (Realm schemas for offline data)
    ├── crdt/
    │   ├── CETestDocument.ts (Automerge document)
    │   └── conflictResolution.ts (merge logic)
    └── utils/
        ├── timeSync.ts (clock skew compensation)
        └── evidenceAttestation.ts (device attestation)
```

**Key Files to Create**:

1. **Realm Schemas**: `packages/mobile/src/realm/schemas.ts`

   - `CEScenarioSchema` (offline scenario storage)
   - `CETestSessionSchema` (test execution state)
   - `CETestStepSchema` (step records with timing)
   - `SyncQueueSchema` (pending uploads)

2. **CRDT Document**: `packages/mobile/src/crdt/CETestDocument.ts`

   - Automerge document structure for C&E tests
   - Vector clock for timing synchronization
   - Conflict-free step recording
   - Evidence association

3. **Main Screen**: `packages/mobile/src/screens/CETestExecutionScreen.tsx`

   - Step-by-step wizard UI
   - Timer display (countdown/elapsed)
   - Real-time deviation detection
   - Evidence capture per step
   - Offline-first state management
   - Resume partial completion

4. **Sync Service**: `packages/mobile/src/services/CETestSyncService.ts`

   - Queue management for offline results
   - CRDT merge before upload
   - Retry logic with exponential backoff
   - Evidence upload with attestation
   - Conflict resolution

5. **Background Timer**: `packages/mobile/src/services/BackgroundTimerService.ts`

   - Accurate timing even when app backgrounds
   - React Native background task integration
   - Persist timing data to Realm

6. **Tests**: `packages/mobile/__tests__/`

   - Component tests with React Native Testing Library
   - Sync service tests
   - CRDT merge tests
   - Timer accuracy tests

### Integration & Testing

**Files to Create**:

1. **E2E Test**: `tests/integration/test_ce_tests_e2e.py`

   - Download scenario → Execute steps → Submit results → Verify deviations → Check fault generation

2. **CRDT Test**: `tests/integration/test_ce_crdt_sync.py`

   - Simulate multiple technicians testing same system
   - Verify conflict-free merge
   - Validate timing reconciliation

3. **Performance Test**: `tests/load/test_ce_performance.py`

   - 100+ concurrent C&E test submissions
   - CRDT merge performance
   - Deviation analysis latency

### Dependencies to Add

**Backend** (`pyproject.toml`):

```toml
scipy = "^1.11.0"  # Statistical analysis for deviations
numpy = "^1.24.0"  # Numerical operations
```

**Mobile** (`packages/mobile/package.json`):

```json
{
  "dependencies": {
    "react-native": "0.74.0",
    "@realm/react": "^0.6.0",
    "automerge": "^2.1.0",
    "react-native-camera": "^4.2.1",
    "react-native-background-timer": "^2.4.1",
    "@react-native-async-storage/async-storage": "^1.21.0"
  }
}
```

### Success Metrics (Week 5)

- ✅ C&E tests executable offline with <2% sync conflicts
- ✅ Deviation detection within 100ms of step completion
- ✅ Automatic fault generation for deviations >2 seconds
- ✅ Background timing accurate to ±500ms
- ✅ Evidence properly linked to deviation points

---

## WEEK 6: Interface Testing Module (PLAN ONLY)

### Backend: Interface Test API

**Files to Create**:

1. **Migration**: `alembic/versions/007_add_interface_test_tables.py`

   - `interface_test_sessions`, `interface_test_steps`, `interface_test_results`, `interface_test_evidence`

2. **Models**: `src/app/models/interface_test.py`

   - Support 4 test types: manual_override, alarm_coordination, shutdown_sequence, sprinkler_interface

3. **Router**: `src/app/routers/interface_tests.py`

   - `POST /v1/interface-tests/sessions`, `POST /v1/interface-tests/{id}/steps`, `POST /v1/interface-tests/{id}/complete`, `GET /v1/interface-tests/templates`

4. **Service**: `src/app/services/interface_test_validator.py`

   - Timing validation per AS 1851-2012
   - Manual override: <3s, Alarm coordination: <10s

### Frontend: React Interface Test Manager

**Files to Create**:

1. **Components**: `packages/ui/src/organisms/InterfaceTestDashboard.tsx`

   - Test type selector (4 cards)
   - Step executor with timer
   - Evidence uploader
   - Results summary

2. **Hooks**: `packages/ui/src/hooks/useInterfaceTest.ts`

   - API integration for interface tests

### Success Metrics (Week 6)

- ✅ All 4 interface test types implemented
- ✅ Evidence required per test type
- ✅ Timing validation per AS 1851-2012
- ✅ Auto-fault generation for failures

---

## WEEK 7: Report Generation & Trending (PLAN ONLY)

### Backend: Enhanced PDF Reports

**Files to Create**:

1. **Service**: `src/app/services/report_generator_v2.py`

   - Chart generation with matplotlib
   - 3-year trend queries
   - C&E results section
   - Calibration verification table
   - Engineer compliance statement

2. **Service**: `src/app/services/trend_analyzer.py`

   - Time series analysis (Prophet/ARIMA)
   - Degradation pattern detection
   - Predictive maintenance recommendations
   - Statistical significance testing

3. **Router**: `src/app/routers/reports.py`

   - `POST /v1/reports/generate`, `GET /v1/reports/{id}/trends`, `GET /v1/reports/{id}/download`

4. **SQL Queries**: `src/app/queries/trend_analysis.sql`

   - 3-year pressure differential aggregation
   - Air velocity trends per doorway
   - Door force trends per door
   - C&E test history rollup

### Dependencies to Add

```toml
prophet = "^1.1.0"  # Time series forecasting
matplotlib = "^3.8.0"  # Chart generation
reportlab = "^4.0.0"  # PDF generation
```

### Success Metrics (Week 7)

- ✅ Reports include 3-year trends with charts
- ✅ Predictive insights for maintenance
- ✅ C&E results section complete
- ✅ PDF generation <10s for 3-year data

---

## WEEK 8: Engineer Sign-off & Compliance (PLAN ONLY)

### Backend: Sign-off Workflow

**Files to Create**:

1. **Migration**: `alembic/versions/008_add_engineer_signoff_tables.py`

   - `engineer_licenses`, `report_signatures`, `compliance_statements`

2. **Router**: `src/app/routers/engineer_signoff.py`

   - `POST /v1/reports/{id}/engineer-review`, `POST /v1/reports/{id}/sign`, `POST /v1/reports/{id}/finalize`, `GET /v1/engineers/verify-license`

3. **Service**: `src/app/services/notification_service.py`

   - SQS/RabbitMQ queue
   - Email (AWS SES), SMS (Twilio), Push (Firebase)
   - 24-hour escalation logic
   - Delivery tracking

4. **Service**: `src/app/services/escalation_engine.py`

   - T+0: Building owner, T+1h: Service manager, T+4h: Regional manager, T+24h: Compliance officer

### Frontend: Compliance Dashboard

**Files to Create**:

1. **Dashboard**: `packages/ui/src/organisms/ComplianceDashboard.tsx`

   - Portfolio overview (all buildings)
   - Compliance heatmap
   - Critical defect alerts
   - Trend sparklines
   - Calendar view for scheduling

2. **Components**: `packages/ui/src/organisms/EngineerSignoffPanel.tsx`

   - Digital signature pad
   - Compliance statement editor
   - License verification
   - Finalization confirmation

### Dependencies to Add

**Backend**:

```toml
twilio = "^8.10.0"  # SMS notifications
firebase-admin = "^6.3.0"  # Push notifications
celery = "^5.3.0"  # Background task queue
```

**Frontend**:

```json
{
  "dependencies": {
    "signature_pad": "^4.1.0",
    "d3": "^7.9.0",
    "react-calendar": "^4.6.0"
  }
}
```

### Success Metrics (Week 8)

- ✅ 100% critical defects notified within 1 hour
- ✅ Digital signatures legally binding
- ✅ License verification against registry
- ✅ Dashboard supports 1000+ buildings

---

## High-Impact Rules Compliance

Following `.cursor/rules/high-impact.mdc`:

- **30-75 LOC changes**: Each file kept under 500 LOC, split into focused modules
- **Plan → Implement → Test**: This plan covers all phases
- **CI Gates**: All new code will pass lint, typecheck, unit, integration, security
- **Security**: No hardcoded secrets, parameterized queries, input validation
- **i18n & a11y**: WCAG 2.2 AA compliance for all UI components
- **Documentation**: ADRs for architectural decisions, API docs for all endpoints

---

## Risk Mitigation

1. **Mobile Development Complexity**: Start with iOS only, add Android after validation
2. **CRDT Sync Conflicts**: Extensive testing with simulated concurrent users
3. **Background Timer Accuracy**: Fallback to server-side timing if mobile unreliable
4. **Report Generation Performance**: Implement caching for expensive trend calculations
5. **Notification Delivery**: Retry logic with exponential backoff, delivery confirmation

---

## Dependencies Between Weeks

- Week 6 depends on Week 5: Interface tests reference C&E deviation patterns
- Week 7 depends on Weeks 5-6: Reports include C&E and interface test results
- Week 8 depends on Week 7: Sign-off requires complete reports with trends

---

## Estimated Effort

- **Week 5**: 40-50 hours (mobile + backend + CRDT sync)
- **Week 6**: 25-30 hours (4 interface test types + UI)
- **Week 7**: 30-35 hours (trend analysis + chart generation)
- **Week 8**: 35-40 hours (notification system + dashboard)

**Total**: 130-155 hours over 4 weeks

### To-dos

- [ ] Create database migration 006_add_ce_test_tables.py with ce_test_sessions, ce_test_steps, ce_test_deviations, ce_test_results tables
- [ ] Create src/app/models/ce_test.py with CETestSession, CETestStep, CETestDeviation, CETestResult models and relationships
- [ ] Create src/app/schemas/ce_test.py with all Pydantic schemas for C&E test API
- [ ] Create src/app/routers/ce_tests.py with 6 endpoints for C&E test execution and results
- [ ] Create src/app/services/ce_deviation_analyzer.py with sequence comparison, timing analysis, severity classification, and fault generation
- [ ] Create tests/unit/test_ce_tests.py with comprehensive unit tests for C&E test API
- [ ] Initialize React Native bare workflow in packages/mobile/ with TypeScript, Realm, Automerge dependencies
- [ ] Create packages/mobile/src/realm/schemas.ts with Realm schemas for offline C&E test data
- [ ] Create packages/mobile/src/crdt/CETestDocument.ts with Automerge document structure and conflict resolution
- [ ] Create CETestExecutionScreen.tsx with step-by-step wizard, timer, deviation detection, and evidence capture
- [ ] Create StepTimer, SequenceRecorder, DeviationDetector, and EvidenceCapture components
- [ ] Create CETestSyncService.ts with queue management, CRDT merge, retry logic, and evidence upload
- [ ] Create BackgroundTimerService.ts for accurate timing even when app backgrounds
- [ ] Create React Native component tests and sync service tests
- [ ] Create tests/integration/test_ce_tests_e2e.py for end-to-end C&E test workflow
- [ ] Create tests/integration/test_ce_crdt_sync.py for multi-user CRDT conflict resolution
- [ ] Create tests/load/test_ce_performance.py for concurrent C&E test submissions
- [ ] Add scipy, numpy to pyproject.toml and React Native dependencies to mobile package.json
- [ ] Create ADR for C&E test architecture and API documentation
- [ ] Create migration 007_add_interface_test_tables.py for 4 interface test types
- [ ] Create src/app/models/interface_test.py with models for manual_override, alarm_coordination, shutdown_sequence, sprinkler_interface
- [ ] Create src/app/routers/interface_tests.py with endpoints for interface test execution
- [ ] Create src/app/services/interface_test_validator.py with AS 1851-2012 timing validation
- [ ] Create packages/ui/src/organisms/InterfaceTestDashboard.tsx with test type selector and step executor
- [ ] Create unit and integration tests for interface testing module
- [ ] Create src/app/services/report_generator_v2.py with chart generation and 3-year trend queries
- [ ] Create src/app/services/trend_analyzer.py with time series analysis and predictive maintenance
- [ ] Create src/app/routers/reports.py with endpoints for report generation and trend analysis
- [ ] Create src/app/queries/trend_analysis.sql with 3-year aggregation queries
- [ ] Add prophet, matplotlib, reportlab to pyproject.toml
- [ ] Create tests for report generation and trend analysis
- [ ] Create migration 008_add_engineer_signoff_tables.py for licenses, signatures, statements
- [ ] Create src/app/routers/engineer_signoff.py with review, sign, finalize, verify-license endpoints
- [ ] Create src/app/services/notification_service.py with SQS queue, email/SMS/push handlers
- [ ] Create src/app/services/escalation_engine.py with 24-hour escalation logic
- [ ] Create packages/ui/src/organisms/ComplianceDashboard.tsx with portfolio overview and heatmap
- [ ] Create packages/ui/src/organisms/EngineerSignoffPanel.tsx with digital signature and license verification
- [ ] Add twilio, firebase-admin, celery to pyproject.toml
- [ ] Create tests for engineer sign-off workflow and notification system
