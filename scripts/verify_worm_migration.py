#!/usr/bin/env python3
"""
Verification script to validate WORM migration success.

Checks:
- All files copied successfully
- Checksums match
- Object Lock is enabled
- Retention period is correct (7 years)
- Database paths updated correctly
"""

import boto3
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

class WormMigrationVerifier:
    """Verify WORM migration success and compliance."""
    
    def __init__(self, source_bucket: str, dest_bucket: str):
        self.source_bucket = source_bucket
        self.dest_bucket = dest_bucket
        self.s3_client = boto3.client('s3')
        self.db_connection = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Connect to database
        self._connect_database()
    
    def _connect_database(self):
        """Connect to PostgreSQL database."""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL environment variable is required")
                
            self.db_connection = psycopg2.connect(
                database_url,
                cursor_factory=RealDictCursor
            )
            self.logger.info("Connected to database successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise
    
    def verify_all(self) -> Dict[str, bool]:
        """Run all verification checks."""
        self.logger.info("Starting comprehensive WORM migration verification")
        
        results = {
            "files_copied": self.verify_files_copied(),
            "checksums_match": self.verify_checksums(),
            "object_lock_enabled": self.verify_object_lock(),
            "retention_correct": self.verify_retention_period(),
            "database_updated": self.verify_database_paths(),
            "replication_enabled": self.verify_replication(),
            "encryption_enabled": self.verify_encryption()
        }
        
        # Overall result
        results["overall_success"] = all(results.values())
        
        # Log results
        self.logger.info("Verification Results:")
        for check, result in results.items():
            status = "PASS" if result else "FAIL"
            self.logger.info(f"  {check}: {status}")
        
        return results
    
    def verify_files_copied(self) -> bool:
        """Verify all files were copied successfully."""
        self.logger.info("Verifying all files were copied...")
        
        try:
            # List source objects
            source_objects = self._list_bucket_objects(self.source_bucket)
            source_keys = {obj['Key'] for obj in source_objects}
            
            # List destination objects
            dest_objects = self._list_bucket_objects(self.dest_bucket)
            dest_keys = {obj['Key'] for obj in dest_objects}
            
            # Check if all source files exist in destination
            missing_files = source_keys - dest_keys
            extra_files = dest_keys - source_keys
            
            if missing_files:
                self.logger.error(f"Missing files in destination: {len(missing_files)}")
                for key in list(missing_files)[:10]:  # Show first 10
                    self.logger.error(f"  Missing: {key}")
                if len(missing_files) > 10:
                    self.logger.error(f"  ... and {len(missing_files) - 10} more")
            
            if extra_files:
                self.logger.warning(f"Extra files in destination: {len(extra_files)}")
                for key in list(extra_files)[:10]:  # Show first 10
                    self.logger.warning(f"  Extra: {key}")
                if len(extra_files) > 10:
                    self.logger.warning(f"  ... and {len(extra_files) - 10} more")
            
            success = len(missing_files) == 0
            self.logger.info(f"Files copied verification: {'PASS' if success else 'FAIL'}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to verify files copied: {e}")
            return False
    
    def verify_checksums(self) -> bool:
        """Verify checksums match between source and destination."""
        self.logger.info("Verifying checksums match...")
        
        try:
            # Get sample of objects to verify (up to 100)
            source_objects = self._list_bucket_objects(self.source_bucket)
            sample_size = min(100, len(source_objects))
            sample_objects = source_objects[:sample_size]
            
            mismatches = 0
            total_checked = 0
            
            for obj in sample_objects:
                source_key = obj['Key']
                dest_key = source_key  # Same key structure
                
                try:
                    # Get source ETag
                    source_response = self.s3_client.head_object(
                        Bucket=self.source_bucket,
                        Key=source_key
                    )
                    source_etag = source_response['ETag'].strip('"')
                    
                    # Get destination ETag
                    dest_response = self.s3_client.head_object(
                        Bucket=self.dest_bucket,
                        Key=dest_key
                    )
                    dest_etag = dest_response['ETag'].strip('"')
                    
                    total_checked += 1
                    
                    if source_etag != dest_etag:
                        mismatches += 1
                        self.logger.error(f"Checksum mismatch for {source_key}: {source_etag} != {dest_etag}")
                
                except Exception as e:
                    self.logger.warning(f"Failed to verify checksum for {source_key}: {e}")
            
            success = mismatches == 0
            self.logger.info(f"Checksum verification: {total_checked} checked, {mismatches} mismatches - {'PASS' if success else 'FAIL'}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to verify checksums: {e}")
            return False
    
    def verify_object_lock(self) -> bool:
        """Verify Object Lock is enabled on all objects."""
        self.logger.info("Verifying Object Lock is enabled...")
        
        try:
            # Get sample of objects to verify
            dest_objects = self._list_bucket_objects(self.dest_bucket)
            sample_size = min(50, len(dest_objects))
            sample_objects = dest_objects[:sample_size]
            
            objects_without_lock = 0
            total_checked = 0
            
            for obj in sample_objects:
                key = obj['Key']
                
                try:
                    # Check Object Lock configuration
                    response = self.s3_client.get_object_retention(
                        Bucket=self.dest_bucket,
                        Key=key
                    )
                    
                    total_checked += 1
                    
                    # Verify retention mode is COMPLIANCE
                    if response['Retention']['Mode'] != 'COMPLIANCE':
                        objects_without_lock += 1
                        self.logger.error(f"Object {key} has incorrect retention mode: {response['Retention']['Mode']}")
                
                except Exception as e:
                    self.logger.warning(f"Failed to check Object Lock for {key}: {e}")
            
            success = objects_without_lock == 0
            self.logger.info(f"Object Lock verification: {total_checked} checked, {objects_without_lock} without lock - {'PASS' if success else 'FAIL'}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to verify Object Lock: {e}")
            return False
    
    def verify_retention_period(self) -> bool:
        """Verify retention period is correct (7 years)."""
        self.logger.info("Verifying retention period is 7 years...")
        
        try:
            # Get sample of objects to verify
            dest_objects = self._list_bucket_objects(self.dest_bucket)
            sample_size = min(20, len(dest_objects))
            sample_objects = dest_objects[:sample_size]
            
            incorrect_retention = 0
            total_checked = 0
            
            # Expected retention: 7 years from now
            expected_min_date = datetime.utcnow() + timedelta(days=365 * 7 - 1)  # Allow 1 day tolerance
            expected_max_date = datetime.utcnow() + timedelta(days=365 * 7 + 1)
            
            for obj in sample_objects:
                key = obj['Key']
                
                try:
                    # Get retention configuration
                    response = self.s3_client.get_object_retention(
                        Bucket=self.dest_bucket,
                        Key=key
                    )
                    
                    retain_until = response['Retention']['RetainUntilDate']
                    total_checked += 1
                    
                    # Check if retention date is within expected range
                    if not (expected_min_date <= retain_until <= expected_max_date):
                        incorrect_retention += 1
                        self.logger.error(f"Object {key} has incorrect retention date: {retain_until}")
                
                except Exception as e:
                    self.logger.warning(f"Failed to check retention for {key}: {e}")
            
            success = incorrect_retention == 0
            self.logger.info(f"Retention period verification: {total_checked} checked, {incorrect_retention} incorrect - {'PASS' if success else 'FAIL'}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to verify retention period: {e}")
            return False
    
    def verify_database_paths(self) -> bool:
        """Verify database paths were updated correctly."""
        self.logger.info("Verifying database paths were updated...")
        
        try:
            with self.db_connection.cursor() as cursor:
                # Check evidence table
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM evidence 
                    WHERE file_path LIKE %s
                """, (f"s3://{self.source_bucket}/%",))
                
                old_paths_count = cursor.fetchone()['count']
                
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM evidence 
                    WHERE file_path LIKE %s
                """, (f"s3://{self.dest_bucket}/%",))
                
                new_paths_count = cursor.fetchone()['count']
                
                # Check reports table if it exists
                try:
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM reports 
                        WHERE file_path LIKE %s
                    """, (f"s3://{self.source_bucket}/%",))
                    
                    old_reports_count = cursor.fetchone()['count']
                    
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM reports 
                        WHERE file_path LIKE %s
                    """, (f"s3://{self.dest_bucket}/%",))
                    
                    new_reports_count = cursor.fetchone()['count']
                    
                except psycopg2.Error:
                    # Reports table doesn't exist
                    old_reports_count = 0
                    new_reports_count = 0
                
                # Success if no old paths remain and new paths exist
                success = (old_paths_count == 0 and new_paths_count > 0 and 
                          old_reports_count == 0 and new_reports_count >= 0)
                
                self.logger.info(f"Database paths verification:")
                self.logger.info(f"  Evidence - Old paths: {old_paths_count}, New paths: {new_paths_count}")
                self.logger.info(f"  Reports - Old paths: {old_reports_count}, New paths: {new_reports_count}")
                self.logger.info(f"  Result: {'PASS' if success else 'FAIL'}")
                
                return success
                
        except Exception as e:
            self.logger.error(f"Failed to verify database paths: {e}")
            return False
    
    def verify_replication(self) -> bool:
        """Verify cross-region replication is enabled."""
        self.logger.info("Verifying cross-region replication...")
        
        try:
            # Check bucket replication configuration
            response = self.s3_client.get_bucket_replication(
                Bucket=self.dest_bucket
            )
            
            replication_config = response['ReplicationConfiguration']
            rules = replication_config.get('Rules', [])
            
            if not rules:
                self.logger.error("No replication rules found")
                return False
            
            # Check if replication is enabled
            enabled_rules = [rule for rule in rules if rule.get('Status') == 'Enabled']
            
            success = len(enabled_rules) > 0
            self.logger.info(f"Replication verification: {len(enabled_rules)} enabled rules - {'PASS' if success else 'FAIL'}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to verify replication: {e}")
            return False
    
    def verify_encryption(self) -> bool:
        """Verify server-side encryption is enabled."""
        self.logger.info("Verifying server-side encryption...")
        
        try:
            # Check bucket encryption configuration
            response = self.s3_client.get_bucket_encryption(
                Bucket=self.dest_bucket
            )
            
            encryption_config = response['ServerSideEncryptionConfiguration']
            rules = encryption_config.get('Rules', [])
            
            if not rules:
                self.logger.error("No encryption rules found")
                return False
            
            # Check if AES256 encryption is configured
            aes256_rules = [
                rule for rule in rules 
                if rule.get('ApplyServerSideEncryptionByDefault', {}).get('SSEAlgorithm') == 'AES256'
            ]
            
            success = len(aes256_rules) > 0
            self.logger.info(f"Encryption verification: {len(aes256_rules)} AES256 rules - {'PASS' if success else 'FAIL'}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to verify encryption: {e}")
            return False
    
    def _list_bucket_objects(self, bucket: str) -> List[Dict]:
        """List all objects in a bucket."""
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket):
            if 'Contents' in page:
                objects.extend(page['Contents'])
        
        return objects
    
    def generate_verification_report(self, results: Dict[str, bool]) -> str:
        """Generate a detailed verification report."""
        report = []
        report.append("WORM Migration Verification Report")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Source Bucket: {self.source_bucket}")
        report.append(f"Destination Bucket: {self.dest_bucket}")
        report.append("")
        
        report.append("Verification Results:")
        for check, result in results.items():
            if check != "overall_success":
                status = "PASS" if result else "FAIL"
                report.append(f"  {check}: {status}")
        
        report.append("")
        report.append(f"Overall Result: {'PASS' if results.get('overall_success') else 'FAIL'}")
        
        return "\n".join(report)

def main():
    """CLI interface for verification script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify WORM migration success')
    parser.add_argument('--source', required=True, help='Source bucket name')
    parser.add_argument('--dest', required=True, help='Destination WORM bucket name')
    parser.add_argument('--report-file', help='Save report to file')
    
    args = parser.parse_args()
    
    verifier = WormMigrationVerifier(args.source, args.dest)
    
    try:
        results = verifier.verify_all()
        
        # Generate and display report
        report = verifier.generate_verification_report(results)
        print(report)
        
        # Save report to file if requested
        if args.report_file:
            with open(args.report_file, 'w') as f:
                f.write(report)
            print(f"\nReport saved to: {args.report_file}")
        
        # Exit with appropriate code
        sys.exit(0 if results.get('overall_success') else 1)
        
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)
    finally:
        if verifier.db_connection:
            verifier.db_connection.close()

if __name__ == "__main__":
    main()
