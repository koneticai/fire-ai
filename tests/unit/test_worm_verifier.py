"""
Unit tests for WORM compliance verifier.
"""

import pytest
import boto3
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

from src.app.services.compliance.worm_verifier import WormComplianceVerifier, ComplianceCheck, ComplianceReport


class TestWormComplianceVerifier:
    """Test cases for WormComplianceVerifier."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            yield mock_s3
    
    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            yield mock_conn, mock_cursor
    
    @pytest.fixture
    def verifier(self, mock_s3_client, mock_db_connection):
        """Create WormComplianceVerifier instance."""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'}):
            return WormComplianceVerifier(
                evidence_bucket="test-evidence-bucket",
                reports_bucket="test-reports-bucket"
            )
    
    def test_init(self, mock_s3_client, mock_db_connection):
        """Test WormComplianceVerifier initialization."""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'}):
            verifier = WormComplianceVerifier()
            
            assert verifier.evidence_bucket == "firemode-evidence-worm"
            assert verifier.reports_bucket == "firemode-reports-worm"
            mock_s3_client.assert_called_once_with('s3')
    
    def test_verify_object_lock_success(self, verifier, mock_s3_client):
        """Test successful Object Lock verification."""
        # Mock responses
        mock_s3_client.get_object_retention.return_value = {
            'Retention': {
                'Mode': 'COMPLIANCE',
                'RetainUntilDate': datetime.utcnow() + timedelta(days=365 * 7)
            }
        }
        
        mock_s3_client.head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': datetime.utcnow(),
            'ServerSideEncryption': 'AES256'
        }
        
        # Test verification
        result = verifier.verify_object_lock("test-bucket", "test/key")
        
        # Verify calls
        mock_s3_client.get_object_retention.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/key"
        )
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/key"
        )
        
        # Verify result
        assert result['bucket'] == "test-bucket"
        assert result['key'] == "test/key"
        assert result['mode'] == 'COMPLIANCE'
        assert result['compliant'] is True
        assert result['is_retained'] is True
        assert result['file_size'] == 1024
        assert result['encryption'] == 'AES256'
    
    def test_verify_object_lock_not_compliant(self, verifier, mock_s3_client):
        """Test Object Lock verification for non-compliant object."""
        # Mock non-compliant response
        mock_s3_client.get_object_retention.return_value = {
            'Retention': {
                'Mode': 'GOVERNANCE',  # Not COMPLIANCE
                'RetainUntilDate': datetime.utcnow() + timedelta(days=365 * 7)
            }
        }
        
        mock_s3_client.head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': datetime.utcnow(),
            'ServerSideEncryption': 'AES256'
        }
        
        # Test verification
        result = verifier.verify_object_lock("test-bucket", "test/key")
        
        assert result['bucket'] == "test-bucket"
        assert result['key'] == "test/key"
        assert result['mode'] == 'GOVERNANCE'
        assert result['compliant'] is False
        assert result['is_retained'] is True
    
    def test_verify_object_lock_error(self, verifier, mock_s3_client):
        """Test Object Lock verification with error."""
        # Mock error
        mock_s3_client.get_object_retention.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}},
            'GetObjectRetention'
        )
        
        # Test verification
        result = verifier.verify_object_lock("test-bucket", "test/key")
        
        assert result['bucket'] == "test-bucket"
        assert result['key'] == "test/key"
        assert result['compliant'] is False
        assert 'error' in result
    
    def test_verify_retention_policy_success(self, verifier, mock_s3_client):
        """Test successful retention policy verification."""
        # Mock response
        mock_s3_client.get_object_lock_configuration.return_value = {
            'ObjectLockConfiguration': {
                'ObjectLockEnabled': 'Enabled',
                'Rule': {
                    'DefaultRetention': {
                        'Mode': 'COMPLIANCE',
                        'Years': 7
                    }
                }
            }
        }
        
        # Test verification
        result = verifier.verify_retention_policy("test-bucket")
        
        # Verify call
        mock_s3_client.get_object_lock_configuration.assert_called_once_with(
            Bucket="test-bucket"
        )
        
        # Verify result
        assert result['bucket'] == "test-bucket"
        assert result['mode'] == 'COMPLIANCE'
        assert result['retention_years'] == 7
        assert result['compliant'] is True
    
    def test_verify_retention_policy_not_compliant(self, verifier, mock_s3_client):
        """Test retention policy verification for non-compliant bucket."""
        # Mock non-compliant response
        mock_s3_client.get_object_lock_configuration.return_value = {
            'ObjectLockConfiguration': {
                'ObjectLockEnabled': 'Enabled',
                'Rule': {
                    'DefaultRetention': {
                        'Mode': 'GOVERNANCE',  # Not COMPLIANCE
                        'Years': 5  # Not 7 years
                    }
                }
            }
        }
        
        # Test verification
        result = verifier.verify_retention_policy("test-bucket")
        
        assert result['bucket'] == "test-bucket"
        assert result['mode'] == 'GOVERNANCE'
        assert result['retention_years'] == 5
        assert result['compliant'] is False
    
    def test_verify_retention_policy_error(self, verifier, mock_s3_client):
        """Test retention policy verification with error."""
        # Mock error
        mock_s3_client.get_object_lock_configuration.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'GetObjectLockConfiguration'
        )
        
        # Test verification
        result = verifier.verify_retention_policy("test-bucket")
        
        assert result['bucket'] == "test-bucket"
        assert result['compliant'] is False
        assert 'error' in result
    
    def test_create_audit_report_success(self, verifier, mock_s3_client, mock_db_connection):
        """Test successful audit report creation."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock database response
        mock_cursor.fetchall.return_value = [
            {
                'id': 'evidence-1',
                'file_path': 's3://test-bucket/evidence-1',
                'created_at': datetime.utcnow(),
                'hash': 'hash1',
                'evidence_type': 'photo',
                'session_id': 'session-1',
                'user_id': 'user-1'
            },
            {
                'id': 'evidence-2',
                'file_path': 's3://test-bucket/evidence-2',
                'created_at': datetime.utcnow(),
                'hash': 'hash2',
                'evidence_type': 'video',
                'session_id': 'session-2',
                'user_id': 'user-2'
            }
        ]
        
        # Mock S3 responses
        mock_s3_client.get_object_lock_configuration.return_value = {
            'ObjectLockConfiguration': {
                'ObjectLockEnabled': 'Enabled',
                'Rule': {
                    'DefaultRetention': {
                        'Mode': 'COMPLIANCE',
                        'Years': 7
                    }
                }
            }
        }
        
        mock_s3_client.get_object_retention.return_value = {
            'Retention': {
                'Mode': 'COMPLIANCE',
                'RetainUntilDate': datetime.utcnow() + timedelta(days=365 * 7)
            }
        }
        
        mock_s3_client.head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': datetime.utcnow(),
            'ServerSideEncryption': 'AES256',
            'ETag': '"test-etag"'
        }
        
        # Test audit report creation
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        report = verifier.create_audit_report(start_date, end_date)
        
        # Verify report structure
        assert isinstance(report, ComplianceReport)
        assert report.evidence_count == 2
        assert len(report.checks) > 0
        assert report.overall_compliance is True
        assert "Audit completed" in report.summary
        
        # Verify database query
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0][0]
        assert "SELECT e.id, e.file_path" in call_args
        assert "FROM evidence e" in call_args
    
    def test_create_audit_report_no_evidence(self, verifier, mock_s3_client, mock_db_connection):
        """Test audit report creation with no evidence."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock empty database response
        mock_cursor.fetchall.return_value = []
        
        # Mock S3 responses
        mock_s3_client.get_object_lock_configuration.return_value = {
            'ObjectLockConfiguration': {
                'ObjectLockEnabled': 'Enabled',
                'Rule': {
                    'DefaultRetention': {
                        'Mode': 'COMPLIANCE',
                        'Years': 7
                    }
                }
            }
        }
        
        # Test audit report creation
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        report = verifier.create_audit_report(start_date, end_date)
        
        assert report.evidence_count == 0
        assert len(report.checks) > 0
        assert report.overall_compliance is True
    
    def test_create_audit_report_error(self, verifier, mock_s3_client, mock_db_connection):
        """Test audit report creation with error."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock database error
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Test audit report creation
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        report = verifier.create_audit_report(start_date, end_date)
        
        assert report.evidence_count == 0
        assert report.overall_compliance is False
        assert "Audit report generation failed" in report.summary
        assert len(report.checks) == 1
        assert report.checks[0].check_name == "Report Generation"
        assert report.checks[0].passed is False
    
    @patch('src.app.services.compliance.worm_verifier.SimpleDocTemplate')
    @patch('src.app.services.compliance.worm_verifier.io.BytesIO')
    def test_generate_compliance_certificate_success(self, mock_bytes_io, mock_doc_template, verifier, mock_db_connection):
        """Test successful compliance certificate generation."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock database response
        mock_cursor.fetchall.return_value = [
            {
                'id': 'evidence-1',
                'evidence_type': 'photo',
                'created_at': datetime.utcnow(),
                'hash': 'hash1',
                'session_id': 'session-1'
            }
        ]
        
        # Mock PDF generation
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b"PDF content"
        mock_bytes_io.return_value = mock_buffer
        
        mock_doc = Mock()
        mock_doc_template.return_value = mock_doc
        
        # Test certificate generation
        evidence_ids = ["evidence-1"]
        pdf_bytes = verifier.generate_compliance_certificate(evidence_ids)
        
        # Verify result
        assert pdf_bytes == b"PDF content"
        mock_doc.build.assert_called_once()
        mock_buffer.close.assert_called_once()
    
    def test_generate_compliance_certificate_empty_list(self, verifier):
        """Test compliance certificate generation with empty evidence list."""
        # Test with empty list
        pdf_bytes = verifier.generate_compliance_certificate([])
        
        # Should still generate a certificate (even if empty)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_verify_evidence_compliance_success(self, verifier, mock_s3_client, mock_db_connection):
        """Test successful evidence compliance verification."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock database response
        mock_cursor.fetchone.return_value = {
            'id': 'evidence-1',
            'file_path': 's3://test-bucket/evidence-1',
            'created_at': datetime.utcnow(),
            'hash': 'hash1',
            'evidence_type': 'photo',
            'session_id': 'session-1'
        }
        
        # Mock S3 response
        mock_s3_client.get_object_retention.return_value = {
            'Retention': {
                'Mode': 'COMPLIANCE',
                'RetainUntilDate': datetime.utcnow() + timedelta(days=365 * 7)
            }
        }
        
        # Test verification
        result = verifier.verify_evidence_compliance("evidence-1")
        
        # Verify result
        assert result['evidence_id'] == "evidence-1"
        assert result['session_id'] == "session-1"
        assert result['evidence_type'] == "photo"
        assert result['file_path'] == "s3://test-bucket/evidence-1"
        assert result['hash'] == "hash1"
        assert result['compliant'] is True
        assert result['object_lock_verification'] is not None
    
    def test_verify_evidence_compliance_not_found(self, verifier, mock_db_connection):
        """Test evidence compliance verification for non-existent evidence."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock empty database response
        mock_cursor.fetchone.return_value = None
        
        # Test verification
        result = verifier.verify_evidence_compliance("nonexistent")
        
        assert result['evidence_id'] == "nonexistent"
        assert result['compliant'] is False
        assert result['error'] == "Evidence not found"
    
    def test_verify_evidence_compliance_no_file_path(self, verifier, mock_db_connection):
        """Test evidence compliance verification for evidence without file path."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock database response with no file path
        mock_cursor.fetchone.return_value = {
            'id': 'evidence-1',
            'file_path': None,
            'created_at': datetime.utcnow(),
            'hash': 'hash1',
            'evidence_type': 'photo',
            'session_id': 'session-1'
        }
        
        # Test verification
        result = verifier.verify_evidence_compliance("evidence-1")
        
        assert result['evidence_id'] == "evidence-1"
        assert result['compliant'] is False
        assert result['file_path'] is None
    
    def test_compliance_check_creation(self):
        """Test ComplianceCheck dataclass creation."""
        check = ComplianceCheck(
            check_name="Test Check",
            passed=True,
            details="Test details",
            timestamp=datetime.utcnow(),
            severity="INFO"
        )
        
        assert check.check_name == "Test Check"
        assert check.passed is True
        assert check.details == "Test details"
        assert check.severity == "INFO"
        assert isinstance(check.timestamp, datetime)
    
    def test_compliance_report_creation(self):
        """Test ComplianceReport dataclass creation."""
        checks = [
            ComplianceCheck(
                check_name="Test Check 1",
                passed=True,
                details="Test details 1",
                timestamp=datetime.utcnow(),
                severity="INFO"
            ),
            ComplianceCheck(
                check_name="Test Check 2",
                passed=False,
                details="Test details 2",
                timestamp=datetime.utcnow(),
                severity="ERROR"
            )
        ]
        
        report = ComplianceReport(
            report_id="test-report",
            generated_at=datetime.utcnow(),
            evidence_count=10,
            checks=checks,
            overall_compliance=False,
            summary="Test summary"
        )
        
        assert report.report_id == "test-report"
        assert report.evidence_count == 10
        assert len(report.checks) == 2
        assert report.overall_compliance is False
        assert report.summary == "Test summary"
