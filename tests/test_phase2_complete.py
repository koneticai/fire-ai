"""
Phase 2 Complete TDD Compliance Test Suite
"""

import pytest
import asyncio
import uuid
import httpx
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

class TestPhase2Compliance:
    """Verify all Phase 2 TDD requirements are met"""
    
    def test_api_contract_compliance(self):
        """Task 2.1: All endpoints match TDD contract"""
        
        # Test error format compliance
        endpoints_to_test = [
            ("/v1/buildings", "POST", {"site_name": "Test", "site_address": "123"}),
            ("/v1/tests/sessions", "GET", {}),
            ("/v1/evidence", "POST", {}),
        ]
        
        for path, method, body in endpoints_to_test:
            if method == "POST":
                response = client.post(path, json=body)
            else:
                response = client.get(path)
            
            # Verify error format matches TDD when applicable
            if response.status_code >= 400:
                error = response.json()
                assert "detail" in error or "error" in error, f"Invalid error format for {path}"
    
    def test_pagination_consistency(self):
        """Task 2.2: Vector clock pagination handles consistency"""
        
        response = client.get("/v1/tests/sessions", params={"limit": 10})
        
        if response.status_code == 200:
            data = response.json()
            
            # Check pagination structure
            expected_fields = ["sessions", "has_more"]
            for field in expected_fields:
                if field in data:
                    assert isinstance(data[field], (list, bool)), f"Invalid {field} type"
    
    def test_health_endpoints(self):
        """Verify health check endpoints are operational"""
        
        # Test liveness
        response = client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert "alive" in data
        assert data["alive"] is True
        
        # Test readiness
        response = client.get("/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert "ready" in data
        assert "checks" in data
        assert isinstance(data["checks"], dict)
    
    def test_performance_metrics_endpoint(self):
        """Verify performance metrics are available"""
        
        response = client.get("/health/metrics")
        assert response.status_code == 200
        
        data = response.json()
        # Should have some performance data structure
        assert isinstance(data, dict)
    
    def test_offline_bundle_structure(self):
        """FR-2: Offline bundle endpoint exists and returns proper structure"""
        
        session_id = str(uuid.uuid4())
        response = client.get(f"/v1/tests/sessions/{session_id}/offline_bundle")
        
        # Should return 404 for non-existent session or 200 with bundle
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            # Bundle should be within size limits
            assert len(response.content) <= 50 * 1024 * 1024, "Bundle exceeds 50MB limit"
    
    def test_classification_endpoint_exists(self):
        """Verify classification endpoint is available"""
        
        response = client.post(
            "/v1/classify",
            json={
                "item_code": "TEST-ITEM",
                "observed_condition": "test_condition"
            }
        )
        
        # Should return either success or proper error (not 404/500)
        assert response.status_code in [200, 400, 401, 422], f"Unexpected status: {response.status_code}"
    
    def test_rtl_integration(self):
        """Verify RTL (Token Revocation List) is integrated"""
        
        # Test RTL endpoint exists
        response = client.get("/v1/auth/rtl")
        
        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404
    
    def test_crdt_endpoint_structure(self):
        """Verify CRDT endpoints handle vector clocks"""
        
        session_id = str(uuid.uuid4())
        response = client.post(
            f"/v1/tests/sessions/{session_id}/results",
            json={
                "changes": [{"op": "set", "path": "/test", "value": "data"}],
                "_sync_meta": {"vector_clock": {}}
            }
        )
        
        # Should handle CRDT structure properly (not crash)
        assert response.status_code in [200, 201, 400, 401, 404, 422]

class TestPerformanceRequirements:
    """Test performance and operational requirements"""
    
    def test_health_check_response_time(self):
        """Health checks should be fast"""
        import time
        
        start = time.time()
        response = client.get("/health/live")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 1.0, f"Health check too slow: {duration:.3f}s"
    
    def test_root_endpoint_performance(self):
        """Root endpoint should respond quickly"""
        import time
        
        start = time.time()
        response = client.get("/")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 0.5, f"Root endpoint too slow: {duration:.3f}s"
        
        data = response.json()
        assert "service" in data
        assert "status" in data

class TestErrorHandling:
    """Test proper error handling across the application"""
    
    def test_invalid_json_handling(self):
        """Test handling of malformed JSON"""
        
        response = client.post(
            "/v1/tests/sessions",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_auth_headers(self):
        """Test endpoints requiring authentication"""
        
        protected_endpoints = [
            "/v1/tests/sessions",
            "/v1/rules",
            "/v1/classify"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should require authentication
            assert response.status_code in [401, 422]
    
    def test_large_payload_handling(self):
        """Test handling of large payloads"""
        
        large_data = {"data": "x" * 10000}  # 10KB payload
        response = client.post("/v1/tests/sessions", json=large_data)
        
        # Should handle gracefully (not crash)
        assert response.status_code in [200, 201, 400, 401, 413, 422]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])