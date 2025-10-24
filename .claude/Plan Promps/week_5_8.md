Week 5-8 Implementation Prompts
Based on the completed implementations (Device Attestation, WORM Storage, Schema Registry, C&E Foundation), here are the prompts for weeks 5-8 to complete the MVP:
WEEK 5: Mobile C&E Test Execution
Prompt 1: React Native C&E Test Runner
Build a React Native component for executing C&E (Cause-and-Effect) tests with real-time sequence recording and offline capability.

Current Backend State:
- C&E scenarios stored in PostgreSQL with expected sequences
- API endpoints at /v1/compliance-workflows for scenario retrieval
- Visual designer completed in web UI (ComplianceDesigner.tsx)

Requirements:
1. Download C&E scenarios as part of offline test bundle
2. Step-by-step execution with timer/stopwatch
3. Record actual vs expected sequences
4. Detect deviations in real-time
5. Support partial completion and resume
6. Photo evidence capture per step

Component Structure:
- CETestExecutionScreen (main container)
- StepTimer (countdown/elapsed time)
- SequenceRecorder (actual events)
- DeviationDetector (compare to expected)
- EvidenceCapture (photos per step)

Technical Requirements:
- React Native 0.74+ with TypeScript
- Realm for offline storage
- React Native Camera for evidence
- Background timer for accurate timing
- CRDT for conflict-free sync

Include:
- Complete React Native component hierarchy
- Realm schema for offline C&E data
- Timer implementation with background support
- Deviation detection algorithm
- Evidence linking to steps
- Sync queue management
- Unit tests with React Native Testing Library

Provide implementation with proper offline handling, accurate timing even when app backgrounds, and CRDT sync for merging results.
```

### Prompt 2: C&E Mobile Sync Service
```
Implement the sync service for C&E test results from mobile to backend with CRDT conflict resolution.

Current State:
- Mobile captures actual sequences offline
- Backend expects results at POST /v1/tests/sessions/{id}/ce-results
- Need to handle conflicts when multiple technicians test

Requirements:
1. Sync C&E test results with Automerge CRDT
2. Handle timing conflicts (different clocks)
3. Merge partial test completions
4. Preserve evidence associations
5. Calculate deviations server-side
6. Auto-generate faults for failures

Implementation needs:
- CRDT document structure for C&E tests
- Vector clock synchronization
- Conflict resolution for timing data
- Evidence upload with attestation
- Fault generation based on deviations
- Retry logic for failed syncs

Include:
- TypeScript CRDT document types
- Sync manager class with queue
- Conflict resolution functions
- Server-side validation and merge
- Fault generation rules
- Integration tests

Provide complete implementation handling offline-first execution, clock skew compensation, and automatic fault creation for deviations >2 seconds.
```

### Prompt 3: C&E Deviation Analysis Engine
```
Create a Python service that analyzes C&E test deviations and generates compliance faults with proper AS 1851-2012 classifications.

Requirements:
1. Compare actual vs expected sequences
2. Calculate timing deviations
3. Classify severity based on deviation magnitude:
   - Critical (1A): Component failed to activate
   - High (1B): Delay >10 seconds
   - Medium (2): Delay 5-10 seconds
   - Low (3): Delay 2-5 seconds
4. Generate detailed fault descriptions
5. Link evidence to specific deviations
6. Create remediation recommendations

Analysis Components:
- Sequence comparison algorithm
- Timing deviation calculator
- Severity classification engine
- Fault description generator
- Evidence association
- Trend analysis for repeated failures

Database Updates:
- ce_test_deviations table
- ce_test_faults with classifications
- Evidence links to deviation points
- Remediation tracking

Include:
- Complete Python analysis service
- SQLAlchemy models for deviations
- Fault generation with templates
- Statistical analysis for patterns
- Performance optimization for batch processing
- Comprehensive unit tests

Provide implementation with detailed deviation tracking, intelligent fault descriptions, and pattern recognition for systemic issues.
```

## WEEK 6: Interface Testing Module

### Prompt 4: Interface Test Workflows API
```
Build FastAPI endpoints for interface testing (manual override, alarm coordination, shutdown, sprinkler) per AS 1851-2012 requirements.

Requirements:
1. Support 4 interface test types:
   - Manual override (fire panel, BMS, local switches)
   - Alarm coordination (detection to pressurization)
   - Shutdown sequence (orderly system stop)
   - Sprinkler interface (activation response)
2. Track expected vs actual responses
3. Time-based validation
4. Evidence requirements per test type
5. Auto-fault generation for failures

