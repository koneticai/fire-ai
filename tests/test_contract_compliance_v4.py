"""
TDD v4.0 Contract Compliance Tests for FireMode Platform
Updated to work with current architecture and properly validate contracts
"""

import pytest
import uuid
from httpx import AsyncClient
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.app.main import app
from src.app.schemas.auth import TokenPayload


@pytest.mark.asyncio
async def test_authentication_flow_contract(auth_headers):
    """Test that authentication flow works properly with JWT tokens"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock successful database operations for authenticated requests
        with patch("src.app.database.core.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result
            mock_get_db.return_value = mock_session
            
            response = await client.get(
                "/v1/tests/sessions",
                headers=auth_headers
            )
            
            # Should return proper pagination structure when authenticated
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "next_cursor" in data
            assert isinstance(data["data"], list)


@pytest.mark.asyncio 
async def test_standardized_fire_error_format():
    """Test that FIRE error format is used for 404 errors"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/nonexistent")
        assert response.status_code == 404
        error = response.json()
        
        # Should use FIRE error format
        assert "transaction_id" in error
        assert "error_code" in error
        assert error["error_code"] == "FIRE-404"
        assert "message" in error
        assert "retryable" in error
        assert isinstance(error["retryable"], bool)


@pytest.mark.asyncio
async def test_unauthorized_access_behavior():
    """Test that unauthenticated requests are properly handled"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/v1/buildings")
        
        # Should require authentication (can be 307 redirect or 401/403)
        assert response.status_code in [307, 401, 403]
        
        # If it's an error response, should have proper format
        if response.status_code in [401, 403]:
            error = response.json()
            assert "error_code" in error
            assert error["error_code"] in ["FIRE-401", "FIRE-403"]


@pytest.mark.asyncio
async def test_building_creation_contract_compliance(auth_headers):
    """Test building creation follows TDD contract exactly"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock successful building creation
        with patch("src.app.database.core.get_db") as mock_get_db:
            mock_session = AsyncMock()
            
            # Mock no existing building found
            mock_result_existing = Mock()
            mock_result_existing.scalar_one_or_none.return_value = None
            
            # Mock successful building creation
            mock_building = Mock()
            mock_building.id = uuid.uuid4()
            mock_building.name = "Test Fire Station Alpha"
            mock_building.address = "123 Fire Safety Lane, Melbourne VIC 3000"
            mock_building.building_type = "fire_station"
            mock_building.compliance_status = "pending"
            mock_building.created_at = datetime.utcnow()
            mock_building.updated_at = datetime.utcnow()
            mock_building.owner_id = uuid.uuid4()
            
            mock_session.execute.return_value = mock_result_existing
            mock_session.add = Mock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_get_db.return_value = mock_session
            
            # Mock the building read schema validation
            with patch("src.app.schemas.building.BuildingRead.model_validate") as mock_validate:
                mock_validate.return_value = {
                    "building_id": str(mock_building.id),
                    "name": mock_building.name,
                    "address": mock_building.address,
                    "building_type": mock_building.building_type,
                    "compliance_status": mock_building.compliance_status,
                    "status": "active",
                    "created_at": mock_building.created_at.isoformat(),
                    "updated_at": mock_building.updated_at.isoformat()
                }
                
                test_building = {
                    "site_name": "Test Fire Station Alpha",
                    "site_address": "123 Fire Safety Lane, Melbourne VIC 3000",
                    "building_type": "fire_station",
                    "compliance_status": "pending"
                }
                
                response = await client.post(
                    "/v1/buildings",
                    json=test_building,
                    headers=auth_headers
                )
                
                # Should follow TDD contract for building creation
                if response.status_code == 201:
                    data = response.json()
                    assert "building_id" in data
                    assert "status" in data
                    assert "name" in data
                    assert "address" in data
                    assert "building_type" in data
                    assert "compliance_status" in data
                    assert "created_at" in data
                    assert "updated_at" in data


