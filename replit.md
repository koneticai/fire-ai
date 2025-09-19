# FireMode Compliance Platform Backend

## Overview

FireMode is a compliance platform backend built for building fire safety testing and evidence management. The system is designed as a hybrid architecture running on Replit's Autoscale Deployments, combining Python/FastAPI for standard API operations with a Go service for performance-critical endpoints. The platform handles user authentication, building management, test sessions, AS1851 rule management, and evidence processing with PII encryption for sensitive data.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Hybrid Runtime Design
The application implements a dual-runtime architecture to meet performance requirements:
- **Python/FastAPI**: Main application entrypoint handling standard CRUD operations, authentication, and business logic
- **Go Service**: Compiled binary running as subprocess to handle performance-critical endpoints (`/v1/evidence` and `/v1/tests/sessions/{session_id}/results`) with p95 latency requirements under 300ms
- **Process Manager**: Robust process management with health monitoring, automatic restarts, and graceful shutdown handling

### API Architecture
- **RESTful Design**: Standard REST endpoints with consistent response patterns
- **Router-based Organization**: Modular endpoint organization using FastAPI routers for tests, rules, evidence, and test results
- **Secure Proxy Layer**: Python application proxies performance-critical requests to the Go service with internal JWT authentication
- **CRDT Support**: Conflict-free Replicated Data Types using automerge library for distributed session data

### Authentication & Security
- **JWT-based Authentication**: Bearer token authentication with configurable expiration
- **Token Revocation List (RTL)**: Database-backed token revocation system for enhanced JWT security
- **Internal JWT Authentication**: Secure inter-service communication between Python and Go services using dedicated JWT tokens
- **PII Encryption**: Fernet symmetric encryption for sensitive user data (full names) stored as BYTEA in database
- **Environment-based Configuration**: Security keys and database credentials managed through environment variables

### Data Architecture
- **PostgreSQL Database**: Relational data storage with encrypted PII fields
- **Schema-first Design**: Complete SQL schema with idempotent initialization scripts
- **Connection Pooling**: Direct psycopg2 connections with dependency injection pattern

### Performance & Monitoring
- **OpenTelemetry Integration**: Built-in observability and performance monitoring
- **Load Testing Ready**: Locust-based performance testing targeting critical endpoints
- **Idempotent Operations**: Request deduplication using idempotency keys

### Application Structure
```
src/app/              # Python FastAPI application
├── database/         # Schema and initialization
├── models/           # Pydantic data models
│   └── rtl.py        # Token Revocation List model
├── routers/          # API endpoint modules
│   ├── auth.py       # Authentication endpoints
│   ├── classify.py   # Fault classification (proxied to Go)
│   ├── evidence.py   # Evidence submission endpoints
│   ├── test_results.py # Test results endpoints
│   ├── tests.py      # Test session management
│   └── rules.py      # AS1851 rules management
├── dependencies.py   # Authentication and DB dependencies
├── internal_jwt.py   # Internal JWT token management
├── process_manager.py # Go service process management
├── proxy.py          # Go service communication layer
├── security.py       # PII encryption utilities
└── main.py           # Application entry point

src/go_service/       # Go performance service
└── main.go           # HTTP service for critical endpoints with JWT auth

tests/                # Test suite
├── test_rtl.py       # Token Revocation List tests
├── test_internal_jwt.py # JWT functionality tests
└── conftest.py       # Test configuration
```

## External Dependencies

### Database
- **Replit Managed PostgreSQL**: Primary data store provisioned via Replit's Databases tool
- **psycopg2-binary**: PostgreSQL driver for Python application connections

### Authentication & Security
- **python-jose[cryptography]**: JWT token handling and cryptographic operations
- **cryptography**: Fernet encryption for PII data protection

### Web Framework & HTTP
- **FastAPI**: Main web framework with automatic OpenAPI documentation
- **uvicorn**: ASGI server for FastAPI applications
- **httpx**: HTTP client for proxying requests to Go service

### Data Processing
- **pydantic**: Data validation and serialization with type hints
- **pandas**: Data analysis and manipulation for compliance reporting
- **automerge**: CRDT operations for distributed session state management

### Monitoring & Testing
- **opentelemetry-instrumentation-fastapi**: Performance monitoring and distributed tracing
- **locust**: Load testing framework for performance validation

### Go Service Dependencies
- **github.com/jackc/pgx/v5**: PostgreSQL driver for Go service
- **github.com/gorilla/mux**: HTTP routing for Go endpoints

### Development & Build
- **Poetry**: Python dependency management and virtual environment
- **Go toolchain**: Compilation of performance-critical service components