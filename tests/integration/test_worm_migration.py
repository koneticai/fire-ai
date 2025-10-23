"""
Integration tests for WORM migration pipeline.
"""

import pytest
import boto3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from scripts.migrate_to_worm import WormMigrationPipeline, MigrationProgress, MigrationResult


class TestWormMigrationPipeline:
    """Integration tests for WORM migration pipeline."""
    
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
    def temp_file(self):
        """Create temporary file for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content for migration")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def pipeline(self, mock_s3_client, mock_db_connection):
        """Create WormMigrationPipeline instance."""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'}):
            return WormMigrationPipeline(
                source_bucket="test-source-bucket",
                dest_bucket="test-dest-bucket",
                batch_size=10,
                dry_run=False,
                max_workers=2
            )
    
    def test_init(self, mock_s3_client, mock_db_connection):
        """Test WormMigrationPipeline initialization."""
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test'}):
            pipeline = WormMigrationPipeline(
                source_bucket="source",
                dest_bucket="dest",
                batch_size=100,
                dry_run=True
            )
            
            assert pipeline.source_bucket == "source"
            assert pipeline.dest_bucket == "dest"
            assert pipeline.batch_size == 100
            assert pipeline.dry_run is True
            assert pipeline.max_workers == 10  # Default
    
    def test_list_all_objects(self, pipeline, mock_s3_client):
        """Test listing all objects in source bucket."""
        # Mock paginated response
        mock_s3_client.get_paginator.return_value.paginate.return_value = [
            {
                'Contents': [
                    {
                        'Key': 'evidence/file1.jpg',
                        'Size': 1024,
                        'LastModified': datetime.utcnow(),
                        'ETag': '"etag1"'
                    },
                    {
                        'Key': 'evidence/file2.pdf',
                        'Size': 2048,
                        'LastModified': datetime.utcnow(),
                        'ETag': '"etag2"'
                    }
                ]
            },
            {
                'Contents': [
                    {
                        'Key': 'evidence/file3.mp4',
                        'Size': 4096,
                        'LastModified': datetime.utcnow(),
                        'ETag': '"etag3"'
                    }
                ]
            }
        ]
        
        # Test listing objects
        objects = pipeline._list_all_objects()
        
        # Verify result
        assert len(objects) == 3
        assert objects[0]['Key'] == 'evidence/file1.jpg'
        assert objects[0]['Size'] == 1024
        assert objects[1]['Key'] == 'evidence/file2.pdf'
        assert objects[2]['Key'] == 'evidence/file3.mp4'
        
        # Verify S3 call
        mock_s3_client.get_paginator.assert_called_once_with('list_objects_v2')
    
    def test_simulate_migration(self, pipeline, mock_s3_client):
        """Test migration simulation (dry run)."""
        # Create dry run pipeline
        dry_run_pipeline = WormMigrationPipeline(
            source_bucket="source",
            dest_bucket="dest",
            dry_run=True
        )
        
        # Mock objects
        objects = [
            {'Key': 'file1.jpg', 'Size': 1024},
            {'Key': 'file2.pdf', 'Size': 2048},
            {'Key': 'file3.mp4', 'Size': 4096}
        ]
        
        # Test simulation
        result = dry_run_pipeline._simulate_migration(objects)
        
        # Verify result
        assert result['total_files'] == 3
        assert result['successful_files'] == 3
        assert result['failed_files'] == 0
        assert result['total_size_bytes'] == 7168  # 1024 + 2048 + 4096
        assert result['estimated_time_minutes'] > 0
    
    def test_migrate_single_object_success(self, pipeline, mock_s3_client):
        """Test successful single object migration."""
        # Mock object
        obj = {
            'Key': 'evidence/file1.jpg',
            'Size': 1024,
            'LastModified': datetime.utcnow(),
            'ETag': '"etag1"'
        }
        
        # Mock S3 copy response
        mock_s3_client.copy_object.return_value = {'ETag': '"new-etag"'}
        
        # Mock head object responses for checksum verification
        mock_s3_client.head_object.side_effect = [
            {'ETag': '"etag1"'},  # Source
            {'ETag': '"etag1"'}   # Destination (same ETag)
        ]
        
        # Test migration
        result = pipeline._migrate_single_object(obj)
        
        # Verify result
        assert result.source_key == 'evidence/file1.jpg'
        assert result.dest_key == 'evidence/file1.jpg'
        assert result.success is True
        assert result.checksum_match is True
        assert result.file_size == 1024
        assert result.error_message is None
        
        # Verify S3 copy call
        mock_s3_client.copy_object.assert_called_once()
        call_args = mock_s3_client.copy_object.call_args
        
        assert call_args[1]['Bucket'] == 'test-dest-bucket'
        assert call_args[1]['Key'] == 'evidence/file1.jpg'
        assert call_args[1]['ObjectLockMode'] == 'COMPLIANCE'
        assert call_args[1]['ServerSideEncryption'] == 'AES256'
        assert 'ObjectLockRetainUntilDate' in call_args[1]
    
    def test_migrate_single_object_checksum_mismatch(self, pipeline, mock_s3_client):
        """Test single object migration with checksum mismatch."""
        # Mock object
        obj = {
            'Key': 'evidence/file1.jpg',
            'Size': 1024,
            'LastModified': datetime.utcnow(),
            'ETag': '"etag1"'
        }
        
        # Mock S3 copy response
        mock_s3_client.copy_object.return_value = {'ETag': '"new-etag"'}
        
        # Mock head object responses with different ETags
        mock_s3_client.head_object.side_effect = [
            {'ETag': '"etag1"'},  # Source
            {'ETag': '"different-etag"'}   # Destination (different ETag)
        ]
        
        # Test migration
        result = pipeline._migrate_single_object(obj)
        
        # Verify result
        assert result.success is True
        assert result.checksum_match is False
    
    def test_migrate_single_object_s3_error(self, pipeline, mock_s3_client):
        """Test single object migration with S3 error."""
        # Mock object
        obj = {
            'Key': 'evidence/file1.jpg',
            'Size': 1024,
            'LastModified': datetime.utcnow(),
            'ETag': '"etag1"'
        }
        
        # Mock S3 error
        from botocore.exceptions import ClientError
        mock_s3_client.copy_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'CopyObject'
        )
        
        # Test migration
        result = pipeline._migrate_single_object(obj)
        
        # Verify result
        assert result.success is False
        assert result.checksum_match is False
        assert "Access Denied" in result.error_message
    
    def test_verify_checksum_success(self, pipeline, mock_s3_client):
        """Test successful checksum verification."""
        # Mock head object responses with matching ETags
        mock_s3_client.head_object.side_effect = [
            {'ETag': '"etag1"'},  # Source
            {'ETag': '"etag1"'}   # Destination
        ]
        
        # Test checksum verification
        result = pipeline._verify_checksum('source-key', 'dest-key')
        
        # Verify result
        assert result is True
        
        # Verify S3 calls
        assert mock_s3_client.head_object.call_count == 2
        calls = mock_s3_client.head_object.call_args_list
        
        assert calls[0][1]['Bucket'] == 'test-source-bucket'
        assert calls[0][1]['Key'] == 'source-key'
        assert calls[1][1]['Bucket'] == 'test-dest-bucket'
        assert calls[1][1]['Key'] == 'dest-key'
    
    def test_verify_checksum_mismatch(self, pipeline, mock_s3_client):
        """Test checksum verification with mismatch."""
        # Mock head object responses with different ETags
        mock_s3_client.head_object.side_effect = [
            {'ETag': '"etag1"'},  # Source
            {'ETag': '"etag2"'}   # Destination
        ]
        
        # Test checksum verification
        result = pipeline._verify_checksum('source-key', 'dest-key')
        
        # Verify result
        assert result is False
    
    def test_verify_checksum_error(self, pipeline, mock_s3_client):
        """Test checksum verification with error."""
        # Mock S3 error
        from botocore.exceptions import ClientError
        mock_s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}},
            'HeadObject'
        )
        
        # Test checksum verification
        result = pipeline._verify_checksum('source-key', 'dest-key')
        
        # Verify result
        assert result is False
    
    def test_update_database_paths_success(self, pipeline, mock_db_connection):
        """Test successful database path update."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Test database update
        result = pipeline._update_database_paths('old/path', 'new/path')
        
        # Verify result
        assert result is True
        
        # Verify database calls
        assert mock_cursor.execute.call_count == 2  # evidence and reports tables
        
        # Verify evidence table update
        evidence_call = mock_cursor.execute.call_args_list[0]
        assert "UPDATE evidence" in evidence_call[0][0]
        assert "file_path = %s" in evidence_call[0][0]
        
        # Verify reports table update
        reports_call = mock_cursor.execute.call_args_list[1]
        assert "UPDATE reports" in reports_call[0][0]
        
        # Verify commit
        mock_conn.commit.assert_called_once()
    
    def test_update_database_paths_error(self, pipeline, mock_db_connection):
        """Test database path update with error."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock database error
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Test database update
        result = pipeline._update_database_paths('old/path', 'new/path')
        
        # Verify result
        assert result is False
        
        # Verify rollback
        mock_conn.rollback.assert_called_once()
    
    def test_migrate_batch_success(self, pipeline, mock_s3_client, mock_db_connection):
        """Test successful batch migration."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock objects
        objects = [
            {'Key': 'file1.jpg', 'Size': 1024, 'LastModified': datetime.utcnow(), 'ETag': '"etag1"'},
            {'Key': 'file2.pdf', 'Size': 2048, 'LastModified': datetime.utcnow(), 'ETag': '"etag2"'}
        ]
        
        # Mock S3 responses
        mock_s3_client.copy_object.return_value = {'ETag': '"new-etag"'}
        mock_s3_client.head_object.return_value = {'ETag': '"etag1"'}
        
        # Test batch migration
        success_count, failure_count = pipeline.migrate_batch(objects)
        
        # Verify result
        assert success_count == 2
        assert failure_count == 0
        
        # Verify S3 calls
        assert mock_s3_client.copy_object.call_count == 2
        assert mock_s3_client.head_object.call_count == 4  # 2 objects * 2 calls each
    
    def test_migrate_batch_partial_failure(self, pipeline, mock_s3_client, mock_db_connection):
        """Test batch migration with partial failures."""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock objects
        objects = [
            {'Key': 'file1.jpg', 'Size': 1024, 'LastModified': datetime.utcnow(), 'ETag': '"etag1"'},
            {'Key': 'file2.pdf', 'Size': 2048, 'LastModified': datetime.utcnow(), 'ETag': '"etag2"'}
        ]
        
        # Mock S3 responses - first succeeds, second fails
        def copy_object_side_effect(*args, **kwargs):
            if 'file1.jpg' in kwargs.get('Key', ''):
                return {'ETag': '"new-etag"'}
            else:
                from botocore.exceptions import ClientError
                raise ClientError(
                    {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
                    'CopyObject'
                )
        
        mock_s3_client.copy_object.side_effect = copy_object_side_effect
        mock_s3_client.head_object.return_value = {'ETag': '"etag1"'}
        
        # Test batch migration
        success_count, failure_count = pipeline.migrate_batch(objects)
        
        # Verify result
        assert success_count == 1
        assert failure_count == 1
    
    def test_save_and_load_progress(self, pipeline):
        """Test progress saving and loading."""
        # Create test progress
        progress = {
            "total_files": 100,
            "processed_files": 50,
            "successful_files": 45,
            "failed_files": 5,
            "current_batch": 5,
            "total_batches": 10
        }
        
        # Save progress
        pipeline.save_progress(progress)
        
        # Verify file was created
        assert pipeline.progress_file.exists()
        
        # Load progress
        loaded_progress = pipeline.load_progress()
        
        # Verify loaded progress
        assert loaded_progress["total_files"] == 100
        assert loaded_progress["processed_files"] == 50
        assert loaded_progress["successful_files"] == 45
        assert loaded_progress["failed_files"] == 5
        assert loaded_progress["current_batch"] == 5
        assert loaded_progress["total_batches"] == 10
        
        # Cleanup
        pipeline.progress_file.unlink()
    
    def test_migration_progress_dataclass(self):
        """Test MigrationProgress dataclass."""
        progress = MigrationProgress(
            total_files=100,
            processed_files=50,
            successful_files=45,
            failed_files=5,
            start_time=datetime.utcnow(),
            batch_size=10,
            current_batch=5,
            total_batches=10
        )
        
        assert progress.total_files == 100
        assert progress.processed_files == 50
        assert progress.successful_files == 45
        assert progress.failed_files == 5
        assert progress.batch_size == 10
        assert progress.current_batch == 5
        assert progress.total_batches == 10
        assert isinstance(progress.start_time, datetime)
    
    def test_migration_result_dataclass(self):
        """Test MigrationResult dataclass."""
        result = MigrationResult(
            source_key="source/key",
            dest_key="dest/key",
            success=True,
            checksum_match=True,
            file_size=1024,
            migration_time=1.5
        )
        
        assert result.source_key == "source/key"
        assert result.dest_key == "dest/key"
        assert result.success is True
        assert result.checksum_match is True
        assert result.file_size == 1024
        assert result.migration_time == 1.5
        assert result.error_message is None
    
    def test_migration_result_with_error(self):
        """Test MigrationResult dataclass with error."""
        result = MigrationResult(
            source_key="source/key",
            dest_key="dest/key",
            success=False,
            checksum_match=False,
            error_message="S3 error",
            file_size=1024,
            migration_time=0.5
        )
        
        assert result.source_key == "source/key"
        assert result.dest_key == "dest/key"
        assert result.success is False
        assert result.checksum_match is False
        assert result.error_message == "S3 error"
        assert result.file_size == 1024
        assert result.migration_time == 0.5
