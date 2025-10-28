#!/bin/bash
# Simple S3 Object Lock verification script
# Usage: ./scripts/verify_s3_simple.sh [bucket-name]

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default bucket names
EVIDENCE_BUCKET="${WORM_EVIDENCE_BUCKET:-fireai-evidence-prod}"
REPORTS_BUCKET="${WORM_REPORTS_BUCKET:-fireai-reports-prod}"

# Use provided bucket or default to evidence bucket
BUCKET="${1:-$EVIDENCE_BUCKET}"

echo "================================================"
echo "  S3 Object Lock Configuration Verification"
echo "================================================"
echo ""
echo "Bucket: $BUCKET"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    echo "Install with: brew install awscli  (macOS)"
    echo "            or: pip install awscli"
    exit 1
fi

# Check if credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Configure with: aws configure"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI configured${NC}"
echo ""

# Check bucket exists
echo "Checking bucket existence..."
if aws s3 ls "s3://$BUCKET" &> /dev/null; then
    echo -e "${GREEN}✅ Bucket exists${NC}"
else
    echo -e "${RED}❌ Bucket not found or access denied${NC}"
    exit 1
fi

echo ""
echo "Checking Object Lock configuration..."
echo ""

# Get Object Lock configuration
if LOCK_CONFIG=$(aws s3api get-object-lock-configuration --bucket "$BUCKET" 2>&1); then
    echo -e "${GREEN}✅ Object Lock is configured${NC}"
    echo ""
    echo "Configuration:"
    echo "$LOCK_CONFIG" | python3 -m json.tool
    echo ""
    
    # Parse and verify
    ENABLED=$(echo "$LOCK_CONFIG" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['ObjectLockConfiguration']['ObjectLockEnabled'])" 2>/dev/null || echo "")
    MODE=$(echo "$LOCK_CONFIG" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['ObjectLockConfiguration']['Rule']['DefaultRetention']['Mode'])" 2>/dev/null || echo "")
    YEARS=$(echo "$LOCK_CONFIG" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['ObjectLockConfiguration']['Rule']['DefaultRetention']['Years'])" 2>/dev/null || echo "")
    
    echo "Verification:"
    
    if [ "$ENABLED" == "Enabled" ]; then
        echo -e "${GREEN}✅ ObjectLockEnabled: Enabled${NC}"
    else
        echo -e "${RED}❌ ObjectLockEnabled: $ENABLED (expected: Enabled)${NC}"
    fi
    
    if [ "$MODE" == "COMPLIANCE" ]; then
        echo -e "${GREEN}✅ Mode: COMPLIANCE${NC}"
    else
        echo -e "${RED}❌ Mode: $MODE (expected: COMPLIANCE)${NC}"
    fi
    
    if [ "$YEARS" == "7" ]; then
        echo -e "${GREEN}✅ Retention: 7 years${NC}"
    else
        echo -e "${YELLOW}⚠️  Retention: $YEARS years (expected: 7)${NC}"
    fi
    
else
    echo -e "${RED}❌ Object Lock is NOT configured${NC}"
    echo ""
    echo "Error details:"
    echo "$LOCK_CONFIG"
    exit 1
fi

echo ""
echo "Checking versioning..."
VERSIONING=$(aws s3api get-bucket-versioning --bucket "$BUCKET" --query 'Status' --output text)
if [ "$VERSIONING" == "Enabled" ]; then
    echo -e "${GREEN}✅ Versioning: Enabled${NC}"
else
    echo -e "${RED}❌ Versioning: $VERSIONING (expected: Enabled)${NC}"
fi

echo ""
echo "Checking encryption..."
if ENCRYPTION=$(aws s3api get-bucket-encryption --bucket "$BUCKET" 2>&1); then
    ALGORITHM=$(echo "$ENCRYPTION" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'])" 2>/dev/null || echo "")
    if [ "$ALGORITHM" == "AES256" ]; then
        echo -e "${GREEN}✅ Encryption: $ALGORITHM${NC}"
    else
        echo -e "${YELLOW}⚠️  Encryption: $ALGORITHM (expected: AES256)${NC}"
    fi
else
    echo -e "${RED}❌ Encryption not configured${NC}"
fi

echo ""
echo "================================================"
echo "  Verification Complete"
echo "================================================"
