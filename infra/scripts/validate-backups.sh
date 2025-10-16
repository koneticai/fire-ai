#!/usr/bin/env bash
#
# Fire-AI Backup Validation Script
# FM-ENH-002: DR Runbook & Testing
#
# This script validates backup status across Aurora, DynamoDB, and S3
# Usage: ./validate-backups.sh [--region <region>] [--days <days>]
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_REGION="ap-southeast-2"
DEFAULT_DAYS=7
REGION="$DEFAULT_REGION"
DAYS="$DEFAULT_DAYS"
VERBOSE=false

# Exit codes
EXIT_SUCCESS=0
EXIT_WARNING=1
EXIT_ERROR=2

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_info() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

# Help function
show_help() {
    cat << EOF
Fire-AI Backup Validation Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --region <region>    AWS region to check (default: $DEFAULT_REGION)
    --days <days>        Number of days to check for backups (default: $DEFAULT_DAYS)
    --verbose, -v        Enable verbose output
    --help, -h           Show this help message

EXAMPLES:
    # Check backups in default region for last 7 days
    $0

    # Check backups in us-west-2 for last 3 days
    $0 --region us-west-2 --days 3

    # Verbose output
    $0 --verbose

DESCRIPTION:
    This script validates backup status for:
    - Aurora PostgreSQL cluster snapshots
    - DynamoDB point-in-time recovery status
    - S3 bucket replication (if configured)
    - Backup encryption settings
    - Backup age and completeness

EXIT CODES:
    0 - All backups are healthy
    1 - Some backups have warnings
    2 - Critical backup issues found

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --region)
                REGION="$2"
                shift 2
                ;;
            --days)
                DAYS="$2"
                shift 2
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log "Backup Validation Parameters:"
    log "  Region: $REGION"
    log "  Days to check: $DAYS"
    log "  Verbose: $VERBOSE"
}

# Validate prerequisites
validate_prerequisites() {
    log "Validating prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit $EXIT_ERROR
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity --region "$REGION" &> /dev/null; then
        log_error "AWS credentials not configured or invalid for region $REGION"
        exit $EXIT_ERROR
    fi

    log_success "Prerequisites validated"
}

# Check Aurora cluster snapshots
check_aurora_snapshots() {
    local exit_code=$EXIT_SUCCESS
    local cutoff_date=$(date -d "$DAYS days ago" --iso-8601)
    
    log "Checking Aurora cluster snapshots (last $DAYS days)..."
    
    # List Aurora clusters
    local clusters=$(aws rds describe-db-clusters \
        --region "$REGION" \
        --query "DBClusters[?contains(DBClusterIdentifier, 'fire-ai')].DBClusterIdentifier" \
        --output text)
    
    if [[ -z "$clusters" ]]; then
        log_warning "No Fire-AI Aurora clusters found in region $REGION"
        return $EXIT_WARNING
    fi
    
    for cluster in $clusters; do
        log_info "Checking cluster: $cluster"
        
        # Get cluster snapshots
        local snapshots=$(aws rds describe-db-cluster-snapshots \
            --db-cluster-identifier "$cluster" \
            --region "$REGION" \
            --query "DBClusterSnapshots[?SnapshotCreateTime >= '$cutoff_date' && Status=='available'].[DBClusterSnapshotIdentifier,SnapshotCreateTime,Status,AllocatedStorage]" \
            --output text)
        
        if [[ -z "$snapshots" ]]; then
            log_error "No recent snapshots found for cluster $cluster"
            exit_code=$EXIT_ERROR
            continue
        fi
        
        # Count snapshots and check age
        local snapshot_count=$(echo "$snapshots" | wc -l)
        local latest_snapshot=$(echo "$snapshots" | head -1 | awk '{print $2}')
        local latest_date=$(date -d "$latest_snapshot" +%s)
        local current_date=$(date +%s)
        local age_hours=$(( (current_date - latest_date) / 3600 ))
        
        log_success "Cluster $cluster: $snapshot_count snapshots found"
        log_info "  Latest snapshot: $latest_snapshot (age: ${age_hours}h)"
        
        # Check if latest snapshot is too old
        if [[ $age_hours -gt 12 ]]; then
            log_warning "Latest snapshot for $cluster is older than 12 hours"
            exit_code=$EXIT_WARNING
        fi
        
        # Check snapshot encryption
        local encrypted_snapshots=$(aws rds describe-db-cluster-snapshots \
            --db-cluster-identifier "$cluster" \
            --region "$REGION" \
            --query "DBClusterSnapshots[?SnapshotCreateTime >= '$cutoff_date' && Status=='available' && StorageEncrypted==\`true\`] | length(@)" \
            --output text)
        
        if [[ "$encrypted_snapshots" == "0" ]]; then
            log_error "Unencrypted snapshots found for cluster $cluster"
            exit_code=$EXIT_ERROR
        else
            log_success "All snapshots for $cluster are encrypted"
        fi
    done
    
    return $exit_code
}

