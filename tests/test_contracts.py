"""
API Contract Tests for FireMode Compliance Platform
Testing error format compliance and pagination contracts
"""

import pytest
from httpx import AsyncClient
from src.app.main import app


@pytest.mark.asyncio
async def test_error_format_compliance():
    """Test that error responses follow the standardized FIRE error format"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/nonexistent")
        assert response.status_code == 404
        error = response.json()
        
        # Validate FIRE error format
        assert "transaction_id" in error
        assert error["error_code"] == "FIRE-404"
        assert error["retryable"] is True
        assert "message" in error


@pytest.mark.asyncio
async def test_pagination_contract():
    """Test that pagination responses follow the contract specification"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/tests/sessions",
            headers={"Authorization": "Bearer test-token"}
        )
        data = response.json()
        
        # Validate pagination structure
        assert "data" in data
        assert "next_cursor" in data
        assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_buildings_contract():
    """Test buildings API contract compliance"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/buildings",
            headers={"Authorization": "Bearer test-token"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "buildings" in data
            assert "total" in data
            assert "has_more" in data
        else:
            # Should return standardized error format
            error = response.json()
            assert "error_code" in error
            assert error["error_code"].startswith("FIRE-")


@pytest.mark.asyncio
async def test_test_sessions_contract():
    """Test test sessions API contract compliance"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/tests/sessions",
            headers={"Authorization": "Bearer test-token"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            assert isinstance(data["data"], list)
            assert "next_cursor" in data
        else:
            # Should return standardized error format
            error = response.json()
            assert "error_code" in error
            assert error["error_code"].startswith("FIRE-")


@pytest.mark.asyncio
async def test_unauthorized_access_contract():
    """Test that unauthorized access returns proper FIRE error format"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/buildings")
        
        assert response.status_code in [401, 403]
        error = response.json()
        assert "error_code" in error
        assert error["error_code"] in ["FIRE-401", "FIRE-403"]
        assert error["retryable"] is False


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint availability"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "service" in data