# WORM Storage Implementation

## Overview

This document describes the WORM (Write Once Read Many) storage implementation for the FireMode Compliance Platform, designed to meet AS 1851-2012 regulatory requirements for fire safety evidence retention.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Evidence      │    │   Migration      │    │   WORM Storage  │
│   Submission    │───▶│   Pipeline       │───▶│   (S3 Object    │
│   (FastAPI)     │    │   (Python)       │    │    Lock)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Database      │    │   Verification   │    │   Compliance    │
│   (PostgreSQL)  │    │   Scripts        │    │   Monitoring    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Components

1. **S3 Object Lock Infrastructure** - CloudFormation templates for WORM-enabled buckets
2. **Migration Pipeline** - Python scripts for migrating existing evidence to WORM storage
3. **Upload Handlers** - FastAPI integration for new evidence submissions
4. **Compliance Verification** - Services for verifying WORM compliance and generating certificates
5. **Monitoring & Alerting** - CloudWatch monitoring and SNS alerts
6. **Testing Suite** - Comprehensive unit and integration tests

## Features

### Core WORM Features

- **Object Lock in COMPLIANCE Mode** - Prevents modification or deletion for 7 years
- **7-Year Retention Period** - Meets AS 1851-2012 requirements
- **Server-Side Encryption** - AES-256 encryption for all stored objects
- **Cross-Region Replication** - Disaster recovery with 15-minute RPO
- **Versioning** - Object versioning for additional protection
- **Public Access Blocking** - Prevents accidental public access

### Compliance Features

- **Audit Reports** - Comprehensive compliance verification reports
- **Compliance Certificates** - Digitally signed PDF certificates for audits
- **Real-time Monitoring** - CloudWatch metrics and alerts
- **Database Integrity Checks** - Verification of evidence metadata
- **Retention Expiration Monitoring** - Alerts for upcoming expirations

### Migration Features

- **Batch Processing** - Configurable batch sizes (default: 1000 files)
- **Checksum Verification** - SHA-256/ETag verification for data integrity
- **Progress Tracking** - Resume capability for interrupted migrations
- **Rollback Support** - Ability to revert failed migrations
- **Dry Run Mode** - Test migrations without actual data movement

## Configuration

### Environment Variables

```bash
# WORM Storage Configuration
WORM_EVIDENCE_BUCKET=firemode-evidence-worm-dev
WORM_REPORTS_BUCKET=firemode-reports-worm-dev
WORM_RETENTION_YEARS=7
WORM_BACKUP_REGION=us-west-2

# Migration Configuration
MIGRATION_BATCH_SIZE=1000
MIGRATION_PROGRESS_DIR=/var/log/firemode/migration
MIGRATION_MAX_WORKERS=10

# Compliance Configuration
COMPLIANCE_SIGNING_KEY_PATH=/path/to/private-key.pem
WORM_ALERTS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:firemode-worm-alerts-dev

# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/database

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### CloudFormation Parameters

```yaml
Parameters:
  Env:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]
  
  RetentionYears:
    Type: Number
    Default: 7
    MinValue: 1
    MaxValue: 10
  
  BackupRegion:
    Type: String
    Default: us-west-2
```

## Deployment Guide

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Python 3.9+** with required dependencies
4. **PostgreSQL** database access
5. **Docker** (optional, for containerized deployment)

### Step 1: Deploy Infrastructure

```bash
# Deploy WORM storage infrastructure
cd infra/cloudformation/worm-storage
./deploy.sh dev us-east-1

# Deploy monitoring infrastructure
cd ../worm-monitoring
./deploy.sh dev us-east-1
```

### Step 2: Configure Environment

```bash
# Set environment variables
export WORM_EVIDENCE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name firemode-worm-storage-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`EvidenceBucketName`].OutputValue' \
  --output text)

export WORM_REPORTS_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name firemode-worm-storage-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ReportsBucketName`].OutputValue' \
  --output text)

export WORM_ALERTS_TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name firemode-worm-monitoring-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AlertsTopicArn`].OutputValue' \
  --output text)
```

### Step 3: Run Migration

```bash
# Test migration with dry run
python scripts/migrate_to_worm.py \
  --source firemode-evidence \
  --dest $WORM_EVIDENCE_BUCKET \
  --dry-run

# Run actual migration
python scripts/migrate_to_worm.py \
  --source firemode-evidence \
  --dest $WORM_EVIDENCE_BUCKET \
  --batch-size 1000 \
  --max-workers 10
```

### Step 4: Verify Migration

```bash
# Run verification script
python scripts/verify_worm_migration.py \
  --source firemode-evidence \
  --dest $WORM_EVIDENCE_BUCKET \
  --report-file migration_verification_report.json
