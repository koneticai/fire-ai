#!/bin/bash

# FM-ENH-005: Test Orchestration Script
# Orchestrates complete performance test suite for 100k req/day validation

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Environment variables
FASTAPI_BASE_URL=${FASTAPI_BASE_URL:-"http://localhost:8080"}
GO_SERVICE_URL=${GO_SERVICE_URL:-"http://localhost:9091"}
DATABASE_URL=${DATABASE_URL:-"postgresql://localhost/firemode"}
INTERNAL_JWT_SECRET_KEY=${INTERNAL_JWT_SECRET_KEY:-"default-secret-for-testing"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test configurations
declare -A TEST_CONFIGS
TEST_CONFIGS["sustained"]="5 1 4h 'Sustained baseline load (4 hours) - Memory leaks, connection stability'"
TEST_CONFIGS["peak"]="50 10 1h 'Peak load (1 hour) - p95 latency <300ms validation'"
TEST_CONFIGS["spike"]="200 50 5m 'Spike/Burst (5 minutes) - Aurora auto-scaling, no dropped requests'"
TEST_CONFIGS["crdt_stress"]="1000 100 10m 'CRDT Stress (10 minutes) - Zero data loss, 1000+ concurrent conflicts'"

echo -e "${BLUE}FM-ENH-005: Performance Validation Test Suite${NC}"
echo "=================================================="
echo "Target: 100k req/day (5x current target)"
echo "Timestamp: $TIMESTAMP"
echo "Results Directory: $RESULTS_DIR"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Function to print section headers
print_section() {
    echo ""
    echo -e "${PURPLE}$1${NC}"
    echo "$(printf '=%.0s' {1..60})"
    echo ""
}

# Function to check service health
check_services() {
    print_section "PRE-FLIGHT CHECKS"
    
    echo -e "${YELLOW}Checking FastAPI service...${NC}"
    if curl -s -f "$FASTAPI_BASE_URL/health" > /dev/null; then
        echo -e "${GREEN}✅ FastAPI service is healthy${NC}"
    else
        echo -e "${RED}❌ FastAPI service health check failed${NC}"
        echo "Make sure the FastAPI service is running on $FASTAPI_BASE_URL"
        exit 1
    fi
    
    echo -e "${YELLOW}Checking Go service...${NC}"
    if curl -s -f "$GO_SERVICE_URL/health" > /dev/null; then
        echo -e "${GREEN}✅ Go service is healthy${NC}"
    else
        echo -e "${RED}❌ Go service health check failed${NC}"
        echo "Make sure the Go service is running on $GO_SERVICE_URL"
        exit 1
    fi
    
    echo -e "${YELLOW}Checking pprof endpoint...${NC}"
    if curl -s -f "http://localhost:6060/debug/pprof/" > /dev/null; then
        echo -e "${GREEN}✅ pprof endpoint is accessible${NC}"
    else
        echo -e "${RED}❌ pprof endpoint not accessible${NC}"
        echo "Make sure pprof is enabled on http://localhost:6060"
        exit 1
    fi
    
    echo -e "${YELLOW}Checking database connection...${NC}"
    if command -v psql > /dev/null; then
        if echo "SELECT 1;" | psql "$DATABASE_URL" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Database connection successful${NC}"
        else
            echo -e "${RED}❌ Database connection failed${NC}"
            echo "Make sure DATABASE_URL is correct: $DATABASE_URL"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  psql not available, skipping database check${NC}"
    fi
    
    echo -e "${YELLOW}Checking Locust installation...${NC}"
    if command -v locust > /dev/null; then
        echo -e "${GREEN}✅ Locust is installed${NC}"
    else
        echo -e "${RED}❌ Locust is not installed${NC}"
        echo "Install with: pip install locust"
        exit 1
    fi
    
    echo ""
}

# Function to run a single test
run_test() {
    local test_name=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local description=$5
    
    print_section "RUNNING TEST: $test_name"
    echo "Description: $description"
    echo "Users: $users"
    echo "Spawn Rate: $spawn_rate"
    echo "Duration: $duration"
    echo ""
    
    # Create test-specific results directory
    local test_results_dir="$RESULTS_DIR/${test_name}_${TIMESTAMP}"
    mkdir -p "$test_results_dir"
    
    # Export environment variables for the test
    export FASTAPI_BASE_URL
    export GO_SERVICE_URL
    export DATABASE_URL
    export INTERNAL_JWT_SECRET_KEY
    
    # Start Go service profiling
    echo -e "${YELLOW}Starting Go service profiling...${NC}"
    local profile_script="$SCRIPT_DIR/profile_go_service.sh"
    if [ -f "$profile_script" ]; then
        # Convert duration to seconds for profiling
        local duration_seconds
        case $duration in
            *h) duration_seconds=$((${duration%h} * 3600)) ;;
            *m) duration_seconds=$((${duration%m} * 60)) ;;
            *s) duration_seconds=${duration%s} ;;
            *) duration_seconds=300 ;;  # Default 5 minutes
        esac
        
        # Start profiling in background
        "$profile_script" "$test_name" "$duration_seconds" "full" > "$test_results_dir/profiling.log" 2>&1 &
        local profile_pid=$!
        echo "Profiling PID: $profile_pid"
        
        # Give profiling a moment to start
        sleep 5
    else
        echo -e "${YELLOW}⚠️  Profiling script not found, skipping profiling${NC}"
        local profile_pid=""
    fi
    
    # Run Locust test
    echo -e "${YELLOW}Starting Locust test...${NC}"
    local locust_command="locust -f $SCRIPT_DIR/test_load_100k.py --headless --host $FASTAPI_BASE_URL -u $users -r $spawn_rate --run-time $duration --csv $test_results_dir/$test_name --html $test_results_dir/${test_name}_report.html"
    
    echo "Command: $locust_command"
    echo ""
    
    # Run the test and capture exit code
    local test_start_time=$(date +%s)
    if $locust_command > "$test_results_dir/locust.log" 2>&1; then
        local test_exit_code=0
        echo -e "${GREEN}✅ Test completed successfully${NC}"
    else
        local test_exit_code=$?
        echo -e "${RED}❌ Test failed with exit code $test_exit_code${NC}"
    fi
    local test_end_time=$(date +%s)
    local test_duration=$((test_end_time - test_start_time))
    
    echo "Test duration: ${test_duration}s"
    
    # Stop profiling
    if [ -n "$profile_pid" ]; then
        echo -e "${YELLOW}Stopping profiling...${NC}"
        sleep 10  # Let profiling finish current operations
        if kill -0 "$profile_pid" 2>/dev/null; then
            kill "$profile_pid" 2>/dev/null || true
            wait "$profile_pid" 2>/dev/null || true
        fi
        echo -e "${GREEN}✅ Profiling stopped${NC}"
    fi
    
    # Collect additional metrics
    echo -e "${YELLOW}Collecting final metrics...${NC}"
    
    # Get final memory stats
    if curl -s "$GO_SERVICE_URL/memory" > "$test_results_dir/final_memory_stats.json" 2>/dev/null; then
        echo -e "${GREEN}✅ Final memory stats collected${NC}"
    fi
    
    # Copy profiling results
    if [ -d "$SCRIPT_DIR/profiles" ]; then
        cp -r "$SCRIPT_DIR/profiles" "$test_results_dir/" 2>/dev/null || true
        echo -e "${GREEN}✅ Profiling results copied${NC}"
    fi
    
    # Generate test summary
    cat > "$test_results_dir/test_summary.md" << EOF
