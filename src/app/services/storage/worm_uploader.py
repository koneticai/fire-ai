"""
WORM-compliant S3 uploader with Object Lock.

Provides secure, immutable storage for evidence and reports
with AS 1851-2012 compliance requirements.
"""

import boto3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from pathlib import Path
import os
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class WormStorageUploader:
    """Upload files to WORM-protected S3 with Object Lock."""
    
    def __init__(self, bucket_name: str, retention_years: int = 7, 
                 region: str = "us-east-1"):
        """
        Initialize WORM uploader.
        
        Args:
            bucket_name: Name of WORM-enabled S3 bucket
            retention_years: Retention period in years (default: 7)
            region: AWS region for S3 operations
        """
        self.bucket_name = bucket_name
        self.retention_years = retention_years
        self.region = region
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=region)
            logger.info(f"Initialized WORM uploader for bucket: {bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def upload_with_retention(self, file_path: Union[str, Path], s3_key: str, 
                             metadata: Optional[Dict[str, str]] = None,
                             content_type: Optional[str] = None) -> str:
        """
        Upload file with Object Lock retention.
        
        Args:
            file_path: Local file path or file-like object
            s3_key: S3 object key
            metadata: Optional metadata dictionary
            content_type: Optional content type
            
        Returns:
            S3 URI of uploaded object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ClientError: If S3 upload fails
        """
        try:
            # Calculate retention date (7 years from now)
            retention_date = datetime.utcnow() + timedelta(days=365 * self.retention_years)
            
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'ObjectLockMode': 'COMPLIANCE',
                'ObjectLockRetainUntilDate': retention_date,
                'ServerSideEncryption': 'AES256'
            }
            
            # Add metadata if provided
            if metadata:
                upload_params['Metadata'] = metadata
            
            # Add content type if provided
            if content_type:
                upload_params['ContentType'] = content_type
            
            # Handle file path or file-like object
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                with open(file_path, 'rb') as f:
                    upload_params['Body'] = f
                    response = self.s3_client.put_object(**upload_params)
            else:
                # Assume file-like object
                upload_params['Body'] = file_path
                response = self.s3_client.put_object(**upload_params)
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Successfully uploaded {s3_key} to WORM storage with retention until {retention_date}")
            
            return s3_uri
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 upload failed for {s3_key}: {error_code} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading {s3_key}: {e}")
            raise
    
    def upload_from_memory(self, data: bytes, s3_key: str,
                          metadata: Optional[Dict[str, str]] = None,
                          content_type: Optional[str] = None) -> str:
        """
        Upload data from memory with Object Lock retention.
        
        Args:
            data: Binary data to upload
            s3_key: S3 object key
            metadata: Optional metadata dictionary
            content_type: Optional content type
            
        Returns:
            S3 URI of uploaded object
        """
        try:
            # Calculate retention date
            retention_date = datetime.utcnow() + timedelta(days=365 * self.retention_years)
            
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'Body': data,
                'ObjectLockMode': 'COMPLIANCE',
                'ObjectLockRetainUntilDate': retention_date,
                'ServerSideEncryption': 'AES256'
            }
            
            if metadata:
                upload_params['Metadata'] = metadata
            
            if content_type:
                upload_params['ContentType'] = content_type
            
            response = self.s3_client.put_object(**upload_params)
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Successfully uploaded {s3_key} from memory to WORM storage")
            
            return s3_uri
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 upload from memory failed for {s3_key}: {error_code} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading from memory {s3_key}: {e}")
            raise
    
    def verify_immutability(self, s3_key: str) -> Dict[str, Any]:
        """
        Verify object is immutable and properly configured.
        
        Args:
            s3_key: S3 object key to verify
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Get Object Lock configuration
            retention_response = self.s3_client.get_object_retention(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Get object metadata
            head_response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            retention_config = retention_response['Retention']
            retain_until = retention_config['RetainUntilDate']
            mode = retention_config['Mode']
            
            # Check if retention is still active
            is_retained = datetime.utcnow() < retain_until.replace(tzinfo=None)
            
            # Check encryption
            is_encrypted = head_response.get('ServerSideEncryption') == 'AES256'
            
            result = {
                's3_key': s3_key,
                'is_immutable': is_retained and mode == 'COMPLIANCE',
                'retention_mode': mode,
                'retain_until': retain_until.isoformat(),
                'is_retained': is_retained,
                'is_encrypted': is_encrypted,
                'file_size': head_response.get('ContentLength', 0),
                'last_modified': head_response.get('LastModified'),
                'etag': head_response.get('ETag', '').strip('"')
            }
            
            logger.info(f"Immutability verification for {s3_key}: {result['is_immutable']}")
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.error(f"Object not found: {s3_key}")
                return {
                    's3_key': s3_key,
                    'is_immutable': False,
                    'error': 'Object not found'
                }
            else:
                logger.error(f"Failed to verify immutability for {s3_key}: {error_code} - {e}")
                return {
                    's3_key': s3_key,
                    'is_immutable': False,
                    'error': str(e)
                }
        except Exception as e:
            logger.error(f"Unexpected error verifying immutability for {s3_key}: {e}")
            return {
                's3_key': s3_key,
                'is_immutable': False,
                'error': str(e)
            }
    
    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for reading WORM-protected object.
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL for object access
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for {s3_key} (expires in {expiration}s)")
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to generate presigned URL for {s3_key}: {error_code} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL for {s3_key}: {e}")
            raise
    
    def check_bucket_compliance(self) -> Dict[str, Any]:
        """
        Check if bucket is properly configured for WORM compliance.
        
        Returns:
            Dictionary with compliance check results
        """
        try:
            # Check Object Lock configuration
            lock_config = self.s3_client.get_object_lock_configuration(
                Bucket=self.bucket_name
            )
            
            # Check encryption configuration
            encryption_config = self.s3_client.get_bucket_encryption(
                Bucket=self.bucket_name
            )
            
            # Check versioning
            versioning_config = self.s_client.get_bucket_versioning(
                Bucket=self.bucket_name
            )
            
            # Check public access block
            public_access_config = self.s3_client.get_public_access_block(
                Bucket=self.bucket_name
            )
            
            result = {
                'bucket_name': self.bucket_name,
                'object_lock_enabled': lock_config.get('ObjectLockConfiguration', {}).get('ObjectLockEnabled') == 'Enabled',
                'encryption_enabled': len(encryption_config.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])) > 0,
                'versioning_enabled': versioning_config.get('Status') == 'Enabled',
                'public_access_blocked': all(
                    public_access_config.get('PublicAccessBlockConfiguration', {}).values()
                ),
                'compliance_status': 'COMPLIANT'
            }
            
            # Determine overall compliance
            if not all([
                result['object_lock_enabled'],
                result['encryption_enabled'],
                result['versioning_enabled'],
                result['public_access_blocked']
            ]):
                result['compliance_status'] = 'NON_COMPLIANT'
            
            logger.info(f"Bucket compliance check for {self.bucket_name}: {result['compliance_status']}")
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to check bucket compliance for {self.bucket_name}: {error_code} - {e}")
            return {
                'bucket_name': self.bucket_name,
                'compliance_status': 'ERROR',
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error checking bucket compliance for {self.bucket_name}: {e}")
            return {
                'bucket_name': self.bucket_name,
                'compliance_status': 'ERROR',
                'error': str(e)
            }
    
    def get_retention_info(self, s3_key: str) -> Dict[str, Any]:
        """
        Get detailed retention information for an object.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Dictionary with retention information
        """
        try:
            response = self.s3_client.get_object_retention(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            retention = response['Retention']
            retain_until = retention['RetainUntilDate']
            
            # Calculate time remaining
            now = datetime.utcnow()
            time_remaining = retain_until.replace(tzinfo=None) - now
            
            result = {
                's3_key': s3_key,
                'mode': retention['Mode'],
                'retain_until': retain_until.isoformat(),
                'time_remaining_days': time_remaining.days,
                'time_remaining_hours': time_remaining.total_seconds() / 3600,
                'is_active': time_remaining.total_seconds() > 0
            }
            
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to get retention info for {s3_key}: {error_code} - {e}")
            return {
                's3_key': s3_key,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error getting retention info for {s3_key}: {e}")
            return {
                's3_key': s3_key,
                'error': str(e)
            }
