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
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

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
    description="Production-grade compliance platform with hybrid Python/Go architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Configure OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Root endpoint
@app.get("/")
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
            "rules": "/v1/rules",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for the main application"""
    return {"status": "ok", "service": "firemode-backend"}

# Reverse proxy endpoints for Go service
@app.post("/v1/evidence")
async def proxy_evidence(request: Request):
    """Reverse proxy for evidence endpoint to Go service"""
    if not go_service_client:
        raise HTTPException(status_code=503, detail="Performance service unavailable")
    
    try:
        # Forward the request to Go service
        body = await request.body()
        headers = dict(request.headers)
        
        # Add user ID header (would normally come from JWT middleware)
        headers["X-User-ID"] = headers.get("x-user-id", "system")
        
        response = await go_service_client.post(
            "/v1/evidence",
            content=body,
            headers=headers,
            timeout=30.0
        )
        
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.RequestError as e:
        logger.error(f"Request to Go service failed: {e}")
        raise HTTPException(status_code=503, detail="Performance service error")

@app.post("/v1/tests/sessions/{session_id}/results")
async def proxy_test_results(session_id: str, request: Request):
    """Reverse proxy for test results endpoint to Go service"""
    if not go_service_client:
        raise HTTPException(status_code=503, detail="Performance service unavailable")
    
    try:
        # Forward the request to Go service
        body = await request.body()
        headers = dict(request.headers)
        
        # Add user ID header (would normally come from JWT middleware)
        headers["X-User-ID"] = headers.get("x-user-id", "system")
        
        response = await go_service_client.post(
            f"/v1/tests/sessions/{session_id}/results",
            content=body,
            headers=headers,
            timeout=30.0
        )
        
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.RequestError as e:
        logger.error(f"Request to Go service failed: {e}")
        raise HTTPException(status_code=503, detail="Performance service error")

# Import and include routers
from .routers import tests, rules

app.include_router(tests.router, prefix="/v1/tests", tags=["tests"])
app.include_router(rules.router, prefix="/v1/rules", tags=["rules"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)