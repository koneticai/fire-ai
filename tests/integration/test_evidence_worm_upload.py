"""
Test evidence upload with WORM protection (Task 2.2)

Integration tests for evidence upload with Object Lock and audit logging.

References:
- data_model.md: evidence table, audit_log table
- AGENTS.md: Security Gate - validation
- AS 1851-2012: Evidence immutability requirements
"""

import pytest
import hashlib
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.evidence import Evidence
from src.app.models.audit_log import AuditLog
from src.app.routers.evidence import calculate_file_hash


class TestEvidenceWormUpload:
    """Integration tests for evidence upload with WORM protection."""
    
    def test_evidence_upload_with_worm(self, client, auth_headers, db_session):
        """Evidence upload should use WORM storage and return WORM metadata."""
        # Mock WORM uploader
        with patch('src.app.routers.evidence.WormStorageUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader_class.return_value = mock_uploader
            
            # Mock S3 upload responses
            test_s3_uri = "s3://test-worm-bucket/evidence/2024/10/27/test-session/abc123_test.jpg"
            mock_uploader.upload_with_retention.return_value = test_s3_uri
            mock_uploader.verify_immutability.return_value = {
                "is_immutable": True,
                "retention_mode": "COMPLIANCE",
                "retain_until": (datetime.utcnow() + timedelta(days=365*7)).isoformat(),
                "is_encrypted": True
            }
            
            # Mock Go service proxy
            with patch('src.app.routers.evidence.GoServiceProxy') as mock_proxy_class:
                mock_proxy = Mock()
                mock_proxy_class.return_value = mock_proxy
                
                test_evidence_id = str(uuid4())
                test_file_content = b"test image data"
                test_hash = calculate_file_hash(test_file_content)
                
                mock_proxy.submit_evidence = AsyncMock(return_value={
                    "evidence_id": test_evidence_id,
                    "hash": test_hash,
                    "status": "verified"
                })
                
                # Mock attestation validation
                with patch('src.app.routers.evidence.validate_device_attestation', return_value=True):
                    # Submit evidence
                    response = client.post(
                        "/v1/evidence/submit",
                        headers={
                            **auth_headers,
                            'X-Device-Attestation': 'mock-attestation-token'
                        },
                        data={
                            "session_id": "test-session-id",
                            "evidence_type": "photo"
                        },
                        files={
                            "file": ("test.jpg", test_file_content, "image/jpeg")
                        }
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    
                    # Verify response includes evidence ID and hash
                    assert data["evidence_id"] == test_evidence_id
                    assert data["hash"] == test_hash
                    assert data["status"] == "verified"
                    
                    # Verify WORM uploader was called correctly
                    mock_uploader.upload_with_retention.assert_called_once()
                    call_kwargs = mock_uploader.upload_with_retention.call_args[1]
                    assert call_kwargs["content_type"] == "image/jpeg"
                    assert "metadata" in call_kwargs
                    
                    # Verify immutability check was performed
                    mock_uploader.verify_immutability.assert_called_once()
    
    def test_evidence_checksum_stored(self, client, auth_headers, db_session):
        """Evidence checksum should be calculated and stored per data_model.md."""
        test_file_content = b"test data for checksum verification"
        expected_checksum = calculate_file_hash(test_file_content)
        
        # Mock WORM uploader
        with patch('src.app.routers.evidence.WormStorageUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader_class.return_value = mock_uploader
            mock_uploader.upload_with_retention.return_value = "s3://test-bucket/test-key"
            mock_uploader.verify_immutability.return_value = {"is_immutable": True}
            
            # Mock Go service proxy
            with patch('src.app.routers.evidence.GoServiceProxy') as mock_proxy_class:
                mock_proxy = Mock()
                mock_proxy_class.return_value = mock_proxy
                
                test_evidence_id = str(uuid4())
                mock_proxy.submit_evidence = AsyncMock(return_value={
                    "evidence_id": test_evidence_id,
                    "hash": expected_checksum,
                    "status": "verified"
                })
                
                # Mock attestation validation
                with patch('src.app.routers.evidence.validate_device_attestation', return_value=True):
                    response = client.post(
                        "/v1/evidence/submit",
                        headers={
                            **auth_headers,
                            'X-Device-Attestation': 'mock-attestation-token'
                        },
                        data={
                            "session_id": "test-session",
                            "evidence_type": "photo"
                        },
                        files={
                            "file": ("test.jpg", test_file_content, "image/jpeg")
                        }
                    )
                    
                    assert response.status_code == 200
                    
                    # Verify checksum was passed to Go service
                    call_kwargs = mock_proxy.submit_evidence.call_args[1]
                    assert call_kwargs["sha256_hash"] == expected_checksum
                    assert len(expected_checksum) == 64  # SHA-256 produces 64-char hex
    
    def test_evidence_metadata_includes_worm_info(self, client, auth_headers):
        """Evidence metadata should include WORM retention details."""
        # Mock WORM uploader
        with patch('src.app.routers.evidence.WormStorageUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader_class.return_value = mock_uploader
            
            retention_until = datetime.utcnow() + timedelta(days=365*7)
            test_s3_uri = "s3://test-bucket/test-key"
            
            mock_uploader.upload_with_retention.return_value = test_s3_uri
            mock_uploader.verify_immutability.return_value = {
                "is_immutable": True,
                "retention_mode": "COMPLIANCE",
                "retain_until": retention_until.isoformat(),
                "is_encrypted": True
            }
            
            # Mock Go service proxy
            with patch('src.app.routers.evidence.GoServiceProxy') as mock_proxy_class:
                mock_proxy = Mock()
                mock_proxy_class.return_value = mock_proxy
                
                test_evidence_id = str(uuid4())
                mock_proxy.submit_evidence = AsyncMock(return_value={
                    "evidence_id": test_evidence_id,
                    "hash": calculate_file_hash(b"test data"),
                    "status": "verified"
                })
                
                # Mock attestation validation
                with patch('src.app.routers.evidence.validate_device_attestation', return_value=True):
                    response = client.post(
                        "/v1/evidence/submit",
                        headers={
                            **auth_headers,
                            'X-Device-Attestation': 'mock-attestation-token'
                        },
                        data={
                            "session_id": "test-session",
                            "evidence_type": "photo"
                        },
                        files={
                            "file": ("test.jpg", b"test data", "image/jpeg")
                        }
                    )
                    
                    assert response.status_code == 200
                    
                    # Verify WORM storage info was passed to Go service
                    call_kwargs = mock_proxy.submit_evidence.call_args[1]
                    worm_info = call_kwargs["worm_storage_info"]
                    
                    assert worm_info["s3_uri"] == test_s3_uri
                    assert worm_info["immutability_verified"] is True
                    assert "bucket" in worm_info
                    assert "s3_key" in worm_info
    
    @pytest.mark.asyncio
    async def test_evidence_audit_log_created(self, client, auth_headers, db_session):
        """Evidence upload should create audit log entry per data_model.md."""
        # Mock WORM uploader
        with patch('src.app.routers.evidence.WormStorageUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader_class.return_value = mock_uploader
            
            test_s3_uri = "s3://test-bucket/evidence/test-key"
            mock_uploader.upload_with_retention.return_value = test_s3_uri
            mock_uploader.verify_immutability.return_value = {
                "is_immutable": True,
                "retention_mode": "COMPLIANCE"
            }
            
            # Mock Go service proxy
            with patch('src.app.routers.evidence.GoServiceProxy') as mock_proxy_class:
                mock_proxy = Mock()
                mock_proxy_class.return_value = mock_proxy
                
                test_evidence_id = str(uuid4())
                test_file_content = b"test audit log data"
                test_hash = calculate_file_hash(test_file_content)
                
                mock_proxy.submit_evidence = AsyncMock(return_value={
                    "evidence_id": test_evidence_id,
                    "hash": test_hash,
                    "status": "verified"
                })
                
                # Mock attestation validation
                with patch('src.app.routers.evidence.validate_device_attestation', return_value=True):
                    # Submit evidence
                    response = client.post(
                        "/v1/evidence/submit",
                        headers={
                            **auth_headers,
                            'X-Device-Attestation': 'mock-attestation-token'
                        },
                        data={
                            "session_id": "test-session-audit",
                            "evidence_type": "photo"
                        },
                        files={
                            "file": ("test.jpg", test_file_content, "image/jpeg")
                        }
                    )
                    
                    assert response.status_code == 200
                    
                    # Verify audit log was created on the mocked session
                    assert db_session.add.call_count >= 1, "AuditLog not added to session"
                    
                    # Get the audit log from the add() call
                    audit_log_calls = [
                        call for call in db_session.add.call_args_list
                        if len(call[0]) > 0 and isinstance(call[0][0], AuditLog)
                    ]
                    assert len(audit_log_calls) > 0, "No AuditLog instances added"
                    
                    latest_log = audit_log_calls[-1][0][0]  # Get the AuditLog instance
                    
                    # Verify audit log properties
                    assert isinstance(latest_log, AuditLog)
                    assert latest_log.action == "UPLOAD_EVIDENCE_WORM"
                    assert latest_log.resource_type == "evidence"
                    assert str(latest_log.resource_id) == test_evidence_id
                    assert latest_log.user_id is not None
                    
                    # Verify audit log new_values contains WORM metadata
                    new_values = latest_log.new_values
                    assert new_values["worm_protected"] is True
                    assert new_values["checksum"] == test_hash
                    assert "retention_until" in new_values
                    assert "s3_uri" in new_values
                    assert new_values["immutability_verified"] is True
                    assert new_values["evidence_type"] == "photo"
                    assert new_values["session_id"] == "test-session-audit"


class TestCalculateFileHash:
    """Unit tests for file hash calculation."""
    
    def test_calculate_file_hash_deterministic(self):
        """Hash calculation should be deterministic."""
        test_content = b"test file content"
        hash1 = calculate_file_hash(test_content)
        hash2 = calculate_file_hash(test_content)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string
    
    def test_calculate_file_hash_empty_file(self):
        """Hash calculation should work for empty files."""
        empty_content = b""
        file_hash = calculate_file_hash(empty_content)
        
        assert len(file_hash) == 64
        assert file_hash == hashlib.sha256(empty_content).hexdigest()
    
    def test_calculate_file_hash_large_file(self):
        """Hash calculation should work for large files."""
        large_content = b"x" * 10000
        file_hash = calculate_file_hash(large_content)
        
        assert len(file_hash) == 64
        assert file_hash == hashlib.sha256(large_content).hexdigest()
