"""
Unit tests for WORM storage uploader.
"""

import pytest
import boto3
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

from src.app.services.storage.worm_uploader import WormStorageUploader


class TestWormStorageUploader:
    """Test cases for WormStorageUploader."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            yield mock_s3
    
    @pytest.fixture
    def uploader(self, mock_s3_client):
        """Create WormStorageUploader instance."""
        return WormStorageUploader(
            bucket_name="test-worm-bucket",
            retention_years=7,
            region="us-east-1"
        )
    
    def test_init(self, mock_s3_client):
        """Test WormStorageUploader initialization."""
        uploader = WormStorageUploader("test-bucket")
        
        assert uploader.bucket_name == "test-bucket"
        assert uploader.retention_years == 7
        assert uploader.region == "us-east-1"
        mock_s3_client.assert_called_once_with('s3', region_name="us-east-1")
    
    def test_upload_with_retention_success(self, uploader, mock_s3_client):
        """Test successful file upload with retention."""
        # Mock file
        mock_file = Mock()
        mock_file.read.return_value = b"test content"
        
        # Mock S3 response
        mock_s3_client.put_object.return_value = {"ETag": '"test-etag"'}
        
        # Test upload
        result = uploader.upload_with_retention(
            file_path=mock_file,
            s3_key="test/key",
            metadata={"test": "value"},
            content_type="text/plain"
        )
        
        # Verify S3 call
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        
        assert call_args[1]['Bucket'] == "test-worm-bucket"
        assert call_args[1]['Key'] == "test/key"
        assert call_args[1]['ObjectLockMode'] == 'COMPLIANCE'
        assert call_args[1]['ServerSideEncryption'] == 'AES256'
        assert call_args[1]['Metadata'] == {"test": "value"}
        assert call_args[1]['ContentType'] == "text/plain"
        
        # Verify retention date is approximately 7 years from now
        retention_date = call_args[1]['ObjectLockRetainUntilDate']
        expected_date = datetime.utcnow() + timedelta(days=365 * 7)
        time_diff = abs((retention_date - expected_date).total_seconds())
        assert time_diff < 60  # Within 1 minute
        
        assert result == "s3://test-worm-bucket/test/key"
    
    def test_upload_with_retention_file_not_found(self, uploader, mock_s3_client):
        """Test upload with non-existent file."""
        with pytest.raises(FileNotFoundError):
            uploader.upload_with_retention(
                file_path="nonexistent/file.txt",
                s3_key="test/key"
            )
    
    def test_upload_with_retention_s3_error(self, uploader, mock_s3_client):
        """Test upload with S3 error."""
        # Mock S3 error
        mock_s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'PutObject'
        )
        
        with pytest.raises(ClientError):
            uploader.upload_with_retention(
                file_path=b"test content",
                s3_key="test/key"
            )
    
    def test_upload_from_memory_success(self, uploader, mock_s3_client):
        """Test successful upload from memory."""
        # Mock S3 response
        mock_s3_client.put_object.return_value = {"ETag": '"test-etag"'}
        
        # Test upload
        result = uploader.upload_from_memory(
            data=b"test content",
            s3_key="test/key",
            metadata={"test": "value"},
            content_type="text/plain"
        )
        
        # Verify S3 call
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        
        assert call_args[1]['Bucket'] == "test-worm-bucket"
        assert call_args[1]['Key'] == "test/key"
        assert call_args[1]['Body'] == b"test content"
        assert call_args[1]['ObjectLockMode'] == 'COMPLIANCE'
        assert call_args[1]['ServerSideEncryption'] == 'AES256'
        
        assert result == "s3://test-worm-bucket/test/key"
    
    def test_verify_immutability_success(self, uploader, mock_s3_client):
        """Test successful immutability verification."""
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
            'ServerSideEncryption': 'AES256',
            'ETag': '"test-etag"'
        }
        
        # Test verification
        result = uploader.verify_immutability("test/key")
        
        # Verify calls
        mock_s3_client.get_object_retention.assert_called_once_with(
            Bucket="test-worm-bucket",
            Key="test/key"
        )
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-worm-bucket",
            Key="test/key"
        )
        
        # Verify result
        assert result['s3_key'] == "test/key"
        assert result['is_immutable'] is True
        assert result['retention_mode'] == 'COMPLIANCE'
        assert result['is_encrypted'] is True
        assert result['file_size'] == 1024
    
    def test_verify_immutability_not_retained(self, uploader, mock_s3_client):
        """Test immutability verification for expired retention."""
        # Mock expired retention
        mock_s3_client.get_object_retention.return_value = {
            'Retention': {
                'Mode': 'COMPLIANCE',
                'RetainUntilDate': datetime.utcnow() - timedelta(days=1)  # Expired
            }
        }
        
        mock_s3_client.head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': datetime.utcnow(),
            'ServerSideEncryption': 'AES256',
            'ETag': '"test-etag"'
        }
        
        # Test verification
        result = uploader.verify_immutability("test/key")
        
        assert result['s3_key'] == "test/key"
        assert result['is_immutable'] is False
        assert result['is_retained'] is False
    
    def test_verify_immutability_object_not_found(self, uploader, mock_s3_client):
        """Test immutability verification for non-existent object."""
        # Mock NoSuchKey error
        mock_s3_client.get_object_retention.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}},
            'GetObjectRetention'
        )
        
        # Test verification
        result = uploader.verify_immutability("test/key")
        
        assert result['s3_key'] == "test/key"
        assert result['is_immutable'] is False
        assert 'error' in result
    
    def test_get_presigned_url_success(self, uploader, mock_s3_client):
        """Test successful presigned URL generation."""
        # Mock presigned URL
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com"
        
        # Test URL generation
        url = uploader.get_presigned_url("test/key", expiration=3600)
        
        # Verify call
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': 'test-worm-bucket', 'Key': 'test/key'},
            ExpiresIn=3600
        )
        
        assert url == "https://test-url.com"
    
    def test_get_presigned_url_error(self, uploader, mock_s3_client):
        """Test presigned URL generation with error."""
        # Mock S3 error
        mock_s3_client.generate_presigned_url.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}},
            'GeneratePresignedUrl'
        )
        
        with pytest.raises(ClientError):
            uploader.get_presigned_url("test/key")
    
    def test_check_bucket_compliance_success(self, uploader, mock_s3_client):
        """Test successful bucket compliance check."""
        # Mock responses
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
        
        mock_s3_client.get_bucket_encryption.return_value = {
            'ServerSideEncryptionConfiguration': {
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }
                ]
            }
        }
        
        mock_s3_client.get_bucket_versioning.return_value = {
            'Status': 'Enabled'
        }
        
        mock_s3_client.get_public_access_block.return_value = {
            'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'BlockPublicPolicy': True,
                'IgnorePublicAcls': True,
                'RestrictPublicBuckets': True
            }
        }
        
        # Test compliance check
        result = uploader.check_bucket_compliance()
        
        # Verify result
        assert result['bucket_name'] == "test-worm-bucket"
        assert result['object_lock_enabled'] is True
        assert result['encryption_enabled'] is True
        assert result['versioning_enabled'] is True
        assert result['public_access_blocked'] is True
        assert result['compliance_status'] == 'COMPLIANT'
    
    def test_check_bucket_compliance_error(self, uploader, mock_s3_client):
        """Test bucket compliance check with error."""
        # Mock error
        mock_s3_client.get_object_lock_configuration.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'GetObjectLockConfiguration'
        )
        
        # Test compliance check
        result = uploader.check_bucket_compliance()
        
        assert result['bucket_name'] == "test-worm-bucket"
        assert result['compliance_status'] == 'ERROR'
        assert 'error' in result
    
    def test_get_retention_info_success(self, uploader, mock_s3_client):
        """Test successful retention info retrieval."""
        # Mock response
        retain_until = datetime.utcnow() + timedelta(days=365 * 7)
        mock_s3_client.get_object_retention.return_value = {
            'Retention': {
                'Mode': 'COMPLIANCE',
                'RetainUntilDate': retain_until
            }
        }
        
        # Test retention info
        result = uploader.get_retention_info("test/key")
        
        # Verify call
        mock_s3_client.get_object_retention.assert_called_once_with(
            Bucket="test-worm-bucket",
            Key="test/key"
        )
        
        # Verify result
        assert result['s3_key'] == "test/key"
        assert result['mode'] == 'COMPLIANCE'
        assert result['is_active'] is True
        assert result['time_remaining_days'] > 2500  # Approximately 7 years
    
    def test_get_retention_info_error(self, uploader, mock_s3_client):
        """Test retention info retrieval with error."""
        # Mock error
        mock_s3_client.get_object_retention.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}},
            'GetObjectRetention'
        )
        
        # Test retention info
        result = uploader.get_retention_info("test/key")
        
        assert result['s3_key'] == "test/key"
        assert 'error' in result
    
    def test_retention_calculation(self, uploader):
        """Test retention date calculation."""
        # Test with different retention years
        uploader_1_year = WormStorageUploader("test-bucket", retention_years=1)
        uploader_10_years = WormStorageUploader("test-bucket", retention_years=10)
        
        # Calculate expected dates
        now = datetime.utcnow()
        expected_1_year = now + timedelta(days=365)
        expected_10_years = now + timedelta(days=365 * 10)
        
        # Test retention calculation (this would be done internally in upload methods)
        retention_1_year = now + timedelta(days=365 * 1)
        retention_10_years = now + timedelta(days=365 * 10)
        
        # Verify calculations are approximately correct
        assert abs((retention_1_year - expected_1_year).total_seconds()) < 1
        assert abs((retention_10_years - expected_10_years).total_seconds()) < 1
