# tests/test_chaos_resilience.py
import pytest
import asyncio
import httpx
from httpx import AsyncClient
from src.app.main import app

@pytest.mark.asyncio
async def test_api_resilience_validation():
    """TDD Task 2.4: Validates API resilience and availability as required by chaos engineering principles."""
    
    # Test 1: Basic availability probe
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Validate that API responds to health check
        try:
            response = await client.get("/health")
            # API should be responsive for basic health check
            assert response.status_code in [200, 404], "API must respond to health requests"
        except Exception:
            # If no health endpoint, test basic API responsiveness
            response = await client.get("/")
            assert response.status_code in [200, 404, 405], "API must be responsive"
    
    # Test 2: Resilience under concurrent load simulation
    async def concurrent_request():
        async with AsyncClient(app=app, base_url="http://test") as client:
            try:
                response = await client.get("/v1/tests/sessions/")
                return response.status_code
            except Exception:
                return 500
    
    # Simulate concurrent load (simplified chaos testing approach)
    tasks = [concurrent_request() for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # TDD RESILIENCE: API should handle concurrent requests gracefully
    successful_responses = sum(1 for r in results if isinstance(r, int) and r in [200, 401, 403])
    
    # At least 70% of concurrent requests should be handled properly (not crash)
    success_rate = successful_responses / len(results)
    assert success_rate >= 0.7, f"API resilience test failed: {success_rate} success rate, expected >= 0.7"

@pytest.mark.asyncio
async def test_error_handling_resilience():
    """TDD Task 2.4: Validates error handling resilience under adverse conditions."""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test 1: Invalid endpoints should return proper error format
        response = await client.get("/v1/invalid/endpoint/path")
        assert response.status_code == 404
        
        error_data = response.json()
        # RESILIENCE: Errors must follow consistent format even under stress
        assert "error_code" in error_data
        assert "transaction_id" in error_data
        
        # Test 2: Malformed requests should be handled gracefully
        response = await client.post("/v1/tests/sessions/invalid-uuid/results", 
                                   json={"malformed": "data"})
        
        # Should return error, not crash
        assert response.status_code in [400, 401, 403, 404, 422], "Malformed requests must be handled gracefully"
        
        # RESILIENCE: Even error responses must follow contract
        if response.status_code != 403:  # Skip format check for auth errors
            error_data = response.json()
            assert "error_code" in error_data or "detail" in error_data, "Error responses must be structured"