```

### Step 5: Configure Monitoring

```bash
# Set up daily compliance monitoring
crontab -e

# Add this line for daily monitoring at 2 AM
0 2 * * * /path/to/python /path/to/scripts/monitor_worm_compliance.py --env dev
```

## Usage

### Evidence Submission

The evidence submission process automatically uses WORM storage:

```python
# Evidence is automatically uploaded to WORM storage
POST /v1/evidence/submit
Content-Type: multipart/form-data

{
  "session_id": "session-123",
  "evidence_type": "photo",
  "file": <file_data>,
  "metadata": "{\"location\": \"building-a\"}"
}
```

### Compliance Verification

```python
# Verify specific evidence compliance
GET /v1/compliance/verify/{evidence_id}

# Generate audit report
POST /v1/compliance/audit
{
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "include_evidence_details": true
}

# Generate compliance certificate
POST /v1/compliance/certificate
{
  "evidence_ids": ["evidence-1", "evidence-2"],
  "include_audit_summary": true
}
```

### Monitoring

```python
# Check compliance status
GET /v1/compliance/status

# Verify bucket compliance
GET /v1/compliance/bucket/verify
```

## API Reference

### Evidence Endpoints

#### Submit Evidence
- **POST** `/v1/evidence/submit`
- **Description**: Submit evidence file to WORM storage
- **Parameters**:
  - `session_id` (string): Test session ID
  - `evidence_type` (string): Type of evidence
  - `file` (file): Evidence file
  - `metadata` (string, optional): JSON metadata
- **Response**: Evidence submission confirmation with WORM storage details

#### Download Evidence
- **GET** `/v1/evidence/{evidence_id}/download`
- **Description**: Generate presigned URL for evidence download
- **Response**: Download URL with expiration

### Compliance Endpoints

#### Verify Evidence Compliance
- **GET** `/v1/compliance/verify/{evidence_id}`
- **Description**: Verify WORM compliance for specific evidence
- **Response**: Compliance verification results

#### Generate Audit Report
- **POST** `/v1/compliance/audit`
- **Description**: Generate comprehensive audit report
- **Parameters**:
  - `start_date` (datetime): Audit period start
  - `end_date` (datetime): Audit period end
  - `include_evidence_details` (boolean): Include detailed evidence info
- **Response**: Audit report with compliance status

#### Generate Compliance Certificate
- **POST** `/v1/compliance/certificate`
- **Description**: Generate compliance certificate PDF
- **Parameters**:
  - `evidence_ids` (array): List of evidence IDs
  - `include_audit_summary` (boolean): Include audit summary
- **Response**: Certificate generation confirmation

#### Get Compliance Status
- **GET** `/v1/compliance/status`
- **Description**: Get overall compliance status
- **Response**: System compliance overview

## Monitoring and Alerting

### CloudWatch Metrics

#### Custom Metrics (FireMode/WORM namespace)
- `ComplianceCheckFailures` - Number of compliance check failures
- `RetentionViolations` - Number of retention policy violations
- `MigrationFailures` - Number of migration failures

#### S3 Metrics (AWS/S3 namespace)
- `BucketSizeBytes` - Bucket storage usage
- `NumberOfObjects` - Object count
- `5xxErrors` - Error rate
- `AllRequests` - Request count

### CloudWatch Alarms

- **Evidence Upload Errors** - Alerts on 5xx errors > 10
- **Reports Upload Errors** - Alerts on 5xx errors > 10
- **Bucket Size** - Alerts when approaching 1TB limit
- **Object Count** - Alerts when approaching 10M objects
- **Compliance Check Failures** - Alerts on any compliance failures
- **Retention Violations** - Alerts on retention policy violations
- **Migration Failures** - Alerts on migration failures > 5

### SNS Notifications

Alerts are sent to the configured SNS topic with:
- Environment information
- Failed check details
- Compliance summary
- Recommended actions

## Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/unit/test_worm_uploader.py -v
pytest tests/unit/test_worm_verifier.py -v
```

### Integration Tests

```bash
# Run integration tests
pytest tests/integration/test_worm_migration.py -v
```

### End-to-End Tests

```bash
# Run E2E tests
pytest tests/integration/test_worm_e2e.py -v
```

## Troubleshooting

### Common Issues

#### 1. Migration Failures

**Problem**: Migration pipeline fails with S3 errors
**Solution**:
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify bucket permissions
aws s3 ls s3://firemode-evidence-worm-dev

