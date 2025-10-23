#!/bin/bash
# Deploy WORM storage infrastructure
# Usage: ./deploy.sh [environment] [region]

set -e

ENV=${1:-dev}
REGION=${2:-us-east-1}
STACK_NAME="firemode-worm-storage-${ENV}"

echo "Deploying WORM storage infrastructure..."
echo "Environment: ${ENV}"
echo "Region: ${REGION}"
echo "Stack Name: ${STACK_NAME}"

# Validate environment
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "Error: Environment must be dev, staging, or prod"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI not configured or credentials invalid"
    exit 1
fi

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file stack.yml \
    --stack-name "${STACK_NAME}" \
    --parameter-overrides \
        Env="${ENV}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "${REGION}" \
    --tags \
        Project=FireMode \
        Environment="${ENV}" \
        Component=WORM-Storage \
        Compliance=AS1851-2012

# Get stack outputs
echo "Retrieving stack outputs..."
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs' \
    --output table

echo "WORM storage infrastructure deployed successfully!"
echo ""
echo "Next steps:"
echo "1. Configure environment variables:"
echo "   export WORM_EVIDENCE_BUCKET=\$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==\`EvidenceBucketName\`].OutputValue' --output text --region ${REGION})"
echo "   export WORM_REPORTS_BUCKET=\$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==\`ReportsBucketName\`].OutputValue' --output text --region ${REGION})"
echo ""
echo "2. Run migration pipeline:"
echo "   python scripts/migrate_to_worm.py --source firemode-evidence --dest \${WORM_EVIDENCE_BUCKET}"
echo ""
echo "3. Verify deployment:"
echo "   python scripts/verify_worm_migration.py"
