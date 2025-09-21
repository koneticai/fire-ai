"""
Final Load Test for TDD Compliance - Phase 2 Validation
"""

import time
import uuid
import numpy as np
from locust import HttpUser, task, between, events

class ProductionLoadTest(HttpUser):
    """Production-grade load test validating p95 latency requirements"""
    wait_time = between(0.5, 1.5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.latencies = []
        self.token = "test-token"  # Simplified for testing
    
    def on_start(self):
        """Setup user session"""
        # In production, would perform actual login
        self.client.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })
    
    @task(10)
    def classify_fault(self):
        """Primary performance-critical endpoint - TDD requirement: p95 < 300ms"""
        start = time.time()
        
        response = self.client.post(
            "/v1/classify",
            json={
                "item_code": "AS1851-2012-FE-01",
                "observed_condition": "pressure_low"
            },
            catch_response=True
        )
        
        latency = time.time() - start
        self.latencies.append(latency)
        
        # Validate response structure
        if response.status_code == 200:
            try:
                data = response.json()
                if "classification" not in data or "audit_log_id" not in data:
                    response.failure("Invalid response structure")
            except:
                response.failure("Invalid JSON response")
        elif response.status_code >= 500:
            response.failure(f"Server error: {response.status_code}")
    
    @task(5)
    def submit_results(self):
        """CRDT submission endpoint - Test vector clock handling"""
        session_id = str(uuid.uuid4())
        
        response = self.client.post(
            f"/v1/tests/sessions/{session_id}/results",
            json={
                "changes": [
                    {"op": "set", "path": "/test_result", "value": "passed"},
                    {"op": "set", "path": "/timestamp", "value": time.time()}
                ],
                "_sync_meta": {
                    "vector_clock": {"client1": 1, "client2": 0},
                    "client_id": str(uuid.uuid4())
                }
            },
            headers={"Idempotency-Key": str(uuid.uuid4())},
            catch_response=True
        )
        
        # Validate idempotency handling
        if response.status_code not in [200, 201, 409]:
            response.failure(f"Unexpected status for CRDT submission: {response.status_code}")
    
    @task(2)
    def get_offline_bundle(self):
        """Offline bundle generation - Test size and performance limits"""
        session_id = str(uuid.uuid4())
        
        response = self.client.get(
            f"/v1/tests/sessions/{session_id}/offline_bundle",
            catch_response=True
        )
        
        if response.status_code == 200:
            # Verify bundle size < 50MB requirement
            size = len(response.content)
            if size > 50 * 1024 * 1024:
                response.failure(f"Bundle too large: {size} bytes > 50MB limit")
            else:
                # Log bundle size for monitoring
                print(f"Bundle size: {size / 1024:.1f}KB")
        elif response.status_code == 404:
            # Expected for non-existent sessions
            pass
        else:
            response.failure(f"Unexpected status for bundle request: {response.status_code}")
    
    @task(3)
    def test_session_operations(self):
        """Test session CRUD with pagination"""
        # Create session
        response = self.client.post(
            "/v1/tests/sessions",
            json={
                "building_id": str(uuid.uuid4()),
                "session_name": f"Load Test Session {time.time()}",
                "status": "active"
            },
            catch_response=True
        )
        
        if response.status_code not in [200, 201]:
            response.failure(f"Session creation failed: {response.status_code}")
            return
        
        # Test pagination
        response = self.client.get(
            "/v1/tests/sessions",
            params={"limit": 10},
            catch_response=True
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "sessions" not in data or "has_more" not in data:
                    response.failure("Invalid pagination response structure")
            except:
                response.failure("Invalid JSON in pagination response")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Validate p95 latency requirement after test completion"""
    print("\n" + "="*50)
    print("FINAL PERFORMANCE VALIDATION")
    print("="*50)
    
    # Collect all latencies from all users
    all_latencies = []
    for user in environment.runner.user_instances:
        if hasattr(user, 'latencies'):
            all_latencies.extend(user.latencies)
    
    if all_latencies:
        # Calculate performance statistics
        sorted_latencies = sorted(all_latencies)
        total_requests = len(sorted_latencies)
        
        avg_latency = np.mean(sorted_latencies)
        p50_latency = np.percentile(sorted_latencies, 50)
        p95_latency = np.percentile(sorted_latencies, 95)
        p99_latency = np.percentile(sorted_latencies, 99)
        max_latency = max(sorted_latencies)
        
        print(f"Total classify requests: {total_requests}")
        print(f"Average latency: {avg_latency:.3f}s")
        print(f"P50 latency: {p50_latency:.3f}s")
        print(f"P95 latency: {p95_latency:.3f}s")
        print(f"P99 latency: {p99_latency:.3f}s")
        print(f"Max latency: {max_latency:.3f}s")
        
        # TDD Requirement Validation
        print("\n" + "-"*30)
        print("TDD REQUIREMENT VALIDATION")
        print("-"*30)
        
        if p95_latency <= 0.3:
            print("✅ PASSED: P95 latency ≤ 300ms requirement")
            print(f"   Actual P95: {p95_latency*1000:.1f}ms")
        else:
            print("❌ FAILED: P95 latency exceeds 300ms requirement")
            print(f"   Required: ≤ 300ms")
            print(f"   Actual P95: {p95_latency*1000:.1f}ms")
            print(f"   Violation: +{(p95_latency - 0.3)*1000:.1f}ms")
        
        # Additional performance insights
        violations = len([l for l in sorted_latencies if l > 0.3])
        violation_rate = (violations / total_requests) * 100
        
        print(f"\nRequests > 300ms: {violations}/{total_requests} ({violation_rate:.1f}%)")
        
        if violation_rate > 5:  # More than 5% violations
            print("⚠️  WARNING: High violation rate indicates performance issues")
    else:
        print("❌ ERROR: No latency data collected")
    
    print("="*50)

class ComplianceStressTest(ProductionLoadTest):
    """Extended stress test for compliance validation"""
    wait_time = between(0.1, 0.5)  # More aggressive load
    
    @task(15)
    def rapid_classification(self):
        """Rapid-fire classification requests"""
        super().classify_fault()
    
    @task(5)
    def concurrent_crdt_updates(self):
        """Simulate concurrent CRDT updates to same session"""
        session_id = "stress-test-session"  # Same session for all users
        
        response = self.client.post(
            f"/v1/tests/sessions/{session_id}/results",
            json={
                "changes": [{"op": "set", "path": f"/user_{self.user_id}", "value": time.time()}],
                "_sync_meta": {
                    "vector_clock": {f"client_{self.user_id}": 1},
                    "client_id": str(self.user_id)
                }
            },
            headers={"Idempotency-Key": f"{self.user_id}-{time.time()}"},
            catch_response=True
        )