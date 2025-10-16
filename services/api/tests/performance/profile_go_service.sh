#!/bin/bash

# FM-ENH-005: Go Service Profiling Script
# Automated profiling workflow for performance testing

set -e

# Configuration
GO_SERVICE_URL=${GO_SERVICE_URL:-"http://localhost:9091"}
PPROF_URL=${PPROF_URL:-"http://localhost:6060"}
PROFILE_DIR=${PROFILE_DIR:-"./profiles"}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create profile directory
mkdir -p "$PROFILE_DIR"

echo -e "${BLUE}FM-ENH-005: Go Service Profiling${NC}"
echo "=================================="
echo "Profile Directory: $PROFILE_DIR"
echo "Go Service URL: $GO_SERVICE_URL"
echo "pprof URL: $PPROF_URL"
echo "Timestamp: $TIMESTAMP"
echo ""

# Function to check service health
check_service_health() {
    echo -e "${YELLOW}Checking Go service health...${NC}"
    
    if curl -s -f "$GO_SERVICE_URL/health" > /dev/null; then
        echo -e "${GREEN}✅ Go service is healthy${NC}"
    else
        echo -e "${RED}❌ Go service health check failed${NC}"
        echo "Make sure the Go service is running on $GO_SERVICE_URL"
        exit 1
    fi
    
    # Check pprof endpoint
    if curl -s -f "$PPROF_URL/debug/pprof/" > /dev/null; then
        echo -e "${GREEN}✅ pprof endpoint is accessible${NC}"
    else
        echo -e "${RED}❌ pprof endpoint not accessible${NC}"
        echo "Make sure pprof is enabled on $PPROF_URL"
        exit 1
    fi
    echo ""
}

# Function to capture memory stats
capture_memory_stats() {
    local test_name=$1
    local filename="$PROFILE_DIR/memory_stats_${test_name}_${TIMESTAMP}.json"
    
    echo -e "${YELLOW}Capturing memory stats for $test_name...${NC}"
    
    if curl -s "$GO_SERVICE_URL/memory" > "$filename"; then
        echo -e "${GREEN}✅ Memory stats saved to $filename${NC}"
        
        # Display key metrics
        heap_mb=$(cat "$filename" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'{data.get(\"heap_alloc_mb\", 0):.1f}')")
        goroutines=$(cat "$filename" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('num_goroutines', 0))")
        
        echo "   Heap Allocation: ${heap_mb}MB"
        echo "   Goroutines: $goroutines"
        
        # Check memory limit
        if (( $(echo "$heap_mb < 512" | bc -l) )); then
            echo -e "${GREEN}   ✅ Memory usage < 512MB limit${NC}"
        else
            echo -e "${RED}   ❌ Memory usage > 512MB limit${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to capture memory stats${NC}"
    fi
    echo ""
}

# Function to capture heap profile
capture_heap_profile() {
    local test_name=$1
    local filename="$PROFILE_DIR/heap_${test_name}_${TIMESTAMP}.prof"
    
    echo -e "${YELLOW}Capturing heap profile for $test_name...${NC}"
    
    if curl -s "$PPROF_URL/debug/pprof/heap" > "$filename"; then
        echo -e "${GREEN}✅ Heap profile saved to $filename${NC}"
        
        # Generate text report
        local text_report="$PROFILE_DIR/heap_report_${test_name}_${TIMESTAMP}.txt"
        if command -v go > /dev/null; then
            go tool pprof -text "$filename" > "$text_report" 2>/dev/null || echo "Could not generate text report"
            echo "   Text report: $text_report"
        fi
        
        # Generate top allocations
        local top_report="$PROFILE_DIR/heap_top_${test_name}_${TIMESTAMP}.txt"
        if command -v go > /dev/null; then
            go tool pprof -top "$filename" > "$top_report" 2>/dev/null || echo "Could not generate top report"
            echo "   Top allocations: $top_report"
        fi
    else
        echo -e "${RED}❌ Failed to capture heap profile${NC}"
    fi
    echo ""
}

