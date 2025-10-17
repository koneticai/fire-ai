# FIRE-AI Backend Investor Demo

Complete demonstration suite for the FIRE-AI Compliance Platform backend API.

## 📋 Overview

This demo showcases the core functionality of the FIRE-AI backend with pre-seeded demo data:

- **Building A** (88c27381-0cf2-4181-8f39-282978f6986f) - Perfect compliance (95%)
- **Building B** (60a03aa0-b407-4091-9e5f-8a4b51bee7b9) - Good compliance (62%)
- **Building C** (63787813-0d18-487a-bfb3-0e8024dcb787) - Poor compliance (45%)

## 🚀 Quick Start

### 1. Set JWT Secret Key

**IMPORTANT**: The JWT_SECRET_KEY must match the one used by the running server.

```bash
# Check your current JWT_SECRET_KEY
echo $JWT_SECRET_KEY

# If using the FireMode Backend workflow, use the key from the workflow config:
export JWT_SECRET_KEY="63181718e4df31f152a20da4502d844b0ced3041a561480f2071321a4006c39e"

# Or get it from your server's environment/config
```

### 2. Generate JWT Token

```bash
python services/api/scripts/generate_demo_token.py
```

**Copy the generated token** - you'll need it for authenticated requests.

**Troubleshooting**: If you get "Invalid token" errors, the JWT_SECRET_KEY used to generate the token doesn't match the server's key. Make sure both use the same secret.

### 3. Run the Demo Script

```bash
# Export the JWT token
export JWT_TOKEN="<paste-token-here>"

# Run the demo
bash docs/demo/run_investor_demo.sh
```

### 4. Use Postman (Alternative)

1. Import the collection: `docs/demo/FIRE-AI-Demo.postman_collection.json`
2. Import the environment: `docs/demo/FIRE-AI-Demo.postman_environment.json`
3. Update the `jwt_token` environment variable with your generated token
4. Run the requests in order

## 📊 Demo Endpoints

The demo tests 8 key endpoints that showcase the platform's capabilities:

### 1. Health Check (No Auth)
```bash
GET /health
```
**Demonstrates:** Service availability and status

**Expected Response:**
```json
{
  "status": "ok",
  "service": "firemode-backend",
  "go_service": {...}
}
```

### 2. List Buildings
```bash
GET /v1/buildings/
Authorization: Bearer <token>
```
**Demonstrates:** Portfolio overview with compliance scores

**Expected Response:**
```json
{
  "buildings": [
    {
      "building_id": "88c27381-0cf2-4181-8f39-282978f6986f",
      "name": "Building A",
      "compliance_status": "excellent",
      ...
    }
  ],
  "total": 3,
  "has_more": false
}
```

### 3. Get Building Evidence
```bash
GET /v1/evidence/session/{session_id}
Authorization: Bearer <token>
```
**Demonstrates:** Evidence tracking for compliance verification

**Expected Response:**
```json
[
  {
    "id": "evidence-uuid",
    "session_id": "session-uuid",
    "evidence_type": "photo",
    "file_hash": "sha256-hash",
    ...
  }
]
```

### 4. Get Evidence Details
```bash
GET /v1/evidence/{evidence_id}
Authorization: Bearer <token>
```
**Demonstrates:** Detailed evidence metadata and verification

**Expected Response:**
```json
{
  "id": "evidence-uuid",
  "evidence_type": "photo",
  "file_hash": "sha256-hash",
  "upload_timestamp": "2025-10-17T...",
  "metadata": {...}
}
```

### 5. Get Building Defects
```bash
GET /v1/defects/buildings/{building_c_id}/defects?status=open
Authorization: Bearer <token>
```
**Demonstrates:** Defect tracking and filtering

**Expected Response:**
```json
[
  {
    "id": "defect-uuid",
    "building_id": "63787813-0d18-487a-bfb3-0e8024dcb787",
    "severity": "high",
    "status": "open",
    "description": "...",
    ...
  }
]
```

### 6. Get Defect Details
```bash
GET /v1/defects/{defect_id}
Authorization: Bearer <token>
```
**Demonstrates:** Detailed defect information

**Expected Response:**
```json
{
  "id": "defect-uuid",
  "severity": "high",
  "category": "fire_safety",
  "description": "...",
  "as1851_rule_code": "...",
  "discovered_at": "2025-10-17T...",
  ...
}
```

### 7. Link Evidence to Defect
```bash
POST /v1/evidence/{evidence_id}/link-defect
Authorization: Bearer <token>
Content-Type: application/json

{
  "defect_id": "defect-uuid"
}
```
**Demonstrates:** Evidence-defect relationship tracking

