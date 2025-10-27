# FireMode Compliance Platform Backend

This is the backend service for the FireMode Compliance Platform, a hybrid Python/FastAPI and Go application designed for high-performance compliance data management.

## ✨ Features
- Hybrid Python/FastAPI + Go architecture
- PostgreSQL database with PII encryption
- JWT-based authentication
- CRDT support for conflict-free data merging
- High-performance endpoints for critical data ingestion

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python), Go
- **Database:** PostgreSQL
- **Dependency Management:** Poetry

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Go 1.24+
- Poetry

### 2. Setup
- Clone the repository.
- Install Python dependencies: `poetry install`
- Create a `.env` file by copying the `.env.example` file and populate it with your secrets. The `DATABASE_URL` can be found in the Replit "Secrets" tab after connecting the database.

### 3. Running the Application
Execute the run script:
```bash
bash run.sh
```
The API will be available at `http://localhost:5000`.

**Note**: The application uses a hybrid architecture with:
- **Python/FastAPI** service on port 5000 (main API)
- **Go service** sidecar on port 9090 (performance-critical endpoints)
- The Python service automatically proxies requests to the Go service as needed

## 🧪 Running Tests
- **Unit/Integration Tests:** `poetry run pytest`
- **Load Tests:** `poetry run locust -f tests/load/locustfile.py`

## 📊 Performance Testing (FM-ENH-005)

The platform includes comprehensive performance testing capabilities to validate 100k req/day scale (5x current target).

### Quick Start
```bash
# Run all performance tests
./services/api/tests/performance/run_all_tests.sh all

# Run specific test
./services/api/tests/performance/run_all_tests.sh peak

# Analyze results
python3 services/api/tests/performance/analyze_results.py ./services/api/tests/performance/results
```

### Test Scenarios

| Test | Description | Users | Duration | Target |
|------|-------------|-------|----------|---------|
| **Sustained** | Memory leaks, connection stability | 5 | 4h | 4,800 requests |
| **Peak** | p95 latency <300ms validation | 50 | 1h | 120,000 requests |
| **Spike** | Aurora auto-scaling validation | 200 | 5m | 10,000 requests |
| **CRDT Stress** | Zero data loss validation | 1000 | 10m | 1000+ conflicts |

### Environment Variables Required
```bash
export FASTAPI_BASE_URL="http://localhost:8080"
export GO_SERVICE_URL="http://localhost:9091"
export DATABASE_URL="postgresql://user:pass@host:port/db"
export INTERNAL_JWT_SECRET_KEY="your-secret-key"
```

### Acceptance Criteria
- ✅ P95 latency <300ms at 100k req/day
- ✅ Zero data loss in CRDT conflicts (1000+ concurrent)
- ✅ Aurora auto-scales automatically (2 ACU → 16 ACU)
- ✅ Go service memory <512MB under sustained load

### Performance Monitoring
The Go service includes built-in profiling endpoints:
- **Memory Stats:** `GET http://localhost:9091/memory`
- **pprof Profiling:** `http://localhost:6060/debug/pprof/`
- **Health Check:** `GET http://localhost:9091/health`

### Results and Reports
- **Locust Reports:** HTML reports generated in `results/` directory
- **Performance Analysis:** Automated analysis with charts and metrics
- **Profiling Data:** Go service memory and CPU profiles
- **Aurora Documentation:** Scaling expectations and migration guidance

For detailed performance analysis and Aurora migration planning, see `docs/performance/FM-ENH-005-report-template.md`.

## 📄 API Documentation
Once the application is running, full interactive API documentation is available at [/docs](http://localhost:5000/docs).

## 🔐 Authentication

The API uses JWT-based authentication with token revocation support. All protected endpoints require a valid JWT token.

### Generating Demo Tokens for Testing

For development and demo purposes, use the token generator script:

```bash
# Set your JWT secret (must match the server's JWT_SECRET_KEY)
export JWT_SECRET_KEY="your-secret-key-here"

# Generate a 24-hour demo token
cd services/api
python scripts/generate_demo_token.py

# Copy the token and use it in your requests
export JWT_TOKEN="<generated-token>"
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:5000/v1/buildings/
```

The demo token is associated with demo user ID `00000000-0000-0000-0000-000000000001` and is valid for 24 hours.

### Using Authentication in Swagger UI
1. Go to [/docs](http://localhost:5000/docs)
2. Click the "Authorize" button (🔒)
3. Enter your JWT token in the format: `Bearer <your-token-here>`
4. Click "Authorize" to apply to all requests

### Using Authentication in Code
```bash
# Example API request with authentication
curl -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     http://localhost:5000/v1/tests/sessions
```

**Required Headers:**
- `Authorization: Bearer <jwt-token>` - For all protected endpoints
- `Content-Type: application/json` - For POST/PUT requests

**Token Features:**
- JWT-based with HS256 algorithm
- Token Revocation List (RTL) support
- 24-hour expiration for demo tokens
- Unique JTI (JWT ID) for each token

---
## 🤖 Agents & Single Source of Truth
Project truth lives in **`./data_model.md`** (root).  
- **Single Source of Truth (SoT):** `./data_model.md` — reference it for any schema/service/UI change.  
- **Agent playbook:** `AGENTS.md` — tool-agnostic rules (small diffs, security gate, PR checklist).  
- **Droid config:** `.droid.yaml` — behavior for Factory Droid.  
- **Cursor rules:** `.cursor/rules/high-impact.mdc` — thin and defers to `AGENTS.md` + SoT.

### Mandatory workflow
1) Plan small changes (30–75 LOC) **referencing `./data_model.md`**.  
2) Prefer **additive** migrations; avoid destructive changes unless planned with backup/rollback.  
3) Run tests; summarize diffs and risks in the PR.

---
## 🔐 Security Setup (aligned with data_model.md)
- **JWT:** short-lived tokens; maintain a **revocation list (RTL)**.  
- **Fernet:** generate `FERNET_KEY` and store in `.env` (do not commit).  
- **Argon2:** use for password hashing.  
- **PostgreSQL:** target **16** (compatible with **14+**); ensure JSONB columns with **GIN** indexes per SoT.

**Example `.env` additions (placeholders):**

```bash
JWT_SECRET=changeme
JWT_EXPIRES_IN_SECONDS=900
FERNET_KEY=changeme_base64_32bytes
ARGON2_TIME_COST=3
ARGON2_MEMORY_COST=65536
ARGON2_PARALLELISM=2
```

---
## 🧭 PR Checklist (paste into PRs)
- [ ] Small, reviewable diff; tests added/updated  
- [ ] Change references `./data_model.md` (SoT)  
- [ ] Security Gate: validation, authZ, JWT/RTL, Fernet, Argon2  
- [ ] DB indexes/constraints match SoT (JSONB/GIN, FK/unique/temporal)  
- [ ] Rollback plan considered (if needed)