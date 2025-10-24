# ADR 0007: C&E and Interface Testing Architecture

## Status
Accepted

## Context

The FireAI compliance platform needs to implement C&E (Cause-and-Effect) and Interface testing per AS 1851-2012 requirements. This involves:

1. **C&E Testing**: Real-time sequence recording with offline mobile capability
2. **Interface Testing**: 4 test types (manual override, alarm coordination, shutdown, sprinkler)
3. **Mobile-First Architecture**: Offline execution with conflict-free sync
4. **Performance Requirements**: Sub-second response times for mobile APIs
5. **Compliance Standards**: AS 1851-2012 timing validation and fault generation

## Decision

### 1. Separate API Endpoints for C&E and Interface Tests

**Decision**: Create dedicated API endpoints for C&E and Interface tests, separate from the existing `compliance_workflows` endpoint.

**Rationale**:
- `compliance_workflows` is designed for visual workflow designer/templates
- C&E and Interface tests require execution-specific endpoints with timing data
- Clear separation of concerns between design and execution
- Better performance optimization for mobile execution

**Implementation**:
- `/v1/ce-tests/*` - C&E test execution endpoints
- `/v1/interface-tests/*` - Interface test execution endpoints
- `/v1/compliance-workflows/*` - Workflow design and templates (existing)

### 2. Mobile-First Architecture with Offline Capability

**Decision**: Implement mobile-first architecture with offline execution and conflict-free sync.

**Rationale**:
- Field technicians often work in areas with poor connectivity
- Offline capability ensures uninterrupted testing
- Conflict-free sync prevents data loss in multi-user scenarios
- Mobile-first design optimizes for field conditions

**Implementation**:
- React Native bare workflow for native performance
- Realm database for offline storage
- Automerge CRDT for conflict-free synchronization
- Background timer service for accurate timing

### 3. CRDT (Conflict-Free Replicated Data Types) for Multi-User Sync

**Decision**: Use Automerge CRDT for handling concurrent test submissions from multiple technicians.

**Rationale**:
- Multiple technicians may test the same system simultaneously
- CRDT ensures no data loss during concurrent operations
- Vector clocks provide conflict resolution
- Maintains data consistency across devices

**Implementation**:
- Automerge document structure for C&E test data
- Vector clock synchronization
- Automatic conflict resolution
- Server-side merge validation

### 4. Automatic Deviation Analysis and Fault Generation

**Decision**: Implement server-side deviation analysis with automatic fault generation.

**Rationale**:
- Real-time deviation detection during test execution
- Automatic fault generation per AS 1851-2012 severity classifications
- Consistent fault descriptions and remediation recommendations
- Reduces manual intervention and human error

**Implementation**:
- Sequence comparison algorithm
- Timing deviation calculator
- Severity classification engine (Critical, High, Medium, Low)
- Automatic fault generation with templates

### 5. Performance-Optimized API Design

**Decision**: Design APIs with strict performance requirements for mobile execution.

**Rationale**:
- Mobile devices have limited processing power
- Field conditions require fast response times
- Battery life optimization
- User experience in challenging environments

**Performance Requirements**:
- C&E session creation: p95 < 300ms
- Step recording: p95 < 200ms
- Deviation analysis: < 200ms
- CRDT merge: p95 < 500ms
- Report generation: < 10s total

### 6. AS 1851-2012 Compliance Integration

**Decision**: Integrate AS 1851-2012 timing requirements directly into the validation logic.

**Rationale**:
- Regulatory compliance is mandatory
- Automated validation reduces human error
- Consistent application of standards
- Audit trail for compliance verification

**Implementation**:
- Manual override: < 3 seconds
- Alarm coordination: < 10 seconds
- Shutdown sequence: Orderly progression
- Sprinkler interface: Per design specification

## Consequences

### Positive
- **Clear Separation of Concerns**: Design vs execution endpoints
- **Offline-First Mobile Experience**: Uninterrupted field testing
- **Conflict-Free Multi-User Testing**: No data loss scenarios
- **Automatic Compliance Checking**: Reduced human error
- **Performance Optimized**: Fast mobile execution
- **Regulatory Compliance**: AS 1851-2012 integration

### Negative
- **Additional Complexity**: CRDT sync logic and conflict resolution
- **Mobile App Development**: Requires React Native expertise
- **Performance Monitoring**: Need to track mobile API performance
- **Offline Data Management**: Complex sync queue management
- **Testing Complexity**: Multi-device and offline testing scenarios

### Risks
- **CRDT Complexity**: Vector clock synchronization can be complex
- **Mobile Performance**: Battery and processing constraints
- **Offline Data Loss**: Risk if sync fails
- **Network Connectivity**: Dependency on reliable sync
- **Multi-User Conflicts**: Complex conflict resolution scenarios

## Implementation Details

### Database Schema
```sql
-- C&E Test Tables
ce_test_sessions (id, test_session_id, building_id, workflow_id, status, created_at)
ce_test_steps (id, ce_test_session_id, step_id, action, actual_time, expected_time, status)
ce_test_deviations (id, ce_test_session_id, step_id, deviation_seconds, severity, description)
ce_test_results (id, ce_test_session_id, overall_status, deviations_count, faults_generated)

-- Interface Test Tables
interface_test_sessions (id, test_session_id, building_id, test_type, status, created_at)
interface_test_steps (id, interface_test_session_id, step_name, action, response_time, status)
interface_test_results (id, interface_test_session_id, overall_status, validation_status)
```

### API Endpoints
```python
# C&E Test API
GET /v1/ce-tests/scenarios/{workflow_id}
POST /v1/ce-tests/sessions
POST /v1/ce-tests/sessions/{id}/steps
POST /v1/ce-tests/sessions/{id}/complete
POST /v1/ce-tests/sessions/{id}/crdt-merge
POST /v1/ce-tests/sessions/{id}/evidence

# Interface Test API
GET /v1/interface-tests/templates
POST /v1/interface-tests/sessions
POST /v1/interface-tests/sessions/{id}/steps
POST /v1/interface-tests/sessions/{id}/complete
```

### Mobile Architecture
```typescript
// React Native Components
CETestExecutionScreen - Main test execution interface
StepTimer - Background timer service
SequenceRecorder - Real-time sequence recording
DeviationDetector - Client-side deviation detection
EvidenceCapture - Photo/video capture with attestation
CETestSyncService - CRDT sync and queue management
```

## Monitoring and Metrics

### Performance Metrics
- API response times (p95, p99)
- CRDT merge success rate
- Offline sync completion rate
- Mobile app performance metrics
- Battery usage optimization

### Business Metrics
- Test completion rate
- Deviation detection accuracy
- Fault generation accuracy
- Compliance rate per building
- Engineer productivity metrics

## Future Considerations

### Scalability
- Horizontal scaling of CRDT merge operations
- Database partitioning for large datasets
- CDN for mobile app updates
- Edge computing for offline sync

### Enhancements
- AI-powered deviation analysis
- Predictive maintenance insights
- Advanced conflict resolution
- Real-time collaboration features
- Augmented reality for test guidance

## References

- [AS 1851-2012 Standard](https://www.standards.org.au/standards-catalogue/sa-snz/building/fs-013/as--1851-2012)
- [Automerge CRDT Documentation](https://automerge.org/)
- [React Native Performance](https://reactnative.dev/docs/performance)
- [Realm Database](https://realm.io/)
- [FastAPI Performance](https://fastapi.tiangolo.com/benchmarks/)

## Decision Date
2025-01-17

## Review Date
2025-04-17 (3 months)

## Stakeholders
- Engineering Team
- Compliance Team
- Field Operations Team
- Product Management
