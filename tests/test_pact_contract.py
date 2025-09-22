# tests/test_pact_contract.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_contract_test_sessions_endpoint(client, authenticated_headers, async_session):
    """Test sessions endpoint contract."""
    # Mock database response properly
    mock_sessions = [
        {"id": "test-1", "building_id": "b1", "status": "pending"},
        {"id": "test-2", "building_id": "b2", "status": "completed"}
    ]
    
    # Configure async session mock
    async_session.execute = AsyncMock(return_value=MagicMock(
        scalars=MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=mock_sessions)
        ))
    ))
    
    response = client.get("/v1/tests/sessions", headers=authenticated_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "next_cursor" in data

@pytest.mark.asyncio  
async def test_pact_consumer_contract_validation():
    """TDD Task 2.3: Validates consumer-provider contract expectations."""
    # This test validates that our API responses match consumer expectations
    # as required by TDD contract testing principles
    
    from httpx import AsyncClient
    from src.app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test standard error format contract
        response = await client.get("/v1/nonexistent-endpoint")
        
        assert response.status_code == 404
        error_data = response.json()
        
        # CONTRACT: Error responses must follow FIRE error format
        required_error_fields = ["transaction_id", "error_code", "message", "retryable"]
        for field in required_error_fields:
            assert field in error_data, f"Contract violation: {field} missing from error response"
        
        # CONTRACT: Error codes must follow FIRE-XXX pattern
        assert error_data["error_code"].startswith("FIRE-"), "Contract violation: error_code must follow FIRE-XXX pattern"