# Function to capture CPU profile
capture_cpu_profile() {
    local test_name=$1
    local duration=${2:-30}  # Default 30 seconds
    local filename="$PROFILE_DIR/cpu_${test_name}_${TIMESTAMP}.prof"
    
    echo -e "${YELLOW}Capturing CPU profile for $test_name (${duration}s)...${NC}"
    
    # Start CPU profiling
    curl -s "$PPROF_URL/debug/pprof/profile?seconds=$duration" > "$filename" &
    local profile_pid=$!
    
    echo "   CPU profiling started (PID: $profile_pid)"
    echo "   Duration: ${duration}s"
    
    # Wait for profile to complete
    wait $profile_pid
    
    if [ -s "$filename" ]; then
        echo -e "${GREEN}✅ CPU profile saved to $filename${NC}"
        
        # Generate text report
        local text_report="$PROFILE_DIR/cpu_report_${test_name}_${TIMESTAMP}.txt"
        if command -v go > /dev/null; then
            go tool pprof -text "$filename" > "$text_report" 2>/dev/null || echo "Could not generate text report"
            echo "   Text report: $text_report"
        fi
    else
        echo -e "${RED}❌ Failed to capture CPU profile${NC}"
    fi
    echo ""
}

# Function to capture goroutine profile
capture_goroutine_profile() {
    local test_name=$1
    local filename="$PROFILE_DIR/goroutines_${test_name}_${TIMESTAMP}.prof"
    
    echo -e "${YELLOW}Capturing goroutine profile for $test_name...${NC}"
    
    if curl -s "$PPROF_URL/debug/pprof/goroutine" > "$filename"; then
        echo -e "${GREEN}✅ Goroutine profile saved to $filename${NC}"
        
        # Count goroutines
        local count=$(curl -s "$PPROF_URL/debug/pprof/goroutine?debug=1" | grep -c "^goroutine" || echo "0")
        echo "   Active goroutines: $count"
        
        # Generate text report
        local text_report="$PROFILE_DIR/goroutines_report_${test_name}_${TIMESTAMP}.txt"
        if command -v go > /dev/null; then
            go tool pprof -text "$filename" > "$text_report" 2>/dev/null || echo "Could not generate text report"
            echo "   Text report: $text_report"
        fi
    else
        echo -e "${RED}❌ Failed to capture goroutine profile${NC}"
    fi
    echo ""
}

# Function to monitor memory during test
monitor_memory_during_test() {
    local test_name=$1
    local duration=${2:-300}  # Default 5 minutes
    local interval=${3:-10}   # Default 10 seconds
    local filename="$PROFILE_DIR/memory_monitor_${test_name}_${TIMESTAMP}.csv"
    
    echo -e "${YELLOW}Monitoring memory during $test_name test...${NC}"
    echo "Duration: ${duration}s, Interval: ${interval}s"
    
    # Create CSV header
    echo "timestamp,heap_alloc_mb,heap_sys_mb,num_goroutines,gc_count" > "$filename"
    
    local end_time=$(($(date +%s) + duration))
    
    while [ $(date +%s) -lt $end_time ]; do
        local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
        
        # Get memory stats
        local stats=$(curl -s "$GO_SERVICE_URL/memory" 2>/dev/null || echo '{}')
        
        if [ "$stats" != "{}" ]; then
            local heap_alloc=$(echo "$stats" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'{data.get(\"heap_alloc_mb\", 0):.2f}')" 2>/dev/null || echo "0")
            local heap_sys=$(echo "$stats" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'{data.get(\"heap_sys_mb\", 0):.2f}')" 2>/dev/null || echo "0")
            local goroutines=$(echo "$stats" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('num_goroutines', 0))" 2>/dev/null || echo "0")
            local gc_count=$(echo "$stats" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('num_gc', 0))" 2>/dev/null || echo "0")
            
            echo "$timestamp,$heap_alloc,$heap_sys,$goroutines,$gc_count" >> "$filename"
            echo "   $timestamp: Heap=${heap_alloc}MB, Goroutines=$goroutines"
        fi
        
        sleep $interval
    done
    
    echo -e "${GREEN}✅ Memory monitoring complete: $filename${NC}"
    echo ""
}

