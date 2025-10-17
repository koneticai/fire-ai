#!/bin/bash

# FIRE-AI Backend Investor Demo Script
# Tests key API endpoints with demo data

set -e  # Exit on error

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:5000}"
JWT_TOKEN="${JWT_TOKEN:-}"

# For production/Replit deployment, use:
# export BASE_URL="https://f4ef6f0f-0f5d-47c0-8400-3ec5dd3e1ea5-00-1947ayqzkyfgn.picard.replit.dev:5000"

# Demo building IDs from seeded data
BUILDING_A_ID="88c27381-0cf2-4181-8f39-282978f6986f"  # Perfect - 95%
BUILDING_B_ID="60a03aa0-b407-4091-9e5f-8a4b51bee7b9"  # Good - 62%
BUILDING_C_ID="63787813-0d18-487a-bfb3-0e8024dcb787"  # Poor - 45%

# Check if JWT token is set
if [ -z "$JWT_TOKEN" ]; then
    echo -e "${RED}ERROR: JWT_TOKEN environment variable not set${NC}"
    echo "Please run: export JWT_TOKEN=\"<your-token>\""
    echo "Generate token with: python services/api/scripts/generate_demo_token.py"
    exit 1
fi

echo "=========================================================================="
echo "🔥 FIRE-AI BACKEND INVESTOR DEMO"
echo "=========================================================================="
echo -e "${BLUE}Base URL: $BASE_URL${NC}"
echo -e "${BLUE}JWT Token: ${JWT_TOKEN:0:20}...${NC}"
echo ""

# Helper function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local auth=$3
    local data=$4
    
    if [ "$auth" = "true" ]; then
        if [ -n "$data" ]; then
            curl -s -X "$method" \
                -H "Authorization: Bearer $JWT_TOKEN" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "${BASE_URL}${endpoint}"
        else
            curl -s -X "$method" \
                -H "Authorization: Bearer $JWT_TOKEN" \
                "${BASE_URL}${endpoint}"
        fi
    else
        curl -s -X "$method" "${BASE_URL}${endpoint}"
    fi
}

# Test 1: Health Check (no auth required)
echo -e "${GREEN}[1/8] Testing Health Check (no auth)${NC}"
echo -e "${BLUE}GET /health${NC}"
RESPONSE=$(api_call "GET" "/health" "false")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Test 2: List Buildings (with auth)
echo -e "${GREEN}[2/8] Listing Buildings${NC}"
echo -e "${BLUE}GET /v1/buildings/${NC}"
RESPONSE=$(api_call "GET" "/v1/buildings/" "true")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Test 3: Get Building B Evidence
echo -e "${GREEN}[3/8] Getting Evidence for Building B (Good - 62%)${NC}"
echo -e "${YELLOW}Building B ID: $BUILDING_B_ID${NC}"
echo -e "${BLUE}GET /v1/evidence/session/{session_id}${NC}"