Endpoints needed:
- POST /v1/interface-tests/sessions - Create test session
- POST /v1/interface-tests/{id}/steps - Record test step
- POST /v1/interface-tests/{id}/complete - Finalize with results
- GET /v1/interface-tests/templates - Get test templates

Database Schema:
- interface_test_sessions (master records)
- interface_test_steps (individual actions)
- interface_test_results (pass/fail per type)
- interface_test_evidence (linked photos)

Validation Rules:
- Manual override must respond within 3 seconds
- Alarm coordination within 10 seconds
- Shutdown sequence must be orderly
- Sprinkler interface per design spec

Include:
- Complete FastAPI router implementation
- Pydantic schemas for requests/responses
- Database models with relationships
- Business logic for validation
- Fault generation service
- OpenAPI documentation
- Integration tests

Provide implementation with proper timing validation, evidence association, and automatic compliance checking.
```

### Prompt 5: React Interface Test Manager
```
Create a React component for managing interface tests with visual feedback and step-by-step guidance.

Component Requirements:
1. Test type selector (4 interface types)
2. Step-by-step execution wizard
3. Timer for response validation
4. Evidence upload per step
5. Pass/fail indicators
6. Deviation notes capture
7. Test history view

UI Components:
- InterfaceTestDashboard (main container)
- TestTypeSelector (card-based selection)
- StepExecutor (guided workflow)
- ResponseTimer (visual countdown)
- EvidenceUploader (drag-drop photos)
- ResultsSummary (pass/fail overview)

Features:
- Real-time validation against thresholds
- Visual timeline of test execution
- Color-coded pass/fail indicators
- Evidence preview with annotations
- Export test results as PDF
- Comparison with previous tests

Technical Stack:
- React 18 with TypeScript
- React Query for API calls
- Zustand for state management
- React Dropzone for uploads
- Chart.js for timing visualizations

Include:
- Complete React component tree
- TypeScript interfaces
- API integration hooks
- State management setup
- File upload handling
- Export functionality
- Storybook stories
- Unit tests

Provide implementation with intuitive UX, real-time feedback, and comprehensive test management.
```

## WEEK 7: Report Generation & Trending

### Prompt 6: Enhanced Report Generator with Trends
```
Upgrade the PDF report generation to include trend analysis, C&E results, interface tests, and engineer compliance statements.

Current State:
- Basic PDF generation with Playwright
- Missing: trends, C&E section, calibration table

New Requirements:
1. Trend charts (3-year history):
   - Pressure differentials per floor
   - Air velocity per doorway
   - Door force per door
2. C&E test results section:
   - Expected vs actual sequences
   - Deviation analysis
   - Pass/fail summary
3. Interface test results
4. Calibration verification table
5. Engineer compliance statement page

Implementation Components:
- Chart generation with Chart.js
- Multi-page PDF assembly
- Data aggregation queries
- Template rendering engine
- Digital signature integration
- WORM storage after finalization

SQL Queries Needed:
- 3-year trend data aggregation
- C&E test history rollup
- Calibration certificate status
- Defect patterns analysis

Include:
- Enhanced PDF generator service
- Chart rendering functions
- Complex SQL aggregations
- HTML template with sections
- Signature integration
- Performance optimization for large reports
- Unit tests for each section

Provide implementation generating professional reports with trends, comprehensive test results, and regulatory compliance sections.
```

### Prompt 7: Trend Analysis Service
```
Build a Python service for analyzing historical test data and generating trend insights for stair pressurization systems.

Requirements:
1. Analyze 3+ years of test data
2. Detect degradation patterns
3. Predict maintenance needs
4. Identify systemic issues
5. Generate recommendations
6. Statistical significance testing

Analysis Types:
- Time series analysis for measurements
- Regression for degradation rates
- Clustering for failure patterns
- Anomaly detection for outliers
- Predictive modeling for maintenance

Data Processing:
- Aggregate measurements by floor/door
- Calculate moving averages
- Detect trend directions
- Identify seasonal patterns
- Find correlation between failures

Output Format:
- JSON API responses
- Chart data for visualization
- Statistical summaries
- Confidence intervals
- Actionable recommendations

Include:
- Complete Python analysis service
- Pandas/NumPy data processing
- Statistical analysis with SciPy
- Time series with Prophet/ARIMA
- API endpoints for insights
- Caching for expensive calculations
- Comprehensive testing

Provide implementation with robust statistical analysis, clear insights, and actionable maintenance recommendations.
```

## WEEK 8: Engineer Sign-off & Compliance

### Prompt 8: Engineer Sign-off Workflow
```
Implement the complete engineer sign-off workflow with digital signatures and compliance statements.

