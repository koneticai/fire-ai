#!/usr/bin/env bash
#
# Fire-AI CloudFormation Stack Recreation Script
# FM-ENH-002: DR Runbook & Testing
#
# This script recreates CloudFormation stacks with optional Aurora snapshot restoration
# Usage: ./recreate-stack.sh [--dry-run] <stack-name> [region] [snapshot-id]
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
DRY_RUN=false
SNAPSHOT_ID=""
STACK_NAME=""
REGION=""
TEMPLATE_FILE=""

# Logging function
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

# Help function
show_help() {
    cat << EOF
Fire-AI CloudFormation Stack Recreation Script

USAGE:
    $0 [OPTIONS] <stack-name> [region] [snapshot-id]

OPTIONS:
    --dry-run           Show what would be done without executing
    --help, -h          Show this help message

ARGUMENTS:
    stack-name          Name of the CloudFormation stack to recreate
    region              AWS region (default: $DEFAULT_REGION)
    snapshot-id         Aurora snapshot ID for database restoration (optional)

EXAMPLES:
    # Dry run to see what would happen
    $0 --dry-run fire-ai-prod-stack

    # Recreate stack without Aurora restoration
    $0 fire-ai-prod-stack ap-southeast-2

    # Recreate stack with Aurora snapshot restoration
    $0 fire-ai-prod-stack ap-southeast-2 rds:fire-ai-prod-cluster-2025-01-15-12-30

DESCRIPTION:
    This script performs the following operations:
    1. Exports current stack configuration as backup
    2. Deletes existing stack (with confirmation)
    3. Recreates stack from template
    4. Optionally restores Aurora from snapshot
    5. Updates Route 53 DNS records if applicable
    6. Validates stack health

PREREQUISITES:
    - AWS CLI v2 configured with appropriate permissions
    - CloudFormation template file exists
    - Appropriate IAM permissions for stack operations

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$STACK_NAME" ]]; then
                    STACK_NAME="$1"
                elif [[ -z "$REGION" ]]; then
                    REGION="$1"
                elif [[ -z "$SNAPSHOT_ID" ]]; then
                    SNAPSHOT_ID="$1"
                else
                    log_error "Too many arguments"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$STACK_NAME" ]]; then
        log_error "Stack name is required"
        show_help
        exit 1
    fi

    # Set default region if not provided
    if [[ -z "$REGION" ]]; then
        REGION="$DEFAULT_REGION"
    fi

    log "Stack Recreation Parameters:"
    log "  Stack Name: $STACK_NAME"
    log "  Region: $REGION"
    log "  Snapshot ID: ${SNAPSHOT_ID:-'Not specified'}"
    log "  Dry Run: $DRY_RUN"
}

# Validate prerequisites
validate_prerequisites() {
    log "Validating prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi

    # Check if stack exists
    if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
        log_error "Stack '$STACK_NAME' not found in region '$REGION'"
        exit 1
    fi

    # Find template file
    TEMPLATE_FILE=$(find . -name "*.yml" -o -name "*.yaml" | grep -E "(template|stack)" | head -1)
    if [[ -z "$TEMPLATE_FILE" ]]; then
        log_error "No CloudFormation template file found"
        exit 1
    fi

    log_success "Prerequisites validated"
}

# Export current stack configuration
export_stack_config() {
    local backup_file="stack-backup-${STACK_NAME}-$(date +%Y%m%d-%H%M%S).json"
    
    log "Exporting current stack configuration to $backup_file..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would export stack configuration to $backup_file"
        return 0
    fi

    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --output json > "$backup_file"
    
    log_success "Stack configuration exported to $backup_file"
}

# Delete existing stack
delete_stack() {
    log "Preparing to delete stack '$STACK_NAME'..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would delete stack '$STACK_NAME'"
        return 0
    fi

    # Confirmation prompt
    echo -n "Are you sure you want to delete stack '$STACK_NAME'? (yes/no): "
    read -r confirmation
    
    if [[ "$confirmation" != "yes" ]]; then
        log "Stack deletion cancelled"
        exit 0
    fi

    log "Deleting stack '$STACK_NAME'..."
    aws cloudformation delete-stack \
        --stack-name "$STACK_NAME" \
        --region "$REGION"

    log "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"

    log_success "Stack deleted successfully"
}

# Recreate stack from template
recreate_stack() {
    log "Recreating stack '$STACK_NAME' from template '$TEMPLATE_FILE'..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would recreate stack using template '$TEMPLATE_FILE'"
        return 0
    fi

    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body "file://$TEMPLATE_FILE" \
        --region "$REGION" \
        --capabilities CAPABILITY_NAMED_IAM

    log "Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete \
        --stack-name "$STACK_NAME" \
        --region "$REGION"

    log_success "Stack recreated successfully"
}