# Function to generate profiling summary
generate_profiling_summary() {
    local test_name=$1
    local summary_file="$PROFILE_DIR/profiling_summary_${test_name}_${TIMESTAMP}.md"
    
    echo -e "${YELLOW}Generating profiling summary...${NC}"
    
    cat > "$summary_file" << EOF
# Go Service Profiling Summary - $test_name

**Test:** $test_name  
**Timestamp:** $TIMESTAMP  
**Go Service URL:** $GO_SERVICE_URL  

## Memory Statistics

EOF

    # Add memory stats if available
    local memory_file="$PROFILE_DIR/memory_stats_${test_name}_${TIMESTAMP}.json"
    if [ -f "$memory_file" ]; then
        echo "### Current Memory Usage" >> "$summary_file"
        echo '```json' >> "$summary_file"
        cat "$memory_file" >> "$summary_file"
        echo '```' >> "$summary_file"
        echo "" >> "$summary_file"
    fi
    
    # Add heap profile info
    local heap_file="$PROFILE_DIR/heap_${test_name}_${TIMESTAMP}.prof"
    if [ -f "$heap_file" ]; then
        echo "### Heap Profile" >> "$summary_file"
        echo "- Profile file: \`$(basename "$heap_file")\`" >> "$summary_file"
        echo "- Size: $(ls -lh "$heap_file" | awk '{print $5}')" >> "$summary_file"
        echo "" >> "$summary_file"
    fi
    
    # Add CPU profile info
    local cpu_file="$PROFILE_DIR/cpu_${test_name}_${TIMESTAMP}.prof"
    if [ -f "$cpu_file" ]; then
        echo "### CPU Profile" >> "$summary_file"
        echo "- Profile file: \`$(basename "$cpu_file")\`" >> "$summary_file"
        echo "- Size: $(ls -lh "$cpu_file" | awk '{print $5}')" >> "$summary_file"
        echo "" >> "$summary_file"
    fi
    
    # Add memory monitoring info
    local monitor_file="$PROFILE_DIR/memory_monitor_${test_name}_${TIMESTAMP}.csv"
    if [ -f "$monitor_file" ]; then
        echo "### Memory Monitoring" >> "$summary_file"
        echo "- Monitoring data: \`$(basename "$monitor_file")\`" >> "$summary_file"
        echo "- Samples: $(($(wc -l < "$monitor_file") - 1))" >> "$summary_file"
        echo "" >> "$summary_file"
    fi
    
    echo "## Analysis Commands" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "To analyze the profiles:" >> "$summary_file"
    echo "" >> "$summary_file"
    
    if [ -f "$heap_file" ]; then
        echo "### Heap Analysis" >> "$summary_file"
        echo "\`\`\`bash" >> "$summary_file"
        echo "# Interactive heap analysis" >> "$summary_file"
        echo "go tool pprof -http=:8080 $heap_file" >> "$summary_file"
        echo "" >> "$summary_file"
        echo "# Text-based analysis" >> "$summary_file"
        echo "go tool pprof -text $heap_file" >> "$summary_file"
        echo "\`\`\`" >> "$summary_file"
        echo "" >> "$summary_file"
    fi
    
    if [ -f "$cpu_file" ]; then
        echo "### CPU Analysis" >> "$summary_file"
        echo "\`\`\`bash" >> "$summary_file"
        echo "# Interactive CPU analysis" >> "$summary_file"
        echo "go tool pprof -http=:8080 $cpu_file" >> "$summary_file"
        echo "" >> "$summary_file"
        echo "# Text-based analysis" >> "$summary_file"
        echo "go tool pprof -text $cpu_file" >> "$summary_file"
        echo "\`\`\`" >> "$summary_file"
    fi
    
    echo -e "${GREEN}✅ Profiling summary saved to $summary_file${NC}"
    echo ""
}

