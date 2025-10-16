#!/bin/bash
# Code Quality Check Script
# =========================
#
# Validates code quality for defects and evidence implementations.
#
# Checks:
# - TODO/FIXME/XXX comments
# - Security issues (eval, exec, SQL injection)
# - Test coverage counts
# - Docstring presence
#
# Usage:
#     ./code_quality_check.sh

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print header
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}======================================================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}======================================================================${NC}"
    echo ""
}

# Print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Print info
print_info() {
    echo "   $1"
}

# Counters
PASSED=0
FAILED=0
WARNINGS=0

print_header "Code Quality Check - Defects & Evidence"
echo "Working Directory: $(pwd)"
echo ""

# Check 1: TODO/FIXME/XXX Comments
print_header "1. Checking for TODO/FIXME/XXX Comments"

echo "Checking defects router..."
DEFECTS_TODOS=$(grep -rn "TODO\|FIXME\|XXX" src/app/routers/defects.py 2>/dev/null | wc -l || echo "0")
if [ "$DEFECTS_TODOS" -eq 0 ]; then
    print_success "Defects router: No TODO comments found"
    ((PASSED++))
else
    print_warning "Defects router: Found $DEFECTS_TODOS TODO comments"
    grep -rn "TODO\|FIXME\|XXX" src/app/routers/defects.py 2>/dev/null | while read line; do
        print_info "$line"
    done
    ((WARNINGS++))
fi

echo ""
echo "Checking evidence router..."
EVIDENCE_TODOS=$(grep -rn "TODO\|FIXME\|XXX" src/app/routers/evidence.py 2>/dev/null | wc -l || echo "0")
if [ "$EVIDENCE_TODOS" -eq 0 ]; then
    print_success "Evidence router: No TODO comments found"
    ((PASSED++))
else
    print_warning "Evidence router: Found $EVIDENCE_TODOS TODO comments"
    grep -rn "TODO\|FIXME\|XXX" src/app/routers/evidence.py 2>/dev/null | while read line; do
        print_info "$line"
    done
    ((WARNINGS++))
fi

echo ""
echo "Checking defects model..."
DEFECTS_MODEL_TODOS=$(grep -rn "TODO\|FIXME\|XXX" src/app/models/defects.py 2>/dev/null | wc -l || echo "0")
if [ "$DEFECTS_MODEL_TODOS" -eq 0 ]; then
    print_success "Defects model: No TODO comments found"
    ((PASSED++))
else
    print_warning "Defects model: Found $DEFECTS_MODEL_TODOS TODO comments"
    ((WARNINGS++))
fi

# Check 2: Security Issues
print_header "2. Security Scan"

echo "Checking for dangerous functions (eval, exec, __import__)..."
DANGEROUS_FUNCS=$(grep -rn "eval\(|exec\(|__import__" src/app/routers/defects.py src/app/routers/evidence.py src/app/models/defects.py 2>/dev/null | wc -l || echo "0")
if [ "$DANGEROUS_FUNCS" -eq 0 ]; then
    print_success "No dangerous functions found (eval, exec, __import__)"
    ((PASSED++))
else
    print_error "Found $DANGEROUS_FUNCS instances of dangerous functions"
    grep -rn "eval\(|exec\(|__import__" src/app/routers/defects.py src/app/routers/evidence.py src/app/models/defects.py 2>/dev/null
    ((FAILED++))
fi

echo ""
echo "Checking for SQL injection vulnerabilities..."
# Note: We need to be careful here - parameterized queries using %s are safe
# We're looking for string concatenation or f-strings in .execute() calls
SQL_INJECTION=$(grep -rn "\.execute(.*f\"|\.execute(.*f'" src/app/routers/defects.py src/app/routers/evidence.py 2>/dev/null | wc -l || echo "0")
if [ "$SQL_INJECTION" -eq 0 ]; then
    print_success "No SQL injection vulnerabilities found"
    ((PASSED++))
else
    print_warning "Found $SQL_INJECTION potential SQL injection patterns"
    print_info "Note: Parameterized queries using %s placeholders are safe"
    grep -rn "\.execute(.*f\"|\.execute(.*f'" src/app/routers/defects.py src/app/routers/evidence.py 2>/dev/null
    ((WARNINGS++))
fi

echo ""
echo "Checking for hardcoded credentials..."
CREDENTIALS=$(grep -rn "password.*=.*['\"]|api_key.*=.*['\"]|secret.*=.*['\"]" src/app/routers/defects.py src/app/routers/evidence.py 2>/dev/null | grep -v "# " | wc -l || echo "0")
if [ "$CREDENTIALS" -eq 0 ]; then
    print_success "No hardcoded credentials found"
    ((PASSED++))
else
    print_error "Found $CREDENTIALS potential hardcoded credentials"
    grep -rn "password.*=.*['\"]|api_key.*=.*['\"]|secret.*=.*['\"]" src/app/routers/defects.py src/app/routers/evidence.py 2>/dev/null | grep -v "# "
    ((FAILED++))
fi

# Check 3: Test Coverage
print_header "3. Test Coverage Analysis"

echo "Counting tests in test_defects.py..."
if [ -f "tests/test_defects.py" ]; then
    DEFECTS_TEST_COUNT=$(grep -c "def test_" tests/test_defects.py 2>/dev/null || echo "0")
    if [ "$DEFECTS_TEST_COUNT" -ge 10 ]; then
        print_success "test_defects.py: $DEFECTS_TEST_COUNT tests (target: ≥10)"
        ((PASSED++))
    else
        print_warning "test_defects.py: Only $DEFECTS_TEST_COUNT tests (target: ≥10)"
        ((WARNINGS++))
    fi
