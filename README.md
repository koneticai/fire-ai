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
The API will be available at `http://localhost:8080`.

## 🧪 Running Tests
- **Unit/Integration Tests:** `poetry run pytest`
- **Load Tests:** `poetry run locust -f tests/load/locustfile.py`

## 📄 API Documentation
Once the application is running, full interactive API documentation is available at [/docs](http://localhost:8080/docs).