# Test Summary: $test_name

**Timestamp:** $TIMESTAMP  
**Description:** $description  
**Users:** $users  
**Spawn Rate:** $spawn_rate  
**Duration:** $duration  
**Actual Duration:** ${test_duration}s  
**Exit Code:** $test_exit_code  

## Files Generated

- \`$test_name.csv\` - Locust CSV results
- \`${test_name}_report.html\` - Locust HTML report
- \`locust.log\` - Locust execution log
- \`profiling.log\` - Go service profiling log
- \`final_memory_stats.json\` - Final memory statistics
- \`profiles/\` - Go service profiling data

## Quick Analysis

\`\`\`bash
# View Locust results
head -n 20 $test_name.csv

# Check memory usage
cat final_memory_stats.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Heap: {data.get(\"heap_alloc_mb\", 0):.1f}MB, Goroutines: {data.get(\"num_goroutines\", 0)}')"

# View profiling summary
find profiles -name "*${test_name}*summary*.md" -exec cat {} \;
\`\`\`
EOF
    
    echo -e "${GREEN}✅ Test summary generated${NC}"
    echo "Results saved in: $test_results_dir"
    
    # Return test results
    echo "$test_name:$test_exit_code:$test_results_dir"
}

# Function to run all tests
run_all_tests() {
    print_section "RUNNING ALL TESTS"
    
    local test_results=()
    local failed_tests=()
    
    for test_name in "${!TEST_CONFIGS[@]}"; do
        IFS=' ' read -r users spawn_rate duration description <<< "${TEST_CONFIGS[$test_name]}"
        
        local result=$(run_test "$test_name" "$users" "$spawn_rate" "$duration" "$description")
        local exit_code=$(echo "$result" | cut -d: -f2)
        local results_dir=$(echo "$result" | cut -d: -f3)
        
        test_results+=("$result")
        
        if [ "$exit_code" != "0" ]; then
            failed_tests+=("$test_name")
        fi
        
        # Brief pause between tests
        echo -e "${YELLOW}Pausing 30 seconds before next test...${NC}"
        sleep 30
    done
    
    # Generate consolidated report
    generate_consolidated_report "${test_results[@]}"
    
    # Final summary
    print_section "FINAL SUMMARY"
    
    if [ ${#failed_tests[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All tests completed successfully!${NC}"
    else
        echo -e "${RED}❌ Some tests failed:${NC}"
        for test in "${failed_tests[@]}"; do
            echo -e "${RED}  - $test${NC}"
        done
    fi
    
    echo ""
    echo "All results saved in: $RESULTS_DIR"
    echo "Run analysis script to generate detailed report:"
    echo "  python3 $SCRIPT_DIR/analyze_results.py $RESULTS_DIR"
}

# Function to generate consolidated report
generate_consolidated_report() {
    local test_results=("$@")
    
    print_section "GENERATING CONSOLIDATED REPORT"
    
    local report_file="$RESULTS_DIR/consolidated_report_${TIMESTAMP}.md"
    
    cat > "$report_file" << EOF
# FM-ENH-005: Consolidated Performance Test Report

**Generated:** $(date)  
**Test Suite:** 100k req/day Performance Validation  
**Timestamp:** $TIMESTAMP  

## Test Summary

| Test | Users | Duration | Status | Results Directory |
|------|-------|----------|--------|-------------------|
EOF

    for result in "${test_results[@]}"; do
        local test_name=$(echo "$result" | cut -d: -f1)
        local exit_code=$(echo "$result" | cut -d: -f2)
        local results_dir=$(echo "$result" | cut -d: -f3)
        
        local status
        if [ "$exit_code" = "0" ]; then
            status="✅ PASSED"
        else
            status="❌ FAILED"
        fi
        
        local config="${TEST_CONFIGS[$test_name]}"
        local users=$(echo "$config" | cut -d' ' -f1)
        local duration=$(echo "$config" | cut -d' ' -f3)
        
        echo "| $test_name | $users | $duration | $status | \`$(basename "$results_dir")\` |" >> "$report_file"
    done
    
    cat >> "$report_file" << EOF

## Acceptance Criteria Validation

### 1. p95 latency <300ms at 100k req/day
- **Test:** Peak Load (Test 2)
- **Status:** See individual test results
- **Requirement:** P95 latency must be ≤ 300ms

### 2. Zero data loss in CRDT conflicts (1000+ concurrent)
- **Test:** CRDT Stress (Test 4)
- **Status:** See individual test results
- **Requirement:** All CRDT operations must succeed without data loss

### 3. Aurora auto-scaling capability
- **Test:** Spike/Burst (Test 3)
- **Status:** See individual test results
- **Requirement:** System must handle 10k requests in 5 minutes

### 4. Go service memory <512MB under sustained load
- **Test:** All tests with profiling
- **Status:** See profiling results
- **Requirement:** Memory usage must stay below 512MB

## Next Steps

1. Run detailed analysis:
   \`\`\`bash
   python3 $SCRIPT_DIR/analyze_results.py $RESULTS_DIR
   \`\`\`

2. Review individual test reports:
   \`\`\`bash
   find $RESULTS_DIR -name "*_report.html" -exec open {} \;
   \`\`\`

3. Analyze profiling data:
   \`\`\`bash
   find $RESULTS_DIR -name "profiling_summary*.md" -exec cat {} \;
   \`\`\`

## Environment

- **FastAPI URL:** $FASTAPI_BASE_URL
- **Go Service URL:** $GO_SERVICE_URL
- **Database:** $DATABASE_URL
- **Timestamp:** $TIMESTAMP

EOF

    echo -e "${GREEN}✅ Consolidated report generated: $report_file${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [test_name]"
    echo ""
    echo "Run specific test:"
    for test_name in "${!TEST_CONFIGS[@]}"; do
        local config="${TEST_CONFIGS[$test_name]}"
        local users=$(echo "$config" | cut -d' ' -f1)
        local duration=$(echo "$config" | cut -d' ' -f3)
        local description=$(echo "$config" | cut -d' ' -f4-)
        echo "  $0 $test_name"
        echo "    $description"
        echo "    Users: $users, Duration: $duration"
        echo ""
    done
    echo "Run all tests:"
    echo "  $0 all"
    echo ""
    echo "Available tests: ${!TEST_CONFIGS[@]}"
}

# Main execution
main() {
    local test_name=${1:-"all"}
    
    # Check if test name is valid
    if [ "$test_name" != "all" ] && [ -z "${TEST_CONFIGS[$test_name]}" ]; then
        echo -e "${RED}Error: Unknown test name '$test_name'${NC}"
        echo ""
        show_usage
        exit 1
    fi
    
    # Run pre-flight checks
    check_services
    
    if [ "$test_name" = "all" ]; then
        run_all_tests
    else
        local config="${TEST_CONFIGS[$test_name]}"
        IFS=' ' read -r users spawn_rate duration description <<< "$config"
        run_test "$test_name" "$users" "$spawn_rate" "$duration" "$description"
    fi
}

# Show usage if no arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

# Run main function
main "$@"