Requirements:
1. Engineer review interface
2. Digital signature capture
3. Compliance statement generation
4. License verification
5. Report finalization
6. WORM storage activation

Backend Components:
- POST /v1/reports/{id}/engineer-review
- POST /v1/reports/{id}/sign
- POST /v1/reports/{id}/finalize
- GET /v1/engineers/verify-license

Frontend Components:
- Engineer review dashboard
- Signature pad component
- Compliance statement editor
- License verification
- Finalization confirmation

Compliance Statement Template:
"I, [Engineer Name], License #[Number], certify that the stair pressurization system at [Building] has been tested in accordance with AS 1851-2012 Section 13 and AS/NZS 1668.1. The system [COMPLIES/DOES NOT COMPLY] with specifications as of [Date]."

Security Requirements:
- Role-based access (engineer only)
- Signature authentication
- Tamper-proof storage
- Audit trail
- License validation against registry

Include:
- Complete backend implementation
- React components for review/sign
- Digital signature library integration
- License verification service
- Database schema updates
- Security middleware
- Integration tests
- Documentation

Provide implementation with legally binding digital signatures, license verification, and immutable report finalization.
```

### Prompt 9: Compliance Dashboard
```
Create a comprehensive compliance dashboard showing building compliance status, upcoming tests, and defect trends.

Dashboard Requirements:
1. Portfolio overview (all buildings)
2. Compliance score per building
3. Upcoming test calendar
4. Critical defect alerts
5. Trend indicators
6. Engineer workload
7. Report generation queue

Visualizations:
- Compliance heatmap (building x time)
- Test completion progress bars
- Defect severity pie charts
- Trend sparklines
- Calendar view for scheduling
- Engineer assignment matrix

Features:
- Real-time data updates
- Drill-down to building details
- Export capabilities
- Notification center
- Quick actions menu
- Filter/sort options

Technical Requirements:
- React 18 with TypeScript
- D3.js for complex visualizations
- WebSocket for real-time updates
- React Query for data fetching
- Responsive grid layout
- Performance optimization for 1000+ buildings

Include:
- Complete dashboard implementation
- Visualization components
- Real-time data hooks
- Export functionality
- Performance optimization
- Mobile responsive design
- Storybook documentation
- E2E tests with Cypress

Provide implementation with intuitive visualizations, real-time updates, and actionable insights for compliance management.
```

### Prompt 10: Notification & Escalation System
```
Build a notification system for critical defects with 24-hour escalation per AS 1851-2012 requirements.

Requirements:
1. Immediate notification for critical (1A) defects
2. 24-hour escalation if not acknowledged
3. Multiple notification channels (email, SMS, in-app)
4. Escalation hierarchy
5. Audit trail of notifications
6. Delivery confirmation

System Components:
- Notification queue (SQS/RabbitMQ)
- Template engine for messages
- Channel handlers (email/SMS/push)
- Escalation scheduler
- Delivery tracking
- Retry logic

Escalation Rules:
- T+0: Notify building owner
- T+1 hour: Notify service manager
- T+4 hours: Notify regional manager
- T+24 hours: Notify compliance officer
- All: Log to regulatory system

Database Schema:
- notification_queue
- notification_templates
- escalation_rules
- notification_log
- delivery_confirmations

Integration Points:
- SendGrid/SES for email
- Twilio for SMS
- Firebase for push
- Slack for team alerts

Include:
- Complete notification service
- Queue implementation
- Template management
- Channel handlers
- Escalation engine
- Delivery tracking
- Retry mechanisms
- Comprehensive tests
- Monitoring setup

Provide implementation with reliable delivery, proper escalation, and complete audit trail for regulatory compliance.
Implementation Priority & Dependencies
Week 5 Focus:

Mobile C&E execution (critical path)
Sync service for offline results
Deviation analysis engine

Week 6 Focus:

Interface test API endpoints
Interface test UI components
Evidence integration

Week 7 Focus:

Enhanced PDF reports with trends
Statistical analysis service
Predictive maintenance insights

Week 8 Focus:

Engineer sign-off workflow
Compliance dashboard
Notification system

Success Metrics

Week 5: C&E tests executable offline with <2% sync conflicts
Week 6: All 4 interface test types implemented with evidence
Week 7: Reports include 3-year trends and predictive insights
Week 8: 100% critical defects notified within 1 hour

These prompts build upon the completed foundation to deliver the complete MVP for AS 1851-2012 stair pressurization compliance.