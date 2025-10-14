#!/bin/bash
set -e
echo "🔍 MPKF Compliance Validation"
echo "=============================="

# 1) Commit message format (last commit)
if ! git log --format=%B -n 1 HEAD | \
  grep -E '^(feat|fix|docs|chore|test|refactor|perf|ci|build)\([a-z]+\): .+ \[FM-ENH-[0-9]{3}\]$' >/dev/null; then
  echo "❌ Commit message doesn't match MPKF format"
  echo "Expected: <type>(<scope>): <subject> [FM-ENH-XXX]"
  exit 1
fi

# 2) MPKF-Ref presence
if ! git log --format=%B -n 1 HEAD | grep -q "MPKF-Ref:"; then
  echo "❌ Missing MPKF-Ref in commit body"
  echo "Add: MPKF-Ref: TDD-v4.0-Section-X,v3.1"
  exit 1
fi

# 3) ADR presence for architectural change
CHANGED_FILES=$(git diff --name-only HEAD~1)
if echo "$CHANGED_FILES" | grep -qE '^(services|infra)/'; then
  if ! echo "$CHANGED_FILES" | grep -q '^docs/adr/'; then
    echo "⚠️  Architectural change without ADR (docs/adr/)"
  fi
fi

# 4) Tests updated when code changes
if echo "$CHANGED_FILES" | grep -qE '\.(py|ts|tsx|go)$'; then
  if ! echo "$CHANGED_FILES" | grep -qE '(test|spec)'; then
    echo "⚠️  Code changes without corresponding tests"
  fi
fi

echo "✅ MPKF validation passed"
