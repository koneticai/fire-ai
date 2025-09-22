"""
FireMode Compliance Platform Backend
Main FastAPI application with hybrid Python/Go architecture
"""

import os
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
# OpenTelemetry imports - simplified for available packages
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False

# Import dependencies needed for authentication
from .dependencies import get_current_active_user
from .schemas.auth import TokenPayload
from .internal_jwt import get_internal_jwt_token
from .process_manager import get_go_service_manager
from .utils.resilience import CircuitBreaker, retry_with_backoff, with_circuit_breaker
from .utils.errors import error_handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Go service client and circuit breaker
go_service_client = None
go_service_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

def setup_telemetry():
    """Configure basic telemetry instrumentation"""
    if TELEMETRY_AVAILABLE:
        try:
            # Basic FastAPI instrumentation
            FastAPIInstrumentor.instrument_app(app)
            logger.info("OpenTelemetry FastAPI instrumentation enabled")
        except Exception as e:
            logger.warning(f"Failed to setup telemetry: {e}")
    else:
        logger.info("OpenTelemetry not available - using basic monitoring")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to start/stop Go service"""
    global go_service_client
    
    # Get the process manager
    process_manager = get_go_service_manager()
    
    try:
        # Setup telemetry
        setup_telemetry()
        logger.info("OpenTelemetry instrumentation configured")
        
        # Start Go service using process manager
        logger.info("Starting Go service with process manager...")
        if await process_manager.start():
            logger.info("Go service started successfully")
            
            # Create HTTP client for Go service
            go_service_client = httpx.AsyncClient(base_url="http://localhost:9091")
            
            # Set Go service client for classification router
            from .routers import classify
            classify.set_go_service_client(go_service_client)
        else:
            logger.error("Failed to start Go service with process manager")
            # Continue without Go service for development
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Go service: {e}")
        # Continue without Go service for development
        yield
    
    finally:
        # Cleanup
        if go_service_client:
            await go_service_client.aclose()
        
        # Stop Go service using process manager
        logger.info("Shutting down Go service...")
        await process_manager.stop()

# Create FastAPI app
app = FastAPI(
    title="FireMode Compliance Platform",
    description="""
    ## FireMode Compliance Platform Backend API

    A high-performance, production-grade compliance platform built with hybrid Python/FastAPI and Go architecture for fire safety testing and evidence management.

    ### Key Features:
    - **Hybrid Architecture**: Python/FastAPI for standard operations + Go service for performance-critical endpoints
    - **AS1851 Compliance**: Full support for AS1851 fire safety rule management and fault classification
    - **Evidence Management**: Secure handling of compliance evidence with PII encryption
    - **CRDT Support**: Conflict-free replicated data types for distributed session data
    - **High Performance**: p95 latency < 300ms for critical endpoints
    - **JWT Authentication**: Secure token-based authentication with revocation list support

    ### Performance-Critical Endpoints:
    - `POST /v1/classify` - Fault classification (handled by Go service)
    - `POST /v1/evidence` - Evidence submission (handled by Go service)
    - `POST /v1/tests/sessions/{session_id}/results` - Test results submission (handled by Go service)

    ### Standard Endpoints:
    - Test session management (`/v1/tests/sessions`)  
    - AS1851 rule management (`/v1/rules`)
    - Fault classification and compliance checks

    Built for enterprise fire safety compliance with PostgreSQL database, OpenTelemetry monitoring, and comprehensive audit logging.
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "FireMode Compliance Platform",
        "url": "https://firemode.com"
    },
    license_info={
        "name": "Proprietary",
    },
    tags_metadata=[
        {
            "name": "Authentication",
            "description": "JWT-based authentication and user management",
        },
        {
            "name": "Test Sessions", 
            "description": "CRUD operations for fire safety test sessions with CRDT support",
        },
        {
            "name": "AS1851 Rules",
            "description": "Management of AS1851 compliance rules and fault classification",
        },
        {
            "name": "Evidence",
            "description": "High-performance evidence submission and management (Go service)",
        },
        {
            "name": "Health",
            "description": "System health checks and monitoring endpoints",
        }
    ]
)

# Configure basic telemetry
if TELEMETRY_AVAILABLE:
    try:
        FastAPIInstrumentor.instrument_app(app)
    except:
        pass  # Continue without telemetry

# Add concurrency middleware for vector clock detection
from .middleware.concurrency import detect_concurrent_writes
app.middleware("http")(detect_concurrent_writes)

# Add performance tracking middleware
from .metrics.performance import track_performance
app.middleware("http")(track_performance)

# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "FireMode Compliance Platform",
        "version": "1.0.0",
        "status": "running",
        "architecture": "hybrid_python_go",
        "endpoints": {
            "health": "/health",
            "evidence": "/v1/evidence",
            "test_results": "/v1/tests/sessions/{session_id}/results",
            "test_sessions": "/v1/tests/sessions",
            "classification": "/v1/classify",
            "rules": "/v1/rules",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for the main application"""
    process_manager = get_go_service_manager()
    go_service_status = process_manager.get_status()
    
    return {
        "status": "ok",
        "service": "firemode-backend", 
        "go_service": go_service_status
    }

# Go service status endpoint
@app.get("/health/go-service", tags=["Health"])
async def go_service_health():
    """Detailed health check for the Go service"""
    process_manager = get_go_service_manager()
    return process_manager.get_status()

# Reverse proxy endpoints for Go service
# REMOVED: Duplicate app-level routes - handled by respective routers with proper validation

# REMOVED: Duplicate app-level route - handled by test_sessions router

# Import and include routers
from .routers import rules, auth, rules_versioned, classify, users, evidence, test_results, rtl, buildings, test_sessions

# Add standardized error handling
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import uuid


async def global_404_handler(request: Request, exc: StarletteHTTPException):
    """Global 404 handler for FIRE error format compliance"""
    return JSONResponse(
        status_code=404,
        content={
            "transaction_id": str(uuid.uuid4()),
            "error_code": "FIRE-404",
            "message": "Not Found: Resource does not exist",
            "retryable": True
        }
    )

# Add exception handlers
app.add_exception_handler(HTTPException, error_handler)
app.add_exception_handler(404, global_404_handler)

# Include API routers
app.include_router(auth.router, prefix="/v1/auth")
app.include_router(rtl.router)  # RTL router has its own prefix (/v1/auth)
app.include_router(buildings.router)  # Buildings router has its own prefix (/v1/buildings)
app.include_router(test_sessions.router)  # Test sessions router has its own prefix (/v1/tests/sessions)
app.include_router(evidence.router)  # Evidence router has its own prefix
# app.include_router(test_results.router)  # REMOVED: Duplicate route conflict with test_sessions
app.include_router(rules.router, prefix="/v1/rules")
app.include_router(rules_versioned.router, prefix="/v2/rules")
app.include_router(classify.router, prefix="/v1/classify")
app.include_router(users.router, prefix="/v1/users")

# Add health endpoints
from .health import readiness
app.include_router(readiness.router, tags=["Health"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)