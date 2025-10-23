#!/usr/bin/env python3
"""
Daily compliance monitoring job for WORM storage.

Checks:
- All evidence has Object Lock
- Retention periods are correct
- No policy violations
- Upcoming retention expirations
- System health and performance
"""

import boto3
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

class WormComplianceMonitor:
    """Monitor WORM compliance and send alerts for issues."""
    
    def __init__(self, environment: str = "dev"):
        """
        Initialize WORM compliance monitor.
        
        Args:
            environment: Environment name (dev, staging, prod)
        """
        self.environment = environment
        self.s3_client = boto3.client('s3')
        self.cloudwatch_client = boto3.client('cloudwatch')
        self.sns_client = boto3.client('sns')
        
        # Configuration
        self.evidence_bucket = os.getenv('WORM_EVIDENCE_BUCKET', f'firemode-evidence-worm-{environment}')
        self.reports_bucket = os.getenv('WORM_REPORTS_BUCKET', f'firemode-reports-worm-{environment}')
        self.alerts_topic_arn = os.getenv('WORM_ALERTS_TOPIC_ARN', '')
        
        # Database connection
        self.db_connection = None
        self._connect_database()
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'worm_compliance_monitor_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
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
            self.logger.info("Connected to database for compliance monitoring")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise
    
    def run_daily_checks(self) -> Dict[str, Any]:
        """
        Run daily compliance checks.
        
        Returns:
            Dictionary with check results and summary
        """
        self.logger.info("Starting daily WORM compliance checks")
        
        check_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "checks": {},
            "summary": {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "warnings": 0
            },
            "alerts_sent": 0
        }
        
        try:
            # Check 1: Bucket Object Lock Configuration
            check_results["checks"]["bucket_object_lock"] = self._check_bucket_object_lock()
            
            # Check 2: Evidence Object Lock Status
            check_results["checks"]["evidence_object_lock"] = self._check_evidence_object_lock()
            
            # Check 3: Retention Period Compliance
            check_results["checks"]["retention_compliance"] = self._check_retention_compliance()
            
            # Check 4: Database Integrity
            check_results["checks"]["database_integrity"] = self._check_database_integrity()
            
            # Check 5: Storage Usage
            check_results["checks"]["storage_usage"] = self._check_storage_usage()
            
            # Check 6: Upcoming Retention Expirations
            check_results["checks"]["retention_expirations"] = self._check_retention_expirations()
            
            # Check 7: System Performance
            check_results["checks"]["system_performance"] = self._check_system_performance()
            
            # Calculate summary
            for check_name, check_result in check_results["checks"].items():
                check_results["summary"]["total_checks"] += 1
                
                if check_result.get("status") == "PASS":
                    check_results["summary"]["passed_checks"] += 1
                elif check_result.get("status") == "FAIL":
                    check_results["summary"]["failed_checks"] += 1
                elif check_result.get("status") == "WARNING":
                    check_results["summary"]["warnings"] += 1
            
            # Send alerts if needed
            if check_results["summary"]["failed_checks"] > 0:
                check_results["alerts_sent"] = self._send_alerts(check_results)
            
            # Send metrics to CloudWatch
            self._send_metrics_to_cloudwatch(check_results)
            
            self.logger.info(f"Daily compliance checks completed: {check_results['summary']}")
            return check_results
            
        except Exception as e:
            self.logger.error(f"Daily compliance checks failed: {e}")
            check_results["error"] = str(e)
            check_results["status"] = "ERROR"
            return check_results
        finally:
            if self.db_connection:
                self.db_connection.close()
    
    def _check_bucket_object_lock(self) -> Dict[str, Any]:
        """Check if buckets have Object Lock enabled."""
        try:
            results = {}
            
            for bucket_name in [self.evidence_bucket, self.reports_bucket]:
                try:
                    response = self.s3_client.get_object_lock_configuration(Bucket=bucket_name)
                    config = response.get('ObjectLockConfiguration', {})
                    
                    object_lock_enabled = config.get('ObjectLockEnabled') == 'Enabled'
                    default_retention = config.get('Rule', {}).get('DefaultRetention', {})
                    mode = default_retention.get('Mode', '')
                    years = default_retention.get('Years', 0)
                    
                    results[bucket_name] = {
                        "object_lock_enabled": object_lock_enabled,
                        "retention_mode": mode,
                        "retention_years": years,
                        "compliant": object_lock_enabled and mode == 'COMPLIANCE' and years == 7
                    }
                    
                except Exception as e:
                    results[bucket_name] = {
                        "error": str(e),
                        "compliant": False
                    }
            
            # Overall status
            all_compliant = all(result.get("compliant", False) for result in results.values())
            has_errors = any("error" in result for result in results.values())
            
            return {
                "status": "PASS" if all_compliant and not has_errors else "FAIL",
                "details": results,
                "message": "All buckets have Object Lock enabled with 7-year COMPLIANCE retention" if all_compliant else "Bucket Object Lock configuration issues found"
            }
            
        except Exception as e:
            return {
                "status": "FAIL",
                "error": str(e),
                "message": "Failed to check bucket Object Lock configuration"
            }
    
    def _check_evidence_object_lock(self) -> Dict[str, Any]:
        """Check Object Lock status for evidence files."""
        try:
            # Get recent evidence files (last 7 days)
            with self.db_connection.cursor() as cursor:
                cursor.execute("""
                    SELECT e.id, e.file_path, e.created_at
                    FROM evidence e
                    WHERE e.created_at >= NOW() - INTERVAL '7 days'
                    AND e.file_path IS NOT NULL
                    AND e.file_path != ''
                    ORDER BY e.created_at DESC
                    LIMIT 100
                """)
                
                evidence_records = cursor.fetchall()
            
            if not evidence_records:
                return {
                    "status": "WARNING",
                    "message": "No recent evidence files found",
                    "details": {"checked_files": 0, "compliant_files": 0}
                }
            
            compliant_count = 0
            total_checked = 0
            issues = []
            
            for record in evidence_records:
                if record['file_path'] and record['file_path'].startswith('s3://'):
                    path_parts = record['file_path'][5:].split('/', 1)
                    if len(path_parts) == 2:
                        bucket, key = path_parts
                        total_checked += 1
                        
                        try:
                            # Check Object Lock
                            response = self.s3_client.get_object_retention(Bucket=bucket, Key=key)
                            retention = response['Retention']
                            
                            mode = retention['Mode']
                            retain_until = retention['RetainUntilDate']
                            is_retained = datetime.utcnow() < retain_until.replace(tzinfo=None)
                            
                            if mode == 'COMPLIANCE' and is_retained:
                                compliant_count += 1
                            else:
                                issues.append({
                                    "evidence_id": record['id'],
                                    "key": key,
                                    "mode": mode,
                                    "is_retained": is_retained
                                })
                                
                        except Exception as e:
                            issues.append({
                                "evidence_id": record['id'],
                                "key": key,
                                "error": str(e)
                            })
            
            compliance_rate = compliant_count / total_checked if total_checked > 0 else 1.0
            
            if compliance_rate >= 0.95:
                status = "PASS"
            elif compliance_rate >= 0.90:
                status = "WARNING"
            else:
                status = "FAIL"
            
            return {
                "status": status,
                "message": f"Object Lock compliance rate: {compliance_rate:.1%}",
                "details": {
                    "checked_files": total_checked,
                    "compliant_files": compliant_count,
                    "compliance_rate": compliance_rate,
                    "issues": issues[:10]  # Limit to first 10 issues
                }
            }
            
        except Exception as e:
            return {
                "status": "FAIL",
                "error": str(e),
                "message": "Failed to check evidence Object Lock status"
            }
    
    def _check_retention_compliance(self) -> Dict[str, Any]:
        """Check retention period compliance."""
        try:
            # Check if retention periods are set correctly
            issues = []
            
            for bucket_name in [self.evidence_bucket, self.reports_bucket]:
                try:
                    response = self.s3_client.get_object_lock_configuration(Bucket=bucket_name)
                    default_retention = response.get('ObjectLockConfiguration', {}).get('Rule', {}).get('DefaultRetention', {})
                    
                    years = default_retention.get('Years', 0)
                    mode = default_retention.get('Mode', '')
                    
                    if years != 7:
                        issues.append(f"{bucket_name}: Expected 7 years, got {years}")
                    
                    if mode != 'COMPLIANCE':
                        issues.append(f"{bucket_name}: Expected COMPLIANCE mode, got {mode}")
                        
                except Exception as e:
                    issues.append(f"{bucket_name}: Error checking retention - {str(e)}")
            
            status = "PASS" if not issues else "FAIL"
            
            return {
                "status": status,
                "message": "Retention periods are correctly set to 7 years in COMPLIANCE mode" if not issues else f"Retention compliance issues: {len(issues)}",
                "details": {
                    "issues": issues,
                    "expected_retention_years": 7,
                    "expected_mode": "COMPLIANCE"
                }
            }
            
        except Exception as e:
            return {
                "status": "FAIL",
                "error": str(e),
                "message": "Failed to check retention compliance"
            }
    
    def _check_database_integrity(self) -> Dict[str, Any]:
        """Check database integrity for evidence records."""
        try:
            with self.db_connection.cursor() as cursor:
                # Check for evidence without file paths
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM evidence
                    WHERE file_path IS NULL OR file_path = ''
                """)
                missing_paths = cursor.fetchone()['count']
                
                # Check for orphaned evidence (no test session)
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM evidence e
                    LEFT JOIN test_sessions ts ON e.session_id = ts.id
                    WHERE ts.id IS NULL
                """)
                orphaned_evidence = cursor.fetchone()['count']
                
                # Check for duplicate hashes
                cursor.execute("""
                    SELECT hash, COUNT(*) as count
                    FROM evidence
                    GROUP BY hash
                    HAVING COUNT(*) > 1
                """)
                duplicate_hashes = cursor.fetchall()
                
                issues = []
                if missing_paths > 0:
                    issues.append(f"{missing_paths} evidence records missing file paths")
                
                if orphaned_evidence > 0:
                    issues.append(f"{orphaned_evidence} orphaned evidence records")
                
                if duplicate_hashes:
                    issues.append(f"{len(duplicate_hashes)} duplicate hash values found")
                
                status = "PASS" if not issues else "WARNING"
                
                return {
                    "status": status,
                    "message": "Database integrity is good" if not issues else f"Database integrity issues: {len(issues)}",
                    "details": {
                        "missing_file_paths": missing_paths,
                        "orphaned_evidence": orphaned_evidence,
                        "duplicate_hashes": len(duplicate_hashes),
                        "issues": issues
                    }
                }
                
        except Exception as e:
            return {
                "status": "FAIL",
                "error": str(e),
                "message": "Failed to check database integrity"
            }
    
    def _check_storage_usage(self) -> Dict[str, Any]:
        """Check storage usage and capacity."""
        try:
            usage_info = {}
            
            for bucket_name in [self.evidence_bucket, self.reports_bucket]:
                try:
                    # Get bucket size and object count
                    response = self.s3_client.list_objects_v2(Bucket=bucket_name)
                    
                    total_size = 0
                    object_count = 0
                    
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            total_size += obj['Size']
                            object_count += 1
                    
                    usage_info[bucket_name] = {
                        "total_size_bytes": total_size,
                        "total_size_gb": total_size / (1024**3),
                        "object_count": object_count
                    }
                    
                except Exception as e:
                    usage_info[bucket_name] = {"error": str(e)}
            
            # Check for storage limits (warnings at 80% of 1TB)
            warnings = []
            for bucket_name, info in usage_info.items():
                if "error" not in info:
                    size_gb = info["total_size_gb"]
                    if size_gb > 800:  # 800GB warning threshold
                        warnings.append(f"{bucket_name}: {size_gb:.1f}GB (approaching 1TB limit)")
            
            status = "PASS" if not warnings else "WARNING"
            
            return {
                "status": status,
                "message": "Storage usage is within normal limits" if not warnings else f"Storage usage warnings: {len(warnings)}",
                "details": {
                    "usage_info": usage_info,
                    "warnings": warnings,
                    "warning_threshold_gb": 800
                }
            }
            
        except Exception as e:
            return {
                "status": "FAIL",
                "error": str(e),
                "message": "Failed to check storage usage"
            }
    
    def _check_retention_expirations(self) -> Dict[str, Any]:
        """Check for upcoming retention expirations."""
        try:
            # Check for objects expiring in the next 30 days
            expiring_soon = []
            
            for bucket_name in [self.evidence_bucket, self.reports_bucket]:
                try:
                    # List objects and check retention
                    response = self.s3_client.list_objects_v2(Bucket=bucket_name)
                    
                    if 'Contents' in response:
                        for obj in response['Contents'][:100]:  # Check first 100 objects
                            key = obj['Key']
                            
                            try:
                                retention_response = self.s3_client.get_object_retention(
                                    Bucket=bucket_name, Key=key
                                )
                                
                                retain_until = retention_response['Retention']['RetainUntilDate']
                                days_until_expiry = (retain_until.replace(tzinfo=None) - datetime.utcnow()).days
                                
                                if 0 <= days_until_expiry <= 30:
                                    expiring_soon.append({
                                        "bucket": bucket_name,
                                        "key": key,
                                        "expires_in_days": days_until_expiry,
                                        "expiry_date": retain_until.isoformat()
                                    })
                                    
                            except Exception:
                                # Object might not have retention set
                                continue
                                
                except Exception as e:
                    self.logger.warning(f"Failed to check retention expirations for {bucket_name}: {e}")
            
            status = "PASS" if not expiring_soon else "WARNING"
            
            return {
                "status": status,
                "message": "No objects expiring in the next 30 days" if not expiring_soon else f"{len(expiring_soon)} objects expiring soon",
                "details": {
                    "expiring_objects": expiring_soon,
                    "check_period_days": 30
                }
            }
            
        except Exception as e:
            return {
                "status": "FAIL",
                "error": str(e),
                "message": "Failed to check retention expirations"
            }
    
    def _check_system_performance(self) -> Dict[str, Any]:
        """Check system performance metrics."""
        try:
            # Get CloudWatch metrics for S3 performance
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            performance_issues = []
            
            for bucket_name in [self.evidence_bucket, self.reports_bucket]:
                try:
                    # Check error rates
                    response = self.cloudwatch_client.get_metric_statistics(
                        Namespace='AWS/S3',
                        MetricName='5xxErrors',
                        Dimensions=[
                            {'Name': 'BucketName', 'Value': bucket_name}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1 hour
                        Statistics=['Sum']
                    )
                    
                    total_errors = sum(point['Sum'] for point in response['Datapoints'])
                    
                    if total_errors > 10:  # More than 10 errors in 24 hours
                        performance_issues.append(f"{bucket_name}: {total_errors} 5xx errors in 24h")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get performance metrics for {bucket_name}: {e}")
            
            status = "PASS" if not performance_issues else "WARNING"
            
            return {
                "status": status,
                "message": "System performance is normal" if not performance_issues else f"Performance issues: {len(performance_issues)}",
                "details": {
                    "performance_issues": performance_issues,
                    "check_period_hours": 24
                }
            }
            
        except Exception as e:
            return {
                "status": "FAIL",
                "error": str(e),
                "message": "Failed to check system performance"
            }
    
    def _send_alerts(self, check_results: Dict[str, Any]) -> int:
        """Send alerts for failed checks."""
        if not self.alerts_topic_arn:
            self.logger.warning("No alerts topic configured - skipping alert sending")
            return 0
        
        try:
            # Prepare alert message
            failed_checks = [
                name for name, result in check_results["checks"].items()
                if result.get("status") == "FAIL"
            ]
            
            alert_message = {
                "environment": self.environment,
                "timestamp": check_results["timestamp"],
                "failed_checks": failed_checks,
                "summary": check_results["summary"],
                "details": {
                    name: result for name, result in check_results["checks"].items()
                    if result.get("status") in ["FAIL", "WARNING"]
                }
            }
            
            # Send SNS notification
            self.sns_client.publish(
                TopicArn=self.alerts_topic_arn,
                Subject=f"WORM Compliance Alert - {self.environment}",
                Message=json.dumps(alert_message, indent=2)
            )
            
            self.logger.info(f"Sent compliance alert for {len(failed_checks)} failed checks")
            return 1
            
        except Exception as e:
            self.logger.error(f"Failed to send alerts: {e}")
            return 0
    
    def _send_metrics_to_cloudwatch(self, check_results: Dict[str, Any]):
        """Send custom metrics to CloudWatch."""
        try:
            metrics = []
            
            # Compliance check failures
            compliance_failures = check_results["summary"]["failed_checks"]
            metrics.append({
                'MetricName': 'ComplianceCheckFailures',
                'Value': compliance_failures,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': self.environment}
                ]
            })
            
            # Retention violations (placeholder - would be calculated from actual checks)
            retention_violations = 0
            for result in check_results["checks"].values():
                if "retention" in result.get("message", "").lower() and result.get("status") == "FAIL":
                    retention_violations += 1
            
            metrics.append({
                'MetricName': 'RetentionViolations',
                'Value': retention_violations,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': self.environment}
                ]
            })
            
            # Send metrics
            if metrics:
                self.cloudwatch_client.put_metric_data(
                    Namespace='FireMode/WORM',
                    MetricData=metrics
                )
                
                self.logger.info(f"Sent {len(metrics)} metrics to CloudWatch")
                
        except Exception as e:
            self.logger.error(f"Failed to send metrics to CloudWatch: {e}")

def main():
    """CLI interface for compliance monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor WORM compliance')
    parser.add_argument('--env', default='dev', choices=['dev', 'staging', 'prod'], help='Environment')
    parser.add_argument('--output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    monitor = WormComplianceMonitor(environment=args.env)
    
    try:
        results = monitor.run_daily_checks()
        
        # Print summary
        summary = results.get("summary", {})
        print(f"Compliance Check Summary:")
        print(f"  Total Checks: {summary.get('total_checks', 0)}")
        print(f"  Passed: {summary.get('passed_checks', 0)}")
        print(f"  Failed: {summary.get('failed_checks', 0)}")
        print(f"  Warnings: {summary.get('warnings', 0)}")
        print(f"  Alerts Sent: {results.get('alerts_sent', 0)}")
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to: {args.output}")
        
        # Exit with appropriate code
        if summary.get('failed_checks', 0) > 0:
            sys.exit(1)
        elif summary.get('warnings', 0) > 0:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"Compliance monitoring failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