# Restore Aurora from snapshot if specified
restore_aurora_snapshot() {
    if [[ -z "$SNAPSHOT_ID" ]]; then
        log "No snapshot ID provided, skipping Aurora restoration"
        return 0
    fi

    log "Restoring Aurora from snapshot '$SNAPSHOT_ID'..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would restore Aurora cluster from snapshot '$SNAPSHOT_ID'"
        return 0
    fi

    # Extract cluster identifier from snapshot ID
    local cluster_id=$(echo "$SNAPSHOT_ID" | sed 's/rds://' | sed 's/-[0-9-]*$//')
    local restored_cluster_id="${cluster_id}-restored"

    log "Restoring Aurora cluster '$cluster_id' as '$restored_cluster_id'..."

    # Restore cluster from snapshot
    aws rds restore-db-cluster-from-snapshot \
        --db-cluster-identifier "$restored_cluster_id" \
        --snapshot-identifier "$SNAPSHOT_ID" \
        --region "$REGION" \
        --engine aurora-postgresql

    # Wait for cluster to be available
    aws rds wait db-cluster-available \
        --db-cluster-identifier "$restored_cluster_id" \
        --region "$REGION"

    log_success "Aurora cluster restored successfully"
}

# Update Route 53 DNS records (if applicable)
update_dns_records() {
    log "Checking for Route 53 DNS updates..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would check and update Route 53 records if needed"
        return 0
    fi

    # Get stack outputs
    local outputs=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs" \
        --output json)

    # Check if there are any Route 53 related outputs
    if echo "$outputs" | grep -q "Route53\|DNS\|Domain"; then
        log "Route 53 outputs detected, manual DNS update may be required"
        log "Please review stack outputs and update DNS records as needed"
    else
        log "No Route 53 outputs detected, skipping DNS updates"
    fi
}

# Validate stack health
validate_stack_health() {
    log "Validating stack health..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would validate stack health"
        return 0
    fi

    # Check stack status
    local stack_status=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].StackStatus" \
        --output text)

    if [[ "$stack_status" == "CREATE_COMPLETE" ]]; then
        log_success "Stack is healthy (status: $stack_status)"
    else
        log_error "Stack is not healthy (status: $stack_status)"
        exit 1
    fi

    # Check for any failed resources
    local failed_resources=$(aws cloudformation describe-stack-events \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "StackEvents[?ResourceStatus=='CREATE_FAILED'].[LogicalResourceId,ResourceStatusReason]" \
        --output text)

    if [[ -n "$failed_resources" ]]; then
        log_warning "Some resources failed to create:"
        echo "$failed_resources"
    fi
}

# Generate validation checklist
generate_checklist() {
    local checklist_file="recovery-checklist-${STACK_NAME}-$(date +%Y%m%d-%H%M%S).txt"
    
    log "Generating validation checklist: $checklist_file"
    
    cat > "$checklist_file" << EOF
Fire-AI Stack Recovery Validation Checklist
Generated: $(date)
Stack: $STACK_NAME
Region: $REGION
Snapshot: ${SNAPSHOT_ID:-'N/A'}

POST-RECOVERY VALIDATION STEPS:

□ Stack Status: CREATE_COMPLETE
□ Aurora Cluster: Available (if restored)
□ ECS Services: Running
□ ALB Target Groups: Healthy
□ DynamoDB Table: Active
□ CloudWatch Logs: No critical errors
□ API Endpoints: Responding
□ Health Checks: Passing

MANUAL VERIFICATION COMMANDS:

# Check stack status
aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query "Stacks[0].StackStatus"

# Check Aurora cluster (if restored)
aws rds describe-db-clusters --db-cluster-identifier ${SNAPSHOT_ID:-'N/A'} --region $REGION --query "DBClusters[0].Status"

# Check ECS services
aws ecs describe-services --cluster fire-ai-prod-cluster --region $REGION --query "services[*].[serviceName,status,runningCount]"

# Check DynamoDB table
aws dynamodb describe-table --table-name fire-ai-schema-versions --region $REGION --query "Table.TableStatus"

# Test API endpoints
curl -f https://api.fire-ai.com/health
curl -f https://api.fire-ai.com/health/readiness

NEXT STEPS:
□ Update application configuration if endpoints changed
□ Run smoke tests
□ Notify stakeholders of recovery completion
□ Schedule post-incident review
□ Update runbook if needed

EOF

    log_success "Validation checklist generated: $checklist_file"
}

# Main execution
main() {
    log "Starting Fire-AI Stack Recreation Process"
    log "=========================================="

    parse_args "$@"
    validate_prerequisites
    
    export_stack_config
    delete_stack
    recreate_stack
    restore_aurora_snapshot
    update_dns_records
    validate_stack_health
    generate_checklist

    log_success "Stack recreation process completed successfully!"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "This was a dry run - no actual changes were made"
    fi
}

# Run main function with all arguments
main "$@"
