#!/usr/bin/env bash
set -euo pipefail

STACK="fire-ai-schema-registry-${1:-dev}"
REGION="${AWS_REGION:-ap-southeast-2}"
TEMPLATE="infra/cloudformation/schema-registry/stack.yml"

aws cloudformation deploy \
  --region "$REGION" \
  --stack-name "$STACK" \
  --template-file "$TEMPLATE" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Env="${1:-dev}" TableName=fire-ai-schema-versions

echo "Stack deployment initiated: $STACK in region $REGION"

