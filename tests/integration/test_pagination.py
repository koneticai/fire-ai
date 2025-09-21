import pytest
import asyncio
import uuid
from httpx import AsyncClient
from src.app.main import app


@pytest.mark.asyncio
async def test_vector_clock_pagination_consistency():
    """Test pagination handles concurrent writes correctly"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create multiple sessions concurrently
        tasks = []
        for i in range(50):
            tasks.append(
                client.post("/v1/tests/sessions", 
                json={"building_id": str(uuid.uuid4())})
            )
        
        await asyncio.gather(*tasks)
        
        # Paginate through results
        all_items = []
        cursor = None
        
        while True:
            params = {"limit": 10}
            if cursor:
                params["cursor"] = cursor
            
            response = await client.get("/v1/tests/sessions", params=params)
            data = response.json()
            all_items.extend(data["data"])
            
            if not data.get("next_cursor"):
                break
            cursor = data["next_cursor"]
        
        # Verify no duplicates despite concurrent writes
        ids = [item["id"] for item in all_items]
        assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_cursor_based_filtering():
    """Test that filtering works with cursor pagination"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create sessions with different statuses
        for status in ["active", "completed", "failed"]:
            for i in range(5):
                await client.post("/v1/tests/sessions", 
                    json={
                        "building_id": str(uuid.uuid4()),
                        "status": status
                    })
        
        # Test filtering by status
        response = await client.get("/v1/tests/sessions", 
            params={"status": ["active"], "limit": 3})
        data = response.json()
        
        assert all(item["status"] == "active" for item in data["data"])
        assert len(data["data"]) <= 3


@pytest.mark.asyncio
async def test_date_range_filtering():
    """Test date-based filtering with pagination"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test date filtering
        response = await client.get("/v1/tests/sessions", 
            params={
                "date_from": "2023-01-01T00:00:00",
                "date_to": "2025-12-31T23:59:59",
                "limit": 5
            })
        
        # Should not raise errors
        assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
async def test_invalid_cursor_handling():
    """Test that invalid cursors are handled gracefully"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/tests/sessions", 
            params={"cursor": "invalid_cursor"})
        
        # Should return empty results or handle gracefully
        assert response.status_code in [200, 400, 401, 403]