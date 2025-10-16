"""
Tests for Defects CRUD endpoints.

This module tests the defects CRUD endpoints:
- POST /v1/defects - Create defect
- GET /v1/defects - List defects with pagination and filters
- GET /v1/defects/{id} - Get defect by ID
- PATCH /v1/defects/{id} - Update defect status
- GET /v1/defects/buildings/{building_id}/defects - Get building defects
- GET /v1/defects/test-sessions/{session_id}/defects - Get test session defects
"""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.app.routers.defects import (
    create_defect,
    list_defects,
    get_defect,
    update_defect,
    get_building_defects,
    get_test_session_defects
)
from src.app.models.defects import Defect
from src.app.models.test_sessions import TestSession
from src.app.models.buildings import Building
from src.app.schemas.auth import TokenPayload
from src.app.schemas.defect import (
    DefectCreate,
    DefectUpdate,
    DefectSeverity,
    DefectStatus
)


class TestDefectsCRUD:
    """Test cases for defects CRUD operations."""
    
    @pytest.fixture
    def mock_defect(self):
        """Create a mock defect object."""
        defect = Mock(spec=Defect)
        defect.id = uuid.uuid4()
        defect.test_session_id = uuid.uuid4()
        defect.building_id = uuid.uuid4()
        defect.severity = DefectSeverity.HIGH
        defect.category = "fire_extinguisher"
        defect.description = "Fire extinguisher pressure below threshold"
        defect.as1851_rule_code = "FE-01"
        defect.asset_id = uuid.uuid4()
        defect.status = DefectStatus.OPEN
        defect.discovered_at = datetime.utcnow()
        defect.acknowledged_at = None
        defect.acknowledged_by = None
        defect.repaired_at = None
        defect.verified_at = None
        defect.closed_at = None
        defect.evidence_ids = []
        defect.repair_evidence_ids = []
        defect.created_at = datetime.utcnow()
        defect.updated_at = datetime.utcnow()
        defect.created_by = uuid.uuid4()
        return defect
    
    @pytest.fixture
    def mock_test_session(self):
        """Create a mock test session object."""
        session = Mock(spec=TestSession)
        session.id = uuid.uuid4()
        session.created_by = uuid.uuid4()
        session.building_id = uuid.uuid4()
        return session
    
    @pytest.fixture
    def mock_building(self):
        """Create a mock building object."""
        building = Mock(spec=Building)
        building.id = uuid.uuid4()
        building.owner_id = uuid.uuid4()
        return building
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user token."""
        return TokenPayload(
            username="testuser",
            user_id=uuid.uuid4(),
            jti=uuid.uuid4(),
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        )
    
    @pytest.fixture
    def defect_create_data(self):
        """Create defect creation data."""
        return DefectCreate(
            test_session_id=uuid.uuid4(),
            severity=DefectSeverity.HIGH,
            category="fire_extinguisher",
            description="Fire extinguisher pressure below threshold",
            as1851_rule_code="FE-01",
            asset_id=uuid.uuid4()
        )
    
    @pytest.mark.asyncio
    async def test_create_defect_success(self, mock_user, mock_test_session, defect_create_data):
        """Test successful defect creation."""
        # Mock database queries
        mock_db = AsyncMock()
        
        # Mock test session query
        mock_session_result = Mock()
        mock_session_result.scalar_one_or_none.return_value = mock_test_session
        mock_db.execute.return_value = mock_session_result
        
        # Call the endpoint
        response = await create_defect(
            defect_data=defect_create_data,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response.test_session_id == defect_create_data.test_session_id
        assert response.severity == defect_create_data.severity
        assert response.category == defect_create_data.category
        assert response.description == defect_create_data.description
        assert response.status == DefectStatus.OPEN
        assert response.created_by == mock_user.user_id
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_defect_invalid_severity(self, mock_user, defect_create_data):
        """Test defect creation with invalid severity."""
        # Set invalid severity
        defect_create_data.severity = "invalid_severity"
        
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await create_defect(
                defect_data=defect_create_data,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 400
        assert "Invalid severity" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_create_defect_missing_test_session(self, mock_user, defect_create_data):
        """Test defect creation when test session not found."""
        mock_db = AsyncMock()
        
        # Mock test session query returning None
        mock_session_result = Mock()
        mock_session_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_session_result
        
        with pytest.raises(HTTPException) as exc_info:
            await create_defect(
                defect_data=defect_create_data,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Test session not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_defect_by_id_success(self, mock_user, mock_defect, mock_building):
        """Test successful defect retrieval by ID."""
        mock_db = AsyncMock()
        
        # Mock defect query with building join
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_defect
        mock_db.execute.return_value = mock_result
        
        # Call the endpoint
        response = await get_defect(
            defect_id=mock_defect.id,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response.id == mock_defect.id
        assert response.test_session_id == mock_defect.test_session_id
        assert response.severity == mock_defect.severity
        assert response.status == mock_defect.status
    
    @pytest.mark.asyncio
    async def test_get_defect_by_id_not_found(self, mock_user):
        """Test defect retrieval when defect not found."""
        mock_db = AsyncMock()
        
        # Mock defect query returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_defect(
                defect_id=uuid.uuid4(),
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Defect not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_defect_by_id_unauthorized(self, mock_user):
        """Test defect retrieval when user doesn't own the building."""
        mock_db = AsyncMock()
        
        # Mock defect query returning None (user doesn't own building)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_defect(
                defect_id=uuid.uuid4(),
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Defect not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_list_defects_filtered_by_status(self, mock_user, mock_defect, mock_building):
        """Test listing defects filtered by status."""
        mock_db = AsyncMock()
        
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_count_result
        
        # Mock defects query
        mock_defects_result = Mock()
        mock_defects_result.scalars.return_value.all.return_value = [mock_defect]
        mock_db.execute.side_effect = [mock_count_result, mock_defects_result]
        
        # Call the endpoint
        response = await list_defects(
            page=1,
            page_size=20,
            status=[DefectStatus.OPEN],
            severity=None,
            building_id=None,
            test_session_id=None,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response.total == 1
        assert len(response.defects) == 1
        assert response.defects[0].id == mock_defect.id
        assert not response.has_more
    
    @pytest.mark.asyncio
    async def test_list_defects_filtered_by_severity(self, mock_user, mock_defect, mock_building):
        """Test listing defects filtered by severity."""
        mock_db = AsyncMock()
        
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_count_result
        
        # Mock defects query
        mock_defects_result = Mock()
        mock_defects_result.scalars.return_value.all.return_value = [mock_defect]
        mock_db.execute.side_effect = [mock_count_result, mock_defects_result]
        
        # Call the endpoint
        response = await list_defects(
            page=1,
            page_size=20,
            status=None,
            severity=[DefectSeverity.HIGH],
            building_id=None,
            test_session_id=None,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response.total == 1
        assert len(response.defects) == 1
        assert response.defects[0].severity == DefectSeverity.HIGH
    
    @pytest.mark.asyncio
    async def test_list_defects_pagination(self, mock_user, mock_defect, mock_building):
        """Test listing defects with pagination."""
        mock_db = AsyncMock()
        
        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 25  # More than page size
        
        # Mock defects query returning more than page_size
        mock_defects_result = Mock()
        defects = [mock_defect] * 21  # Return 21 defects when page_size=20
        mock_defects_result.scalars.return_value.all.return_value = defects
        mock_db.execute.side_effect = [mock_count_result, mock_defects_result]
        
        # Call the endpoint
        response = await list_defects(
            page=1,
            page_size=20,
            status=None,
            severity=None,
            building_id=None,
            test_session_id=None,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response.total == 25
        assert len(response.defects) == 20  # Should be truncated to page_size
        assert response.has_more  # Should indicate more pages
    
    @pytest.mark.asyncio
    async def test_update_defect_acknowledge(self, mock_user, mock_defect, mock_building):
        """Test updating defect to acknowledged status."""
        mock_db = AsyncMock()
        
        # Mock defect query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_defect
        mock_db.execute.return_value = mock_result
        
        # Create update data
        update_data = DefectUpdate(status=DefectStatus.ACKNOWLEDGED)
        
        # Call the endpoint
        response = await update_defect(
            defect_id=mock_defect.id,
            defect_update=update_data,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response.status == DefectStatus.ACKNOWLEDGED
        assert response.acknowledged_by == mock_user.user_id
        assert response.acknowledged_at is not None
        
        # Verify database operations
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_defect_invalid_status_transition(self, mock_user, mock_defect, mock_building):
        """Test updating defect with invalid status transition."""
        # Set defect to acknowledged status
        mock_defect.status = DefectStatus.ACKNOWLEDGED
        
        mock_db = AsyncMock()
        
        # Mock defect query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_defect
        mock_db.execute.return_value = mock_result
        
        # Try to transition directly to closed (invalid)
        update_data = DefectUpdate(status=DefectStatus.CLOSED)
        
        with pytest.raises(HTTPException) as exc_info:
            await update_defect(
                defect_id=mock_defect.id,
                defect_update=update_data,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 422
        assert "Invalid status transition" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_building_defects(self, mock_user, mock_defect, mock_building):
        """Test getting defects for a specific building."""
        # Set the defect's building_id to match the building
        mock_defect.building_id = mock_building.id
        
        mock_db = AsyncMock()
        
        # Mock building query
        mock_building_result = Mock()
        mock_building_result.scalar_one_or_none.return_value = mock_building
        
        # Mock defects query
        mock_defects_result = Mock()
        mock_defects_result.scalars.return_value.all.return_value = [mock_defect]
        
        mock_db.execute.side_effect = [mock_building_result, mock_defects_result]
        
        # Call the endpoint
        response = await get_building_defects(
            building_id=mock_building.id,
            status=None,
            severity=None,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert len(response) == 1
        assert response[0].id == mock_defect.id
        assert response[0].building_id == mock_building.id
    
    @pytest.mark.asyncio
    async def test_get_test_session_defects(self, mock_user, mock_defect, mock_test_session):
        """Test getting defects for a specific test session."""
        # Set the defect's test_session_id to match the test session
        mock_defect.test_session_id = mock_test_session.id
        
        mock_db = AsyncMock()
        
        # Mock test session query
        mock_session_result = Mock()
        mock_session_result.scalar_one_or_none.return_value = mock_test_session
        
        # Mock defects query
        mock_defects_result = Mock()
        mock_defects_result.scalars.return_value.all.return_value = [mock_defect]
        
        mock_db.execute.side_effect = [mock_session_result, mock_defects_result]
        
        # Call the endpoint
        response = await get_test_session_defects(
            session_id=mock_test_session.id,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert len(response) == 1
        assert response[0].id == mock_defect.id
        assert response[0].test_session_id == mock_test_session.id
    
    @pytest.mark.asyncio
    async def test_get_building_defects_building_not_found(self, mock_user):
        """Test getting defects when building not found."""
        mock_db = AsyncMock()
        
        # Mock building query returning None
        mock_building_result = Mock()
        mock_building_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_building_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_building_defects(
                building_id=uuid.uuid4(),
                status=None,
                severity=None,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Building not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_test_session_defects_session_not_found(self, mock_user):
        """Test getting defects when test session not found."""
        mock_db = AsyncMock()
        
        # Mock test session query returning None
        mock_session_result = Mock()
        mock_session_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_session_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_test_session_defects(
                session_id=uuid.uuid4(),
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Test session not found" in exc_info.value.detail
