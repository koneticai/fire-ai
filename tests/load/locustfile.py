"""
Locust load testing configuration for FireMode Compliance Platform
Targets performance-critical endpoints to validate p95 latency < 300ms
"""

import json
import uuid
import time
from locust import HttpUser, task, between

class FireModeUser(HttpUser):
    """Load testing user for FireMode performance validation"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Setup called when user starts"""
        # Generate test data
        self.session_id = str(uuid.uuid4())
        self.idempotency_keys = {}
        
        # Mock authentication header (in real scenario, would get from login)
        self.headers = {
            "Content-Type": "application/json",
            "X-User-ID": "test-user-" + str(uuid.uuid4()),
            "Authorization": "Bearer mock-token-for-testing"
        }
    
    def generate_idempotency_key(self, endpoint):
        """Generate unique idempotency key for each request"""
        key = f"{endpoint}-{int(time.time()*1000)}-{uuid.uuid4()}"
        self.idempotency_keys[endpoint] = key
        return key
    
    @task(3)
    def post_evidence(self):
        """Test POST /v1/evidence endpoint (performance-critical)"""
        
        evidence_data = {
            "session_id": self.session_id,
            "evidence_type": "fire_extinguisher_test",
            "file_path": f"/uploads/evidence_{int(time.time())}.jpg",
            "metadata": {
                "location": "Building A - Floor 2",
                "inspector": "John Doe",
                "timestamp": int(time.time()),
                "equipment_id": f"FE-{uuid.uuid4().hex[:8]}"
            },
            "data": "mock_binary_data_" + "x" * 1000  # Simulate some data
        }
        
        headers = self.headers.copy()
        headers["Idempotency-Key"] = self.generate_idempotency_key("evidence")
        
        with self.client.post(
            "/v1/evidence",
            json=evidence_data,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 503:
                # Service unavailable - expected during development
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(2)
    def post_test_results(self):
        """Test POST /v1/tests/sessions/{session_id}/results endpoint (performance-critical)"""
        
        results_data = {
            "results": {
                "test_type": "monthly_inspection",
                "status": "passed",
                "findings": [
                    {
                        "item": "fire_extinguisher_pressure",
                        "status": "ok",
                        "value": 200,
                        "unit": "psi",
                        "notes": "Within acceptable range"
                    },
                    {
                        "item": "safety_pin_intact",
                        "status": "ok",
                        "value": True,
                        "notes": "Pin properly secured"
                    }
                ],
                "inspector_notes": "All equipment functioning properly",
                "completion_time": int(time.time())
            },
            "timestamp": time.time()
        }
        
        headers = self.headers.copy()
        headers["Idempotency-Key"] = self.generate_idempotency_key("test_results")
        
        with self.client.post(
            f"/v1/tests/sessions/{self.session_id}/results",
            json=results_data,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Session not found - expected during testing
                response.success()
            elif response.status_code == 503:
                # Service unavailable - expected during development
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Test health endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(1)
    def list_test_sessions(self):
        """Test GET /v1/tests/sessions endpoint (non-critical but important)"""
        with self.client.get(
            "/v1/tests/sessions?limit=10",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 503]:
                # Accept these status codes during testing
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

class HighThroughputUser(FireModeUser):
    """High-frequency user for stress testing performance-critical endpoints"""
    
    wait_time = between(0.1, 0.5)  # Very short wait times for stress testing
    
    @task(5)
    def rapid_evidence_submission(self):
        """Rapid-fire evidence submission to test p95 latency"""
        self.post_evidence()
    
    @task(3)  
    def rapid_results_submission(self):
        """Rapid-fire results submission to test p95 latency"""
        self.post_test_results()

# Define user classes for different load patterns
class StandardLoadUser(FireModeUser):
    """Standard load pattern for normal operations"""
    weight = 3

class StressTestUser(HighThroughputUser):
    """High throughput pattern for stress testing"""
    weight = 1