# Main profiling workflow
main() {
    local test_name=${1:-"default"}
    local test_duration=${2:-300}  # Default 5 minutes
    local action=${3:-"full"}      # full, memory, heap, cpu, goroutines, monitor
    
    echo -e "${BLUE}Starting Go service profiling for test: $test_name${NC}"
    echo "Test duration: ${test_duration}s"
    echo "Action: $action"
    echo ""
    
    # Check service health
    check_service_health
    
    case $action in
        "full")
            echo -e "${BLUE}Running full profiling suite...${NC}"
            capture_memory_stats "pre_$test_name"
            capture_heap_profile "pre_$test_name"
            capture_goroutine_profile "pre_$test_name"
            
            echo -e "${BLUE}Starting memory monitoring during test...${NC}"
            monitor_memory_during_test "$test_name" "$test_duration" 10 &
            local monitor_pid=$!
            
            echo -e "${BLUE}Capturing CPU profile during test...${NC}"
            capture_cpu_profile "$test_name" "$test_duration" &
            local cpu_pid=$!
            
            # Wait for test to complete
            echo -e "${YELLOW}Waiting for test to complete (${test_duration}s)...${NC}"
            sleep "$test_duration"
            
            # Wait for background processes
            wait $monitor_pid $cpu_pid
            
            capture_memory_stats "post_$test_name"
            capture_heap_profile "post_$test_name"
            capture_goroutine_profile "post_$test_name"
            ;;
            
        "memory")
            capture_memory_stats "$test_name"
            ;;
            
        "heap")
            capture_heap_profile "$test_name"
            ;;
            
        "cpu")
            capture_cpu_profile "$test_name" "$test_duration"
            ;;
            
        "goroutines")
            capture_goroutine_profile "$test_name"
            ;;
            
        "monitor")
            monitor_memory_during_test "$test_name" "$test_duration" 10
            ;;
            
        *)
            echo -e "${RED}Unknown action: $action${NC}"
            echo "Available actions: full, memory, heap, cpu, goroutines, monitor"
            exit 1
            ;;
    esac
    
    # Generate summary
    generate_profiling_summary "$test_name"
    
    echo -e "${GREEN}Profiling complete for test: $test_name${NC}"
    echo "Profile files saved in: $PROFILE_DIR"
    echo ""
    
    # List generated files
    echo -e "${BLUE}Generated files:${NC}"
    ls -la "$PROFILE_DIR"/*"$test_name"*"$TIMESTAMP"* 2>/dev/null || echo "No files found"
}

# Show usage if no arguments provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <test_name> [duration] [action]"
    echo ""
    echo "Arguments:"
    echo "  test_name  - Name of the test (e.g., sustained, peak, spike, crdt_stress)"
    echo "  duration   - Test duration in seconds (default: 300)"
    echo "  action     - Profiling action (default: full)"
    echo ""
    echo "Actions:"
    echo "  full       - Complete profiling suite (memory, heap, cpu, goroutines, monitoring)"
    echo "  memory     - Memory stats only"
    echo "  heap       - Heap profile only"
    echo "  cpu        - CPU profile only"
    echo "  goroutines - Goroutine profile only"
    echo "  monitor    - Memory monitoring only"
    echo ""
    echo "Examples:"
    echo "  $0 sustained 14400 full      # 4-hour sustained test"
    echo "  $0 peak 3600 memory          # 1-hour peak test, memory only"
    echo "  $0 spike 300 cpu             # 5-minute spike test, CPU profile"
    echo ""
    exit 1
fi

# Run main function
main "$@"