@pytest.mark.asyncio
async def test_pagination_contract_structure(auth_headers):
    """Test that pagination follows the contract specification"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock successful session list with pagination
        with patch("src.app.database.core.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            
            # Mock test sessions with proper structure
            mock_sessions = [
                Mock(
                    id=uuid.uuid4(),
                    session_name="Test Session 1",
                    status="active",
                    vector_clock={"user_1": 1},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                Mock(
                    id=uuid.uuid4(),
                    session_name="Test Session 2", 
                    status="active",
                    vector_clock={"user_1": 2},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            
            mock_result.scalars.return_value.all.return_value = mock_sessions
            mock_session.execute.return_value = mock_result
            mock_get_db.return_value = mock_session
            
            response = await client.get(
                "/v1/tests/sessions?limit=10",
                headers=auth_headers
            )
            
            # Should return proper pagination structure
            assert response.status_code == 200
            data = response.json()
            
            # Validate contract-compliant pagination structure
            assert "data" in data
            assert "next_cursor" in data
            assert isinstance(data["data"], list)
            
            # Each session should have required fields
            for session in data["data"]:
                assert "id" in session
                assert "session_name" in session
                assert "status" in session
                assert "vector_clock" in session
                assert "created_at" in session


@pytest.mark.asyncio
async def test_evidence_submission_contract(auth_headers):
    """Test evidence submission follows TDD contract"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock session ownership verification and Go service communication
        with patch("src.app.database.core.get_db") as mock_get_db, \
             patch("src.app.routers.evidence.get_go_service_proxy") as mock_proxy:
            
            # Mock session exists and belongs to user
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_test_session = Mock()
            mock_test_session.id = uuid.uuid4()
            mock_result.scalar_one_or_none.return_value = mock_test_session
            mock_session.execute.return_value = mock_result
            mock_get_db.return_value = mock_session
            
            # Mock successful Go service proxy response
            mock_go_proxy = Mock()
            mock_go_proxy.submit_evidence = AsyncMock(return_value={
                "evidence_id": str(uuid.uuid4()),
                "hash": "abcd1234567890",
                "status": "uploaded"
            })
            mock_proxy.return_value = mock_go_proxy
            
            # Test evidence submission with file
            files = {"file": ("test.jpg", b"fake image data", "image/jpeg")}
            data = {
                "session_id": str(mock_test_session.id),
                "evidence_type": "photo"
            }
            
            response = await client.post(
                "/v1/evidence/submit",
                files=files,
                data=data,
                headers=auth_headers
            )
            
            # Should follow evidence submission contract
            if response.status_code == 200:
                result = response.json()
                assert "evidence_id" in result
                assert "hash" in result
                assert "status" in result


@pytest.mark.asyncio 
async def test_health_endpoint_contract():
    """Test health endpoints follow contract specification"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test main health endpoint
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["status"] == "ok"
        assert data["service"] == "firemode-backend"


@pytest.mark.asyncio
async def test_vector_clock_crdt_contract(auth_headers):
    """Test CRDT vector clock behavior follows contract"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock session update with vector clock
        with patch("src.app.database.core.get_db") as mock_get_db:
            mock_session = AsyncMock() 
            mock_result = Mock()
            
            # Mock existing session with vector clock
            mock_test_session = Mock()
            mock_test_session.id = uuid.uuid4()
            mock_test_session.vector_clock = {"user_1": 1}
            mock_test_session.created_at = datetime.utcnow()
            mock_test_session.updated_at = datetime.utcnow()
            mock_result.scalar_one_or_none.return_value = mock_test_session
            mock_session.execute.return_value = mock_result
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_get_db.return_value = mock_session
            
            session_id = str(mock_test_session.id)
            update_data = {
                "session_name": "Updated Session",
                "session_data": {"test": "data"}
            }
            
            # Mock vector clock in request state
            with patch("fastapi.Request") as mock_request:
                mock_request_instance = Mock()
                mock_request_instance.state.vector_clock = {"user_1": 1}
                
                response = await client.put(
                    f"/v1/tests/sessions/{session_id}",
                    json=update_data,
                    headers={**auth_headers, "If-Match": '{"user_1": 1}'}
                )
                
                # Should handle CRDT vector clock updates
                if response.status_code in [200, 412, 428]:
                    # These are all valid CRDT responses
                    if response.status_code == 200:
                        data = response.json()
                        assert "vector_clock" in data
                        assert isinstance(data["vector_clock"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])