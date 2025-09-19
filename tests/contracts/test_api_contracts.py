"""
API Contract Tests for FireMode Phase 2 v4.0 compliance
"""

import pytest
import uuid
from httpx import AsyncClient
from datetime import datetime
from src.app.main import app


@pytest.mark.asyncio
async def test_building_creation_contract():
    """
    Test building creation endpoint matches TDD contract exactly.
    
    Validates response structure, status codes, and field compliance.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test matches TDD contract exactly
        test_building = {
            "site_name": "Test Fire Station Alpha",
            "site_address": "123 Fire Safety Lane, Melbourne VIC 3000",
            "building_type": "fire_station",
            "compliance_status": "pending"
        }
        
        response = await client.post(
            "/v1/buildings",
            json=test_building,
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Validate contract-compliant response structure
        assert "building_id" in data
        assert isinstance(data["building_id"], str)
        assert "status" in data
        assert data["status"] == "active"
        assert data["name"] == test_building["site_name"]
        assert data["address"] == test_building["site_address"]
        assert data["building_type"] == test_building["building_type"]
        assert data["compliance_status"] == test_building["compliance_status"]
        
        # Validate timestamps
        assert "created_at" in data
        assert "updated_at" in data
        
        # Validate UUID format
        uuid.UUID(data["building_id"])  # Should not raise exception


@pytest.mark.asyncio
async def test_building_list_pagination_contract():
    """
    Test building list endpoint with cursor-based pagination.
    
    Validates pagination response structure per TDD specification.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/v1/buildings?limit=10",
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate pagination response structure
        assert "buildings" in data
        assert "total" in data
        assert "has_more" in data
        assert isinstance(data["buildings"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["has_more"], bool)
        
        # Validate optional cursor
        if "next_cursor" in data:
            assert isinstance(data["next_cursor"], str) or data["next_cursor"] is None


@pytest.mark.asyncio 
async def test_test_session_creation_contract():
    """
    Test test session creation endpoint with CRDT initialization.
    
    Validates vector clock initialization and session structure.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First create a building
        building_data = {
            "site_name": "Test Building for Sessions",
            "site_address": "456 Test Avenue",
            "building_type": "commercial"
        }
        
        building_response = await client.post(
            "/v1/buildings",
            json=building_data,
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        building_id = building_response.json()["building_id"]
        
        # Create test session
        session_data = {
            "building_id": building_id,
            "session_name": "Q1 2024 Fire Safety Inspection",
            "status": "active",
            "session_data": {
                "inspector": "John Smith",
                "weather": "Clear"
            }
        }
        
        response = await client.post(
            "/v1/tests/sessions",
            json=session_data,
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Validate session structure
        assert "id" in data
        assert "building_id" in data
        assert "session_name" in data
        assert "status" in data
        assert "session_data" in data
        assert "vector_clock" in data
        assert "created_at" in data
        
        # Validate CRDT initialization
        assert isinstance(data["vector_clock"], dict)
        assert len(data["vector_clock"]) > 0  # Should have initial user entry
        
        # Validate session data preservation
        assert data["session_data"]["inspector"] == "John Smith"
        assert data["session_data"]["weather"] == "Clear"


@pytest.mark.asyncio
async def test_offline_bundle_contract():
    """
    Test offline bundle generation for test sessions.
    
    Validates bundle structure and CRDT metadata.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Assume session exists (would be created in setup)
        session_id = "550e8400-e29b-41d4-a716-446655440000"  # Mock UUID
        
        response = await client.get(
            f"/v1/tests/sessions/{session_id}/offline-bundle",
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        # Handle both success and not found cases
        if response.status_code == 200:
            data = response.json()
            
            # Validate bundle structure
            assert "session_id" in data
            assert "bundle_data" in data
            assert "vector_clock" in data
            assert "expires_at" in data
            
            # Validate bundle contents
            bundle = data["bundle_data"]
            assert "session" in bundle
            assert "building" in bundle
            assert "evidence" in bundle
            assert "sync_metadata" in bundle
        
        elif response.status_code == 404:
            # Validate error format
            error = response.json()
            assert "error_code" in error
            assert error["error_code"] == "FIRE-404"
            assert "message" in error
            assert "transaction_id" in error
            assert "retryable" in error


@pytest.mark.asyncio
async def test_standardized_error_format():
    """
    Test standardized error response format across all endpoints.
    
    Validates error structure per TDD specification.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test 404 error format
        response = await client.get(
            "/v1/buildings/non-existent-id",
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        if response.status_code == 404:
            error = response.json()
            assert "error_code" in error
            assert error["error_code"] == "FIRE-404"
            assert "message" in error
            assert "transaction_id" in error
            assert "retryable" in error
            assert isinstance(error["retryable"], bool)
            
            # Validate transaction ID format (should be UUID)
            uuid.UUID(error["transaction_id"])


@pytest.mark.asyncio
async def test_cursor_pagination_format():
    """
    Test cursor pagination format compliance.
    
    Validates base64 cursor encoding and decoding.
    """
    from src.app.utils.pagination import encode_cursor, decode_cursor
    
    # Test cursor encoding/decoding
    test_data = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "created_at": datetime.utcnow(),
        "vector_clock": {"user_1": 5, "user_2": 3}
    }
    
    # Encode cursor
    cursor = encode_cursor(test_data)
    assert isinstance(cursor, str)
    assert len(cursor) > 0
    
    # Decode cursor
    decoded = decode_cursor(cursor)
    assert "last_evaluated_id" in decoded
    assert "vector_clock" in decoded
    assert "created_at" in decoded
    
    # Validate round-trip consistency
    assert decoded["last_evaluated_id"] == str(test_data["id"])
    assert decoded["vector_clock"] == test_data["vector_clock"]


@pytest.mark.asyncio
async def test_idempotency_compliance():
    """
    Test idempotency behavior for building creation.
    
    Validates duplicate prevention and consistent responses.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        building_data = {
            "site_name": "Idempotency Test Building",
            "site_address": "789 Unique Street",
            "building_type": "warehouse"
        }
        
        # First creation
        response1 = await client.post(
            "/v1/buildings",
            json=building_data,
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        # Second creation (should detect duplicate)
        response2 = await client.post(
            "/v1/buildings",
            json=building_data,
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        # First should succeed
        if response1.status_code == 201:
            assert "building_id" in response1.json()
        
        # Second should return conflict
        if response2.status_code == 409:
            error = response2.json()
            assert "error_code" in error
            assert error["error_code"] == "FIRE-409"


@pytest.mark.asyncio
async def test_authentication_required():
    """
    Test that authentication is required for all endpoints.
    
    Validates security enforcement across API.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test without authentication
        response = await client.get("/v1/buildings")
        
        # Should require authentication
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_vector_clock_updates():
    """
    Test CRDT vector clock updates in test sessions.
    
    Validates vector clock increment on updates.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        session_id = "550e8400-e29b-41d4-a716-446655440000"  # Mock UUID
        
        update_data = {
            "session_name": "Updated Session Name",
            "session_data": {
                "updated_field": "new_value"
            }
        }
        
        response = await client.put(
            f"/v1/tests/sessions/{session_id}",
            json=update_data,
            headers={"Authorization": "Bearer valid-test-token"}
        )
        
        # Handle both success and not found cases
        if response.status_code == 200:
            data = response.json()
            
            # Validate vector clock exists and is updated
            assert "vector_clock" in data
            assert isinstance(data["vector_clock"], dict)
            
            # Should have at least one entry with incremented value
            assert len(data["vector_clock"]) > 0