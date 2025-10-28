#!/usr/bin/env python3
"""
Verify WORM infrastructure deployment and configuration.

This script checks:
1. S3 buckets exist
2. Object Lock is enabled and configured correctly
3. Encryption is enabled
4. Versioning is enabled
5. CloudFormation stacks are deployed (if applicable)

Usage:
    python scripts/verify_worm_infrastructure.py
    python scripts/verify_worm_infrastructure.py --env prod
    python scripts/verify_worm_infrastructure.py --detailed
"""

import boto3
import sys
import os
import argparse
from typing import Dict, Any, List, Tuple
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError

class Colors:
    """Terminal colors for output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")

def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

class WormInfrastructureVerifier:
    """Verify WORM infrastructure deployment."""
    
    def __init__(self, env: str = "dev", region: str = None):
        """
        Initialize verifier.
        
        Args:
            env: Environment (dev/staging/prod)
            region: AWS region (defaults to environment variable or us-east-1)
        """
        self.env = env
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        
        # Expected bucket names
        self.evidence_bucket = os.getenv('WORM_EVIDENCE_BUCKET', f'firemode-evidence-worm-{env}')
        self.reports_bucket = os.getenv('WORM_REPORTS_BUCKET', f'firemode-reports-worm-{env}')
        
        # Expected retention
        self.expected_retention_years = int(os.getenv('WORM_RETENTION_YEARS', '7'))
        
        # Initialize clients
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            self.cf_client = boto3.client('cloudformation', region_name=self.region)
            print_success(f"AWS clients initialized for region: {self.region}")
        except NoCredentialsError:
            print_error("AWS credentials not found. Please configure AWS CLI.")
            sys.exit(1)
        except Exception as e:
            print_error(f"Failed to initialize AWS clients: {e}")
            sys.exit(1)
    
    def check_bucket_exists(self, bucket_name: str) -> bool:
        """Check if S3 bucket exists."""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            elif error_code == '403':
                print_warning(f"Access denied to bucket {bucket_name} (may still exist)")
                return False
            else:
                print_error(f"Error checking bucket {bucket_name}: {e}")
                return False
    
    def check_object_lock(self, bucket_name: str) -> Dict[str, Any]:
        """
        Check Object Lock configuration.
        
        Returns:
            Dict with Object Lock status and configuration
        """
        try:
            response = self.s3_client.get_object_lock_configuration(Bucket=bucket_name)
            config = response.get('ObjectLockConfiguration', {})
            
            enabled = config.get('ObjectLockEnabled') == 'Enabled'
            rule = config.get('Rule', {})
            default_retention = rule.get('DefaultRetention', {})
            mode = default_retention.get('Mode', 'N/A')
            years = default_retention.get('Years', 0)
            
            return {
                'enabled': enabled,
                'mode': mode,
                'years': years,
                'compliant': enabled and mode == 'COMPLIANCE' and years == self.expected_retention_years,
                'config': config
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ObjectLockConfigurationNotFoundError':
                return {
                    'enabled': False,
                    'mode': 'N/A',
                    'years': 0,
                    'compliant': False,
                    'error': 'Object Lock not configured'
                }
            else:
                return {
                    'enabled': False,
                    'mode': 'N/A',
                    'years': 0,
                    'compliant': False,
                    'error': str(e)
                }
    
    def check_versioning(self, bucket_name: str) -> bool:
        """Check if versioning is enabled."""
        try:
            response = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
            status = response.get('Status', 'Disabled')
            return status == 'Enabled'
        except ClientError as e:
            print_error(f"Error checking versioning for {bucket_name}: {e}")
            return False
    
    def check_encryption(self, bucket_name: str) -> Tuple[bool, str]:
        """
        Check if encryption is enabled.
        
        Returns:
            Tuple of (enabled, algorithm)
        """
        try:
            response = self.s3_client.get_bucket_encryption(Bucket=bucket_name)
            rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            
            if not rules:
                return False, 'N/A'
            
            algorithm = rules[0].get('ApplyServerSideEncryptionByDefault', {}).get('SSEAlgorithm', 'N/A')
            return True, algorithm
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ServerSideEncryptionConfigurationNotFoundError':
                return False, 'N/A'
            else:
                print_error(f"Error checking encryption for {bucket_name}: {e}")
                return False, 'ERROR'
    
    def check_public_access_block(self, bucket_name: str) -> bool:
        """Check if public access is blocked."""
        try:
            response = self.s3_client.get_public_access_block(Bucket=bucket_name)
            config = response.get('PublicAccessBlockConfiguration', {})
            
            return all([
                config.get('BlockPublicAcls', False),
                config.get('BlockPublicPolicy', False),
                config.get('IgnorePublicAcls', False),
                config.get('RestrictPublicBuckets', False)
            ])
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchPublicAccessBlockConfiguration':
                return False
            else:
                print_error(f"Error checking public access block for {bucket_name}: {e}")
                return False
    
    def check_cloudformation_stack(self) -> Dict[str, Any]:
        """Check CloudFormation stack status."""
        stack_name = f'firemode-worm-storage-{self.env}'
        
        try:
            response = self.cf_client.describe_stacks(StackName=stack_name)
            stacks = response.get('Stacks', [])
            
            if not stacks:
                return {
                    'exists': False,
                    'status': 'NOT_FOUND'
                }
            
            stack = stacks[0]
            status = stack.get('StackStatus', 'UNKNOWN')
            
            return {
                'exists': True,
                'status': status,
                'stack_name': stack_name,
                'creation_time': stack.get('CreationTime'),
                'outputs': stack.get('Outputs', [])
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationError':
                return {
                    'exists': False,
                    'status': 'NOT_FOUND'
                }
            else:
                return {
                    'exists': False,
                    'status': 'ERROR',
                    'error': str(e)
                }
    
    def verify_bucket(self, bucket_name: str, bucket_type: str) -> Dict[str, Any]:
        """
        Comprehensive bucket verification.
        
        Args:
            bucket_name: S3 bucket name
            bucket_type: Type (evidence/reports)
        
        Returns:
            Dict with verification results
        """
        print_header(f"Verifying {bucket_type.upper()} Bucket: {bucket_name}")
        
        results = {
            'bucket_name': bucket_name,
            'bucket_type': bucket_type,
            'checks': {}
        }
        
        # Check 1: Bucket exists
        print("Checking bucket existence...")
        exists = self.check_bucket_exists(bucket_name)
        results['checks']['exists'] = exists
        
        if exists:
            print_success(f"Bucket {bucket_name} exists")
        else:
            print_error(f"Bucket {bucket_name} does not exist")
            results['overall_status'] = 'FAILED'
            return results
        
        # Check 2: Object Lock
        print("\nChecking Object Lock configuration...")
        object_lock = self.check_object_lock(bucket_name)
        results['checks']['object_lock'] = object_lock
        
        if object_lock.get('compliant'):
            print_success(f"Object Lock: {object_lock['mode']}, {object_lock['years']} years")
        else:
            print_error(f"Object Lock: {object_lock.get('error', 'Not compliant')}")
            if 'mode' in object_lock:
                print_info(f"  Mode: {object_lock['mode']}, Years: {object_lock['years']}")
        
        # Check 3: Versioning
        print("\nChecking versioning...")
        versioning = self.check_versioning(bucket_name)
        results['checks']['versioning'] = versioning
        
        if versioning:
            print_success("Versioning: Enabled")
        else:
            print_error("Versioning: Not enabled")
        
        # Check 4: Encryption
        print("\nChecking encryption...")
        encryption_enabled, algorithm = self.check_encryption(bucket_name)
        results['checks']['encryption'] = {
            'enabled': encryption_enabled,
            'algorithm': algorithm
        }
        
        if encryption_enabled and algorithm == 'AES256':
            print_success(f"Encryption: {algorithm}")
        elif encryption_enabled:
            print_warning(f"Encryption: {algorithm} (expected AES256)")
        else:
            print_error("Encryption: Not enabled")
        
        # Check 5: Public access block
        print("\nChecking public access block...")
        public_blocked = self.check_public_access_block(bucket_name)
        results['checks']['public_blocked'] = public_blocked
        
        if public_blocked:
            print_success("Public access: Blocked")
        else:
            print_error("Public access: Not fully blocked")
        
        # Overall status
        all_compliant = (
            exists and
            object_lock.get('compliant', False) and
            versioning and
            encryption_enabled and
            algorithm == 'AES256' and
            public_blocked
        )
        
        results['overall_status'] = 'COMPLIANT' if all_compliant else 'NON_COMPLIANT'
        
        return results
    
    def run_verification(self, detailed: bool = False) -> bool:
        """
        Run complete infrastructure verification.
        
        Args:
            detailed: Show detailed output
        
        Returns:
            True if all checks pass, False otherwise
        """
        print_header(f"WORM Infrastructure Verification - {self.env.upper()} Environment")
        print_info(f"Region: {self.region}")
        print_info(f"Evidence Bucket: {self.evidence_bucket}")
        print_info(f"Reports Bucket: {self.reports_bucket}")
        print_info(f"Expected Retention: {self.expected_retention_years} years")
        
        all_passed = True
        
        # Verify evidence bucket
        evidence_results = self.verify_bucket(self.evidence_bucket, 'evidence')
        if evidence_results['overall_status'] != 'COMPLIANT':
            all_passed = False
        
        # Verify reports bucket
        reports_results = self.verify_bucket(self.reports_bucket, 'reports')
        if reports_results['overall_status'] != 'COMPLIANT':
            all_passed = False
        
        # Check CloudFormation stack
        print_header("CloudFormation Stack Status")
        stack_info = self.check_cloudformation_stack()
        
        if stack_info.get('exists'):
            status = stack_info['status']
            if status == 'CREATE_COMPLETE' or status == 'UPDATE_COMPLETE':
                print_success(f"Stack: {stack_info['stack_name']} ({status})")
                if detailed and stack_info.get('outputs'):
                    print("\nStack Outputs:")
                    for output in stack_info['outputs']:
                        print(f"  - {output['OutputKey']}: {output['OutputValue']}")
            else:
                print_warning(f"Stack: {stack_info['stack_name']} ({status})")
        else:
            print_warning("CloudFormation stack not found (may be manually deployed)")
        
        # Final summary
        print_header("Verification Summary")
        
        if all_passed:
            print_success("✅ All WORM infrastructure checks PASSED")
            print_success("✅ System is compliant with AS 1851-2012 requirements")
            print_success("✅ Ready for production use")
        else:
            print_error("❌ Some WORM infrastructure checks FAILED")
            print_error("❌ System is NOT compliant with AS 1851-2012 requirements")
            print_error("❌ Review failed checks and remediate before use")
        
        print(f"\n{Colors.BOLD}Verification completed at: {datetime.now().isoformat()}{Colors.END}\n")
        
        return all_passed

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Verify WORM infrastructure deployment')
    parser.add_argument('--env', default='dev', choices=['dev', 'staging', 'prod'],
                      help='Environment to verify (default: dev)')
    parser.add_argument('--region', help='AWS region (default: from AWS_REGION env var or us-east-1)')
    parser.add_argument('--detailed', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    verifier = WormInfrastructureVerifier(env=args.env, region=args.region)
    
    try:
        success = verifier.run_verification(detailed=args.detailed)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