**Expected Response:**
```json
{
  "evidence_id": "evidence-uuid",
  "defect_id": "defect-uuid",
  "evidence_ids": ["evidence-uuid"],
  "message": "Evidence linked successfully"
}
```

### 8. Update Defect Status
```bash
PATCH /v1/defects/{defect_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "acknowledged"
}
```
**Demonstrates:** Defect lifecycle management

**Expected Response:**
```json
{
  "id": "defect-uuid",
  "status": "acknowledged",
  "updated_at": "2025-10-17T...",
  ...
}
```

## 🔧 Configuration

### Environment Variables

The demo requires these environment variables:

```bash
# Required for token generation
export JWT_SECRET_KEY="your-secret-key"

# Optional: Override base URL (defaults to Replit URL)
export BASE_URL="https://your-domain.com:5000"
```

### Building IDs

Pre-seeded demo buildings:
- `BUILDING_A_ID`: 88c27381-0cf2-4181-8f39-282978f6986f (Perfect - 95%)
- `BUILDING_B_ID`: 60a03aa0-b407-4091-9e5f-8a4b51bee7b9 (Good - 62%)
- `BUILDING_C_ID`: 63787813-0d18-487a-bfb3-0e8024dcb787 (Poor - 45%)

## 🐛 Troubleshooting

### Issue: "JWT_TOKEN environment variable not set"

**Solution:**
```bash
# Generate token first
python services/api/scripts/generate_demo_token.py

# Export the token
export JWT_TOKEN="<your-token>"

# Verify it's set
echo $JWT_TOKEN
```

### Issue: "ERROR: JWT_SECRET_KEY environment variable not set"

**Solution:**
```bash
# Check if JWT_SECRET_KEY is set
echo $JWT_SECRET_KEY

# For FireMode Backend workflow, use:
export JWT_SECRET_KEY="63181718e4df31f152a20da4502d844b0ced3041a561480f2071321a4006c39e"

# Or get it from your server's environment/config file
# It must match the secret used by the running server!
```

### Issue: 403 Forbidden or 401 Unauthorized

**Possible causes:**
1. JWT token expired (tokens last 24 hours)
2. JWT_SECRET_KEY mismatch
3. Token not properly exported

**Solution:**
```bash
# Generate a fresh token
python services/api/scripts/generate_demo_token.py

# Re-export with the new token
export JWT_TOKEN="<new-token>"
```

### Issue: "No sessions/evidence/defects found"

**Possible causes:**
1. Demo data not seeded
2. Wrong building ID
3. Database empty

**Solution:**
```bash
# Check if buildings exist
curl -H "Authorization: Bearer $JWT_TOKEN" \
  https://your-url.com:5000/v1/buildings/

# If empty, seed demo data (contact admin)
```

### Issue: Connection refused or timeout

**Possible causes:**
1. Server not running
2. Wrong base URL
3. Network/firewall issues

**Solution:**
```bash
# Test health endpoint (no auth required)
curl https://your-url.com:5000/health

# If that fails, check if server is running
# Verify the base URL in your environment or script
```

### Issue: "Command not found: python3"

**Solution:**
```bash
# Try with python instead of python3
python services/api/scripts/generate_demo_token.py

# Or install Python 3 on your system
```

### Issue: JSON parsing errors

**Cause:** The demo uses `python3 -m json.tool` for formatting

**Solution:**
```bash
# Ensure Python 3 is installed
python3 --version

# If not available, install Python 3 or remove the json formatting:
# Edit run_investor_demo.sh and remove "| python3 -m json.tool" from responses
```

## 📝 What Each Endpoint Demonstrates

1. **Health Check** - System availability and monitoring
2. **List Buildings** - Portfolio management and compliance overview
3. **Get Evidence** - Evidence collection and verification system
4. **Evidence Details** - Metadata tracking and file integrity
5. **Get Defects** - Issue tracking and filtering capabilities
6. **Defect Details** - Comprehensive defect information
7. **Link Evidence** - Evidence-defect relationship management
8. **Update Defect** - Defect lifecycle and workflow automation

## 🎯 Success Criteria

After running the demo successfully, you should see:

✅ Health check returns status "ok"  
✅ 3 buildings listed with different compliance scores  
✅ Evidence items retrieved for Building B  
✅ Defects listed for Building C  
✅ Evidence successfully linked to defect  
✅ Defect status updated to "acknowledged"

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all environment variables are set correctly
3. Ensure the server is running on the correct port
4. Check server logs for detailed error messages

## 🔗 Additional Resources

- **API Documentation**: `https://your-url.com:5000/docs`
- **OpenAPI Spec**: `https://your-url.com:5000/openapi.json`
- **Health Status**: `https://your-url.com:5000/health`
- **Readiness Check**: `https://your-url.com:5000/health/ready`