# Check migration logs
tail -f migration_log_*.log
```

#### 2. Compliance Check Failures

**Problem**: Compliance verification fails
**Solution**:
```bash
# Check Object Lock configuration
aws s3api get-object-lock-configuration --bucket firemode-evidence-worm-dev

# Verify retention settings
aws s3api get-object-retention --bucket firemode-evidence-worm-dev --key evidence/file.jpg
```

#### 3. Database Connection Issues

**Problem**: Database connection failures
**Solution**:
```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check connection pool settings
# Verify DATABASE_URL format: postgresql://user:password@host:port/database
```

#### 4. Monitoring Alerts

**Problem**: False positive alerts
**Solution**:
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace FireMode/WORM \
  --metric-name ComplianceCheckFailures \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Sum

# Adjust alarm thresholds if needed
```

### Log Analysis

#### Migration Logs
```bash
# View migration progress
grep "Processing batch" migration_log_*.log

# Check for errors
grep "ERROR" migration_log_*.log

# Monitor completion
grep "Migration complete" migration_log_*.log
```

#### Compliance Monitoring Logs
```bash
# View compliance check results
grep "Compliance Check Summary" worm_compliance_monitor_*.log

# Check for failures
grep "FAIL" worm_compliance_monitor_*.log

# Monitor alerts
grep "Sent compliance alert" worm_compliance_monitor_*.log
```

## Performance Optimization

### Migration Performance

- **Batch Size**: Increase to 2000-5000 for faster migration
- **Concurrent Workers**: Increase to 20-50 based on network capacity
- **Regional Proximity**: Run migration from same region as S3 buckets

### Storage Optimization

- **Lifecycle Policies**: Automatic transition to Glacier after 90 days
- **Compression**: Enable S3 compression for text files
- **Deduplication**: Use content-based addressing to reduce storage

### Monitoring Performance

- **Metric Granularity**: Use 1-minute periods for real-time monitoring
- **Dashboard Refresh**: Set to 1-minute refresh for operational dashboards
- **Alert Frequency**: Use 5-minute evaluation periods for critical alerts

## Security Considerations

### Access Control

- **IAM Roles**: Use least-privilege IAM roles for all services
- **Bucket Policies**: Restrict access to specific IP ranges if needed
- **VPC Endpoints**: Use VPC endpoints for private S3 access

### Encryption

- **Server-Side Encryption**: All objects encrypted with AES-256
- **Key Management**: Use AWS KMS for additional key management
- **In-Transit**: All API calls use HTTPS/TLS

### Audit Trail

- **CloudTrail**: Enable CloudTrail for all S3 operations
- **Access Logs**: Enable S3 access logging
- **Database Logging**: Log all evidence access and modifications

## Compliance Documentation

### AS 1851-2012 Requirements

1. **7-Year Retention**: ✅ Implemented with S3 Object Lock
2. **Immutability**: ✅ COMPLIANCE mode prevents modification
3. **Integrity Verification**: ✅ Checksum verification and monitoring
4. **Audit Trail**: ✅ Comprehensive logging and monitoring
5. **Disaster Recovery**: ✅ Cross-region replication

### Compliance Certificates

Compliance certificates include:
- Certificate ID and generation timestamp
- Evidence file details and hashes
- Object Lock verification status
- Digital signature (if configured)
- Compliance statement and validity period

### Audit Reports

Audit reports provide:
- Evidence count and date range
- Compliance check results
- Object Lock verification status
- Database integrity checks
- Performance metrics
- Recommendations for improvements

## Support and Maintenance

### Regular Maintenance Tasks

1. **Daily**: Compliance monitoring and alert review
2. **Weekly**: Performance metrics review and optimization
3. **Monthly**: Full compliance audit and certificate generation
4. **Quarterly**: Disaster recovery testing and documentation updates

### Backup and Recovery

- **S3 Cross-Region Replication**: Automatic backup to secondary region
- **Database Backups**: Regular PostgreSQL backups
- **Configuration Backups**: CloudFormation templates and scripts
- **Recovery Testing**: Quarterly disaster recovery drills

### Updates and Upgrades

- **Security Updates**: Monthly security patch review
- **Feature Updates**: Quarterly feature release planning
- **Compliance Updates**: Annual compliance requirement review
- **Performance Tuning**: Continuous performance optimization

## Contact Information

For technical support or compliance questions:
- **Technical Issues**: devops@firemode.com
- **Compliance Questions**: compliance@firemode.com
- **Emergency Support**: +1-800-FIREMODE

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial WORM storage implementation
- S3 Object Lock with 7-year retention
- Migration pipeline with batch processing
- Compliance verification service
- CloudWatch monitoring and alerting
- Comprehensive test suite
- Documentation and deployment guides