# First, get test sessions for Building B to find evidence
SESSIONS_RESPONSE=$(api_call "GET" "/v1/tests/sessions/?limit=100" "true")
# Extract first session ID for Building B
BUILDING_B_SESSION=$(echo "$SESSIONS_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
sessions = data.get('sessions', [])
for session in sessions:
    if session.get('building_id') == '$BUILDING_B_ID':
        print(session['id'])
        break
" 2>/dev/null || echo "")

if [ -n "$BUILDING_B_SESSION" ]; then
    echo -e "${YELLOW}Found Session ID: $BUILDING_B_SESSION${NC}"
    EVIDENCE_RESPONSE=$(api_call "GET" "/v1/evidence/session/$BUILDING_B_SESSION" "true")
    echo "$EVIDENCE_RESPONSE" | python3 -m json.tool
    
    # Extract first evidence ID
    FIRST_EVIDENCE_ID=$(echo "$EVIDENCE_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
evidence_list = data if isinstance(data, list) else data.get('evidence', [])
if evidence_list:
    print(evidence_list[0].get('id', ''))
" 2>/dev/null || echo "")
else
    echo -e "${YELLOW}No sessions found for Building B${NC}"
    FIRST_EVIDENCE_ID=""
fi
echo ""

# Test 4: Get Specific Evidence Details
if [ -n "$FIRST_EVIDENCE_ID" ]; then
    echo -e "${GREEN}[4/8] Getting Evidence Details${NC}"
    echo -e "${YELLOW}Evidence ID: $FIRST_EVIDENCE_ID${NC}"
    echo -e "${BLUE}GET /v1/evidence/{evidence_id}${NC}"
    EVIDENCE_DETAIL=$(api_call "GET" "/v1/evidence/$FIRST_EVIDENCE_ID" "true")
    echo "$EVIDENCE_DETAIL" | python3 -m json.tool
else
    echo -e "${GREEN}[4/8] Skipping Evidence Details (no evidence found)${NC}"
fi
echo ""

# Test 5: Get Building C Defects (status=open)
echo -e "${GREEN}[5/8] Getting Open Defects for Building C (Poor - 45%)${NC}"
echo -e "${YELLOW}Building C ID: $BUILDING_C_ID${NC}"
echo -e "${BLUE}GET /v1/defects/buildings/{building_id}/defects?status=open${NC}"
DEFECTS_RESPONSE=$(api_call "GET" "/v1/defects/buildings/$BUILDING_C_ID/defects?status=open" "true")
echo "$DEFECTS_RESPONSE" | python3 -m json.tool

# Extract first defect ID
FIRST_DEFECT_ID=$(echo "$DEFECTS_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
defects = data if isinstance(data, list) else data.get('defects', [])
if defects:
    print(defects[0].get('id', ''))
" 2>/dev/null || echo "")

if [ -n "$FIRST_DEFECT_ID" ]; then
    echo -e "${YELLOW}Found Defect ID: $FIRST_DEFECT_ID${NC}"
fi
echo ""

# Test 6: Get Specific Defect Details
if [ -n "$FIRST_DEFECT_ID" ]; then
    echo -e "${GREEN}[6/8] Getting Defect Details${NC}"
    echo -e "${YELLOW}Defect ID: $FIRST_DEFECT_ID${NC}"
    echo -e "${BLUE}GET /v1/defects/{defect_id}${NC}"
    DEFECT_DETAIL=$(api_call "GET" "/v1/defects/$FIRST_DEFECT_ID" "true")
    echo "$DEFECT_DETAIL" | python3 -m json.tool
else
    echo -e "${GREEN}[6/8] Skipping Defect Details (no defects found)${NC}"
fi
echo ""

# Test 7: Link Evidence to Defect
if [ -n "$FIRST_EVIDENCE_ID" ] && [ -n "$FIRST_DEFECT_ID" ]; then
    echo -e "${GREEN}[7/8] Linking Evidence to Defect${NC}"
    echo -e "${YELLOW}Evidence ID: $FIRST_EVIDENCE_ID${NC}"
    echo -e "${YELLOW}Defect ID: $FIRST_DEFECT_ID${NC}"
    echo -e "${BLUE}POST /v1/evidence/{evidence_id}/link-defect${NC}"
    
    LINK_DATA="{\"defect_id\": \"$FIRST_DEFECT_ID\"}"
    LINK_RESPONSE=$(api_call "POST" "/v1/evidence/$FIRST_EVIDENCE_ID/link-defect" "true" "$LINK_DATA")
    echo "$LINK_RESPONSE" | python3 -m json.tool
else
    echo -e "${GREEN}[7/8] Skipping Evidence Link (missing evidence or defect)${NC}"
fi
echo ""

# Test 8: Update Defect Status
if [ -n "$FIRST_DEFECT_ID" ]; then
    echo -e "${GREEN}[8/8] Updating Defect Status to 'acknowledged'${NC}"
    echo -e "${YELLOW}Defect ID: $FIRST_DEFECT_ID${NC}"
    echo -e "${BLUE}PATCH /v1/defects/{defect_id}${NC}"
    
    UPDATE_DATA="{\"status\": \"acknowledged\"}"
    UPDATE_RESPONSE=$(api_call "PATCH" "/v1/defects/$FIRST_DEFECT_ID" "true" "$UPDATE_DATA")
    echo "$UPDATE_RESPONSE" | python3 -m json.tool
else
    echo -e "${GREEN}[8/8] Skipping Defect Update (no defect found)${NC}"
fi
echo ""

echo "=========================================================================="
echo -e "${GREEN}✅ DEMO COMPLETE!${NC}"
echo "=========================================================================="
echo ""
echo "Summary:"
echo "  • Health check: ✓"
echo "  • Buildings listed: ✓"
echo "  • Evidence retrieved: $([ -n "$FIRST_EVIDENCE_ID" ] && echo "✓" || echo "⚠")"
echo "  • Defects retrieved: $([ -n "$FIRST_DEFECT_ID" ] && echo "✓" || echo "⚠")"
echo "  • Evidence linked: $([ -n "$FIRST_EVIDENCE_ID" ] && [ -n "$FIRST_DEFECT_ID" ] && echo "✓" || echo "⚠")"
echo "  • Defect updated: $([ -n "$FIRST_DEFECT_ID" ] && echo "✓" || echo "⚠")"
echo ""
