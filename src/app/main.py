"""
FireMode Compliance Platform Backend
Main FastAPI application with hybrid Python/Go architecture
"""

import os
import subprocess
import time
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Import dependencies needed for authentication
from .dependencies import get_current_active_user
from .models import TokenData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Go service process
go_service_process = None
go_service_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to start/stop Go service"""
    global go_service_process, go_service_client
    
    try:
        # Build and start Go service
        logger.info("Building Go service...")
        go_service_dir = Path(__file__).parent.parent / "go_service"
        
        # Build the Go service
        build_result = subprocess.run(
            ["go", "build", "-o", "firemode-go-service", "main.go"],
            cwd=go_service_dir,
            capture_output=True,
            text=True
        )
        
        if build_result.returncode != 0:
            logger.error(f"Go service build failed: {build_result.stderr}")
            raise Exception("Failed to build Go service")
        
        logger.info("Starting Go service...")
        # Start the Go service as a subprocess
        go_service_process = subprocess.Popen(
            ["./firemode-go-service"],
            cwd=go_service_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a moment for the service to start
        await asyncio.sleep(2)
        
        # Check if the process is still running
        if go_service_process.poll() is not None:
            stdout, stderr = go_service_process.communicate()
            logger.error(f"Go service failed to start. stdout: {stdout.decode()}, stderr: {stderr.decode()}")
            raise Exception("Go service failed to start")
        
        # Create HTTP client for Go service
        go_service_client = httpx.AsyncClient(base_url="http://localhost:9090")
        
        # Test connection to Go service
        try:
            response = await go_service_client.get("/health", timeout=5.0)
            if response.status_code == 200:
                logger.info("Go service started successfully")
            else:
                logger.warning(f"Go service health check returned {response.status_code}")
        except Exception as e:
            logger.warning(f"Go service health check failed: {e}")
        
        # Set Go service client for classification router
        from .routers import classify
        classify.set_go_service_client(go_service_client)
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Go service: {e}")
        # Continue without Go service for development
        yield
    
    finally:
        # Cleanup
        if go_service_client:
            await go_service_client.aclose()
        
        if go_service_process and go_service_process.poll() is None:
            logger.info("Shutting down Go service...")
            go_service_process.terminate()
            try:
                go_service_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                go_service_process.kill()

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

# Configure OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

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
    return {"status": "ok", "service": "firemode-backend"}

# Reverse proxy endpoints for Go service
@app.post("/v1/evidence", tags=["Evidence"], summary="Submit Evidence", description="High-performance evidence submission endpoint (proxied to Go service)")
async def proxy_evidence(request: Request, current_user: TokenData = Depends(get_current_active_user)):
    """Reverse proxy for evidence endpoint to Go service with authentication"""
    if not go_service_client:
        raise HTTPException(status_code=503, detail="Performance service unavailable")
    
    try:
        # Forward the request to Go service
        body = await request.body()
        headers = dict(request.headers)
        
        # Add authenticated user ID header for Go service
        # Remove any client-supplied x-user-id to prevent spoofing
        headers.pop("x-user-id", None)
        headers.pop("X-User-ID", None)
        headers["X-User-ID"] = str(current_user.user_id)
        
        response = await go_service_client.post(
            "/v1/evidence",
            content=body,
            headers=headers,
            timeout=30.0
        )
        
        # Filter response headers to only include safe headers
        safe_headers = {
            k: v for k, v in response.headers.items() 
            if k.lower() in ["content-type", "content-length", "cache-control"]
        }
        
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
            headers=safe_headers
        )
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.RequestError as e:
        logger.error(f"Request to Go service failed: {e}")
        raise HTTPException(status_code=503, detail="Performance service error")

@app.post("/v1/tests/sessions/{session_id}/results", tags=["Evidence"], summary="Submit Test Results", description="High-performance test results submission endpoint (proxied to Go service)")
async def proxy_test_results(session_id: str, request: Request, current_user: TokenData = Depends(get_current_active_user)):
    """Reverse proxy for test results endpoint to Go service with authentication"""
    if not go_service_client:
        raise HTTPException(status_code=503, detail="Performance service unavailable")
    
    try:
        # Forward the request to Go service
        body = await request.body()
        headers = dict(request.headers)
        
        # Add authenticated user ID header for Go service
        # Remove any client-supplied x-user-id to prevent spoofing
        headers.pop("x-user-id", None)
        headers.pop("X-User-ID", None)
        headers["X-User-ID"] = str(current_user.user_id)
        
        response = await go_service_client.post(
            f"/v1/tests/sessions/{session_id}/results",
            content=body,
            headers=headers,
            timeout=30.0
        )
        
        # Filter response headers to only include safe headers
        safe_headers = {
            k: v for k, v in response.headers.items() 
            if k.lower() in ["content-type", "content-length", "cache-control"]
        }
        
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
            headers=safe_headers
        )
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.RequestError as e:
        logger.error(f"Request to Go service failed: {e}")
        raise HTTPException(status_code=503, detail="Performance service error")

# Import and include routers
from .routers import tests, rules, auth, rules_versioned, classify, users

app.include_router(auth.router, prefix="/v1/auth")
app.include_router(tests.router, prefix="/v1/tests")
app.include_router(rules.router, prefix="/v1/rules")
app.include_router(rules_versioned.router, prefix="/v2/rules")
app.include_router(classify.router, prefix="/v1/classify")
app.include_router(users.router, prefix="/v1/users")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)