else
    print_error "test_defects.py not found"
    ((FAILED++))
fi

echo ""
echo "Counting tests in test_evidence*.py..."
EVIDENCE_TEST_COUNT=0
for file in tests/test_evidence*.py; do
    if [ -f "$file" ]; then
        COUNT=$(grep -c "def test_" "$file" 2>/dev/null || echo "0")
        EVIDENCE_TEST_COUNT=$((EVIDENCE_TEST_COUNT + COUNT))
        print_info "$(basename $file): $COUNT tests"
    fi
done

if [ "$EVIDENCE_TEST_COUNT" -ge 10 ]; then
    print_success "Evidence tests: $EVIDENCE_TEST_COUNT total tests (target: ≥10)"
    ((PASSED++))
else
    print_warning "Evidence tests: Only $EVIDENCE_TEST_COUNT tests (target: ≥10)"
    ((WARNINGS++))
fi

# Check 4: Docstrings
print_header "4. Documentation (Docstrings)"

echo "Checking defects router docstrings..."
DEFECTS_ROUTER_FUNCS=$(grep -c "^async def\|^def" src/app/routers/defects.py 2>/dev/null || echo "0")
DEFECTS_ROUTER_DOCS=$(grep -c '"""' src/app/routers/defects.py 2>/dev/null || echo "0")
# Each function should have a docstring (opening """), so docs should be >= functions
if [ "$DEFECTS_ROUTER_DOCS" -ge "$DEFECTS_ROUTER_FUNCS" ]; then
    print_success "Defects router: $DEFECTS_ROUTER_FUNCS functions, $DEFECTS_ROUTER_DOCS docstrings"
    ((PASSED++))
else
    print_warning "Defects router: $DEFECTS_ROUTER_FUNCS functions, $DEFECTS_ROUTER_DOCS docstrings (some may be missing)"
    ((WARNINGS++))
fi

echo ""
echo "Checking evidence router docstrings..."
EVIDENCE_ROUTER_FUNCS=$(grep -c "^async def\|^def" src/app/routers/evidence.py 2>/dev/null || echo "0")
EVIDENCE_ROUTER_DOCS=$(grep -c '"""' src/app/routers/evidence.py 2>/dev/null || echo "0")
if [ "$EVIDENCE_ROUTER_DOCS" -ge "$EVIDENCE_ROUTER_FUNCS" ]; then
    print_success "Evidence router: $EVIDENCE_ROUTER_FUNCS functions, $EVIDENCE_ROUTER_DOCS docstrings"
    ((PASSED++))
else
    print_warning "Evidence router: $EVIDENCE_ROUTER_FUNCS functions, $EVIDENCE_ROUTER_DOCS docstrings (some may be missing)"
    ((WARNINGS++))
fi

# Check 5: Import Organization
print_header "5. Import Organization"

echo "Checking for proper import grouping (stdlib, third-party, local)..."
# This is a simple check - just verify that imports are at the top of the file
DEFECTS_IMPORTS_OK=true
if grep -q "^import\|^from" src/app/routers/defects.py; then
    # Check if there are any imports after the first function definition
    IMPORTS_AFTER_CODE=$(awk '/^(async )?def /,0' src/app/routers/defects.py | grep -c "^import\|^from" 2>/dev/null || echo "0")
    if [ "$IMPORTS_AFTER_CODE" -eq 0 ]; then
        print_success "Defects router: Imports properly organized at top of file"
        ((PASSED++))
    else
        print_warning "Defects router: Found $IMPORTS_AFTER_CODE imports after code (should be at top)"
        ((WARNINGS++))
    fi
else
    print_error "Defects router: No imports found"
    ((FAILED++))
fi

# Check 6: File Structure
print_header "6. File Structure"

echo "Checking required files exist..."
REQUIRED_FILES=(
    "src/app/routers/defects.py"
    "src/app/routers/evidence.py"
    "src/app/models/defects.py"
    "src/app/models/evidence.py"
    "src/app/schemas/defect.py"
    "src/app/schemas/evidence.py"
    "tests/test_defects.py"
)

MISSING_FILES=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "File exists: $file"
    else
        print_error "File missing: $file"
        ((MISSING_FILES++))
    fi
done

if [ "$MISSING_FILES" -eq 0 ]; then
    ((PASSED++))
else
    print_error "Missing $MISSING_FILES required files"
    ((FAILED++))
fi

# Summary
print_header "Code Quality Summary"

echo ""
echo -e "${BOLD}Results:${NC}"
echo -e "  ${GREEN}Passed:${NC}   $PASSED"
echo -e "  ${RED}Failed:${NC}   $FAILED"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
echo ""

# Calculate percentage
TOTAL=$((PASSED + FAILED))
if [ "$TOTAL" -gt 0 ]; then
    PERCENTAGE=$((PASSED * 100 / TOTAL))
    echo -e "${BOLD}Quality Score: $PERCENTAGE%${NC}"
    echo ""
fi

# Exit with appropriate code
if [ "$FAILED" -eq 0 ]; then
    if [ "$WARNINGS" -eq 0 ]; then
        echo -e "${BOLD}${GREEN}✅ All code quality checks passed!${NC}"
        echo ""
        exit 0
    else
        echo -e "${BOLD}${YELLOW}✅ Code quality checks passed with $WARNINGS warnings${NC}"
        echo ""
        exit 0
    fi
else
    echo -e "${BOLD}${RED}❌ Code quality checks failed - please fix the issues above${NC}"
    echo ""
    exit 1
fi
