"""
Tests for Evidence CRUD endpoints.

This module tests the new evidence CRUD endpoints:
- GET /v1/evidence/{id} - Get evidence metadata
- GET /v1/evidence/{id}/download - Get download URL
- PATCH /v1/evidence/{id}/flag - Flag evidence for review
- POST /v1/evidence/{id}/link-defect - Link evidence to defect
"""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.app.routers.evidence import (
    get_evidence_metadata,
    get_evidence_download_url,
    flag_evidence_for_review,
    link_evidence_to_defect
)
from src.app.models.evidence import Evidence
from src.app.models.test_sessions import TestSession
from src.app.models.defects import Defect
from src.app.schemas.auth import TokenPayload
from src.app.schemas.evidence import (
    EvidenceFlagRequest,
    EvidenceLinkDefectRequest
)


class TestEvidenceCRUD:
    """Test cases for evidence CRUD operations."""
    
    @pytest.fixture
    def mock_evidence(self):
        """Create a mock evidence object."""
        evidence = Mock(spec=Evidence)
        evidence.id = uuid.uuid4()
        evidence.session_id = uuid.uuid4()
        evidence.evidence_type = "photo"
        evidence.checksum = "abc123def456"
        evidence.created_at = datetime.utcnow()
        evidence.flagged_for_review = False
        evidence.flag_reason = None
        evidence.flagged_at = None
        evidence.flagged_by = None
        evidence.file_path = "s3://test-bucket/evidence/test_photo.jpg"
        evidence.evidence_metadata = {
            "filename": "test_photo.jpg",
            "file_type": "image/jpeg",
            "file_size": 1024,
            "device_attestation_status": "verified"
        }
        return evidence
    
    @pytest.fixture
    def mock_test_session(self):
        """Create a mock test session object."""
        session = Mock(spec=TestSession)
        session.id = uuid.uuid4()
        session.created_by = uuid.uuid4()
        return session
    
    @pytest.fixture
    def mock_defect(self):
        """Create a mock defect object."""
        defect = Mock(spec=Defect)
        defect.id = uuid.uuid4()
        defect.test_session_id = uuid.uuid4()
        defect.evidence_ids = []
        return defect
    
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
    def mock_admin_user(self):
        """Create a mock admin user token."""
        return TokenPayload(
            username="admin_user_admin",
            user_id=uuid.uuid4(),
            jti=uuid.uuid4(),
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        )
    
    @pytest.mark.asyncio
    async def test_get_evidence_by_id_success(self, mock_evidence, mock_test_session, mock_user):
        """Test successful retrieval of evidence metadata."""
        # Mock database query with join
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_evidence
        mock_db.execute.return_value = mock_result
        
        # Call the endpoint
        response = await get_evidence_metadata(
            evidence_id=mock_evidence.id,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response.id == mock_evidence.id
        assert response.session_id == mock_evidence.session_id
        assert response.evidence_type == mock_evidence.evidence_type
        assert response.filename == "test_photo.jpg"
        assert response.file_type == "image/jpeg"
        assert response.file_size == 1024
        assert response.hash == mock_evidence.checksum
        assert response.device_attestation_status == "verified"
        assert response.flagged_for_review == False
    
    @pytest.mark.asyncio
    async def test_get_evidence_by_id_not_found(self, mock_user):
        """Test evidence metadata retrieval when evidence not found."""
        # Mock database query returning None
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Call the endpoint
        with pytest.raises(HTTPException) as exc_info:
            await get_evidence_metadata(
                evidence_id=uuid.uuid4(),
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Evidence not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_evidence_by_id_unauthorized(self, mock_user):
        """Test evidence retrieval when user doesn't own the test session."""
        # Mock database query returning None (user doesn't own session)
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_evidence_metadata(
                evidence_id=uuid.uuid4(),
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Evidence not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('src.app.routers.evidence.boto3.client')
    async def test_get_evidence_download_url_success(self, mock_boto3_client, mock_evidence, mock_test_session, mock_user):
        """Test successful generation of download URL."""
        # Mock database query with join
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_evidence
        mock_db.execute.return_value = mock_result
        
        # Mock S3 client
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/evidence/test_photo.jpg?presigned"
        mock_boto3_client.return_value = mock_s3_client
        
        # Call the endpoint
        response = await get_evidence_download_url(
            evidence_id=mock_evidence.id,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response.download_url == "https://s3.amazonaws.com/test-bucket/evidence/test_photo.jpg?presigned"
        assert isinstance(response.expires_at, datetime)
        
        # Verify S3 client was called correctly
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': 'test-bucket', 'Key': 'evidence/test_photo.jpg'},
            ExpiresIn=7 * 24 * 60 * 60
        )
    
    @pytest.mark.asyncio
    async def test_get_evidence_download_unauthorized(self, mock_user):
        """Test download URL generation when user doesn't own the test session."""
        # Mock database query returning None (user doesn't own session)
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_evidence_download_url(
                evidence_id=uuid.uuid4(),
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Evidence not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_flag_evidence_admin_only(self, mock_user):
        """Test flagging evidence with non-admin user (should return 403)."""
        mock_db = AsyncMock()
        
        flag_request = EvidenceFlagRequest(flag_reason="Test reason")
        
        with pytest.raises(HTTPException) as exc_info:
            await flag_evidence_for_review(
                evidence_id=uuid.uuid4(),
                flag_request=flag_request,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 403
        assert "Admin role required" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_flag_evidence_success(self, mock_evidence, mock_admin_user):
        """Test successful flagging of evidence for review."""
        # Mock database query
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_evidence
        mock_db.execute.return_value = mock_result
        
        # Call the endpoint
        flag_request = EvidenceFlagRequest(flag_reason="Suspicious content detected")
        
        response = await flag_evidence_for_review(
            evidence_id=mock_evidence.id,
            flag_request=flag_request,
            db=mock_db,
            current_user=mock_admin_user
        )
        
        # Verify response
        assert response.id == mock_evidence.id
        assert response.flagged_for_review == True
        assert response.flag_reason == "Suspicious content detected"
        assert response.flagged_by == mock_admin_user.user_id
        
        # Verify database was updated
        assert mock_evidence.flagged_for_review == True
        assert mock_evidence.flag_reason == "Suspicious content detected"
        assert mock_evidence.flagged_by == mock_admin_user.user_id
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_flag_evidence_not_found(self, mock_admin_user):
        """Test flagging evidence when evidence not found."""
        mock_db = AsyncMock()
        
        # Mock database query returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        flag_request = EvidenceFlagRequest(flag_reason="Test reason")
        
        with pytest.raises(HTTPException) as exc_info:
            await flag_evidence_for_review(
                evidence_id=uuid.uuid4(),
                flag_request=flag_request,
                db=mock_db,
                current_user=mock_admin_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Evidence not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_link_evidence_to_defect_success(self, mock_evidence, mock_test_session, mock_defect, mock_user):
        """Test successful linking of evidence to defect."""
        # Mock database queries
        mock_db = AsyncMock()
        
        # Mock evidence query with join
        mock_evidence_result = Mock()
        mock_evidence_result.scalar_one_or_none.return_value = mock_evidence
        
        # Mock defect query with join (second call)
        mock_defect_result = Mock()
        mock_defect_result.scalar_one_or_none.return_value = mock_defect
        
        # Set up mock to return different results for different calls
        mock_db.execute.side_effect = [mock_evidence_result, mock_defect_result]
        
        # Call the endpoint
        link_request = EvidenceLinkDefectRequest(defect_id=mock_defect.id)
        
        response = await link_evidence_to_defect(
            evidence_id=mock_evidence.id,
            link_request=link_request,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response
        assert response["defect_id"] == mock_defect.id
        assert response["evidence_id"] == mock_evidence.id
        assert mock_evidence.id in response["evidence_ids"]
        assert "successfully linked" in response["message"]
        
        # Verify database was updated
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_link_evidence_to_defect_evidence_not_found(self, mock_user):
        """Test linking evidence to defect when evidence not found."""
        mock_db = AsyncMock()
        
        # Mock evidence query returning None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        link_request = EvidenceLinkDefectRequest(defect_id=uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await link_evidence_to_defect(
                evidence_id=uuid.uuid4(),
                link_request=link_request,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Evidence not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_link_evidence_to_defect_defect_not_found(self, mock_evidence, mock_test_session, mock_user):
        """Test linking evidence to defect when defect not found."""
        mock_db = AsyncMock()
        
        # Mock evidence query with join
        mock_evidence_result = Mock()
        mock_evidence_result.scalar_one_or_none.return_value = mock_evidence
        
        # Mock defect query returning None (second call)
        mock_defect_result = Mock()
        mock_defect_result.scalar_one_or_none.return_value = None
        
        # Set up mock to return different results for different calls
        mock_db.execute.side_effect = [mock_evidence_result, mock_defect_result]
        
        link_request = EvidenceLinkDefectRequest(defect_id=uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await link_evidence_to_defect(
                evidence_id=mock_evidence.id,
                link_request=link_request,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Defect not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_link_evidence_already_linked(self, mock_evidence, mock_test_session, mock_defect, mock_user):
        """Test linking evidence to defect when already linked."""
        # Set up defect with evidence already linked
        mock_defect.evidence_ids = [mock_evidence.id]
        
        mock_db = AsyncMock()
        
        # Mock evidence query with join
        mock_evidence_result = Mock()
        mock_evidence_result.scalar_one_or_none.return_value = mock_evidence
        
        # Mock defect query with join (second call)
        mock_defect_result = Mock()
        mock_defect_result.scalar_one_or_none.return_value = mock_defect
        
        # Set up mock to return different results for different calls
        mock_db.execute.side_effect = [mock_evidence_result, mock_defect_result]
        
        # Call the endpoint
        link_request = EvidenceLinkDefectRequest(defect_id=mock_defect.id)
        
        response = await link_evidence_to_defect(
            evidence_id=mock_evidence.id,
            link_request=link_request,
            db=mock_db,
            current_user=mock_user
        )
        
        # Verify response indicates already linked
        assert response["defect_id"] == mock_defect.id
        assert response["evidence_id"] == mock_evidence.id
        assert "already linked" in response["message"]
        
        # Verify no database operations were performed
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_evidence_download_file_not_found(self, mock_evidence, mock_test_session, mock_user):
        """Test download URL generation when evidence file not found."""
        # Set evidence without file_path
        mock_evidence.file_path = None
        
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_evidence
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_evidence_download_url(
                evidence_id=mock_evidence.id,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 404
        assert "Evidence file not found" in exc_info.value.detail