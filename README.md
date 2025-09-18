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

## 📄 API Documentation
Once the application is running, full interactive API documentation is available at [/docs](http://localhost:5000/docs).

## 🔐 Authentication

### Getting Access Tokens
The API uses JWT-based authentication. To access protected endpoints:

1. **Create a user account** (implementation specific)
2. **Obtain a JWT token** by authenticating with your credentials
3. **Use the token** in API requests

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