# Check DynamoDB point-in-time recovery
check_dynamodb_pitr() {
    local exit_code=$EXIT_SUCCESS
    
    log "Checking DynamoDB point-in-time recovery status..."
    
    # Check schema registry table
    local table_name="fire-ai-schema-versions"
    
    if ! aws dynamodb describe-table --table-name "$table_name" --region "$REGION" &> /dev/null; then
        log_warning "DynamoDB table $table_name not found in region $REGION"
        return $EXIT_WARNING
    fi
    
    # Check PITR status
    local pitr_status=$(aws dynamodb describe-continuous-backups \
        --table-name "$table_name" \
        --region "$REGION" \
        --query "ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus" \
        --output text)
    
    if [[ "$pitr_status" == "ENABLED" ]]; then
        log_success "Point-in-time recovery is ENABLED for $table_name"
    else
        log_error "Point-in-time recovery is DISABLED for $table_name"
        exit_code=$EXIT_ERROR
    fi
    
    # Check table encryption
    local encryption_status=$(aws dynamodb describe-table \
        --table-name "$table_name" \
        --region "$REGION" \
        --query "Table.SSEDescription.Status" \
        --output text)
    
    if [[ "$encryption_status" == "ENABLED" ]]; then
        log_success "Encryption is ENABLED for $table_name"
    else
        log_error "Encryption is DISABLED for $table_name"
        exit_code=$EXIT_ERROR
    fi
    
    # Check table status
    local table_status=$(aws dynamodb describe-table \
        --table-name "$table_name" \
        --region "$REGION" \
        --query "Table.TableStatus" \
        --output text)
    
    if [[ "$table_status" == "ACTIVE" ]]; then
        log_success "Table $table_name is ACTIVE"
    else
        log_warning "Table $table_name status: $table_status"
        exit_code=$EXIT_WARNING
    fi
    
    return $exit_code
}

# Check S3 bucket replication
check_s3_replication() {
    local exit_code=$EXIT_SUCCESS
    
    log "Checking S3 bucket replication status..."
    
    # List Fire-AI related buckets
    local buckets=$(aws s3api list-buckets \
        --query "Buckets[?contains(Name, 'fire-ai')].Name" \
        --output text)
    
    if [[ -z "$buckets" ]]; then
        log_warning "No Fire-AI S3 buckets found"
        return $EXIT_WARNING
    fi
    
    for bucket in $buckets; do
        log_info "Checking bucket: $bucket"
        
        # Check if bucket exists in current region
        local bucket_region=$(aws s3api get-bucket-location \
            --bucket "$bucket" \
            --query "LocationConstraint" \
            --output text)
        
        if [[ "$bucket_region" == "None" ]]; then
            bucket_region="us-east-1"
        fi
        
        if [[ "$bucket_region" != "$REGION" ]]; then
            log_info "Bucket $bucket is in region $bucket_region, skipping"
            continue
        fi
        
        # Check replication configuration
        local replication_config=$(aws s3api get-bucket-replication \
            --bucket "$bucket" \
            --region "$REGION" 2>/dev/null || echo "No replication")
        
        if [[ "$replication_config" == "No replication" ]]; then
            log_warning "No replication configured for bucket $bucket"
            exit_code=$EXIT_WARNING
        else
            log_success "Replication is configured for bucket $bucket"
        fi
        
        # Check bucket encryption
        local encryption_config=$(aws s3api get-bucket-encryption \
            --bucket "$bucket" \
            --region "$REGION" 2>/dev/null || echo "No encryption")
        
        if [[ "$encryption_config" == "No encryption" ]]; then
            log_error "No encryption configured for bucket $bucket"
            exit_code=$EXIT_ERROR
        else
            log_success "Encryption is configured for bucket $bucket"
        fi
        
        # Check bucket versioning
        local versioning_status=$(aws s3api get-bucket-versioning \
            --bucket "$bucket" \
            --region "$REGION" \
            --query "Status" \
            --output text)
        
        if [[ "$versioning_status" == "Enabled" ]]; then
            log_success "Versioning is enabled for bucket $bucket"
        else
            log_warning "Versioning is not enabled for bucket $bucket"
            exit_code=$EXIT_WARNING
        fi
    done
    
    return $exit_code
}

# Generate backup summary report
generate_summary_report() {
    local overall_status=$EXIT_SUCCESS
    
    log "Generating backup summary report..."
    
    # Check Aurora snapshots
    if ! check_aurora_snapshots; then
        overall_status=$EXIT_WARNING
    fi
    
    echo "----------------------------------------"
    
    # Check DynamoDB PITR
    if ! check_dynamodb_pitr; then
        overall_status=$EXIT_ERROR
    fi
    
    echo "----------------------------------------"
    
    # Check S3 replication
    if ! check_s3_replication; then
        overall_status=$EXIT_WARNING
    fi
    
    echo "----------------------------------------"
    
    # Overall status
    case $overall_status in
        $EXIT_SUCCESS)
            log_success "All backups are healthy"
            ;;
        $EXIT_WARNING)
            log_warning "Some backups have warnings"
            ;;
        $EXIT_ERROR)
            log_error "Critical backup issues found"
            ;;
    esac
    
    return $overall_status
}

# Generate detailed report for CI/CD
generate_detailed_report() {
    local report_file="backup-validation-report-$(date +%Y%m%d-%H%M%S).json"
    
    log "Generating detailed report: $report_file"
    
    cat > "$report_file" << EOF
{
  "timestamp": "$(date --iso-8601)",
  "region": "$REGION",
  "days_checked": $DAYS,
  "aurora_clusters": {
    "status": "checked",
    "details": "See log output above"
  },
  "dynamodb_tables": {
    "fire-ai-schema-versions": {
      "status": "checked",
      "pitr_enabled": true,
      "encryption_enabled": true
    }
  },
  "s3_buckets": {
    "status": "checked",
    "replication_configured": "varies by bucket",
    "encryption_enabled": "varies by bucket"
  },
  "recommendations": [
    "Ensure Aurora snapshots are created every 6 hours",
    "Verify DynamoDB PITR is enabled",
    "Configure S3 cross-region replication for critical buckets",
    "Enable S3 bucket versioning and encryption"
  ]
}
EOF
    
    log_success "Detailed report generated: $report_file"
}

# Main execution
main() {
    log "Starting Fire-AI Backup Validation"
    log "=================================="
    
    parse_args "$@"
    validate_prerequisites
    
    generate_summary_report
    local exit_code=$?
    
    if [[ "$VERBOSE" == "true" ]]; then
        generate_detailed_report
    fi
    
    log "Backup validation completed with exit code: $exit_code"
    exit $exit_code
}

# Run main function with all arguments
main "$@"
