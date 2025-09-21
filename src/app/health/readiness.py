"""
Production Readiness Checklist for FireMode Compliance Platform
"""

import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
import psycopg2
import os

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/ready")
async def readiness_check():
    """Comprehensive readiness check for production deployment"""
    checks = {
        "database": False,
        "go_service": False,
        "rtl_enabled": False,
        "migrations": False,
        "performance": False,
        "environment": False
    }
    
    details = {}
    
    # Check database connectivity and basic operations
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        with conn.cursor() as cursor:
            # Basic connectivity
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            checks["database"] = result[0] == 1
            
            # Check connection pool status
            connection_info = conn.get_dsn_parameters()
            details["database"] = {
                "connected": True,
                "host": connection_info.get("host", "unknown"),
                "dbname": connection_info.get("dbname", "unknown")
            }
        conn.close()
    except Exception as e:
        details["database"] = {"error": str(e)}
    
    # Check Go service health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:9091/health", timeout=2)
            checks["go_service"] = response.status_code == 200
            details["go_service"] = {
                "status": response.status_code,
                "available": checks["go_service"]
            }
    except Exception as e:
        details["go_service"] = {"error": str(e), "available": False}
    
    # Check RTL (Token Revocation List) is operational
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'token_revocation_list'
            """)
            table_exists = cursor.fetchone()[0] > 0
            
            if table_exists:
                cursor.execute("""
                    SELECT COUNT(*) FROM token_revocation_list 
                    WHERE expires_at > NOW()
                """)
                checks["rtl_enabled"] = True
                details["rtl"] = {"table_exists": True, "operational": True}
            else:
                details["rtl"] = {"table_exists": False, "operational": False}
        conn.close()
    except Exception as e:
        details["rtl"] = {"error": str(e)}
    
    # Check if migrations are current (simplified check)
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        with conn.cursor() as cursor:
            # Check if essential tables exist
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name IN ('test_sessions', 'as1851_rules', 'audits')
            """)
            tables_count = cursor.fetchone()[0]
            checks["migrations"] = tables_count >= 3
            details["migrations"] = {
                "essential_tables": tables_count,
                "expected": 3,
                "current": checks["migrations"]
            }
        conn.close()
    except Exception as e:
        details["migrations"] = {"error": str(e)}
    
    # Quick performance check
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        start = asyncio.get_event_loop().time()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        latency = asyncio.get_event_loop().time() - start
        checks["performance"] = latency < 0.01  # 10ms database response
        details["performance"] = {
            "db_latency_ms": round(latency * 1000, 2),
            "requirement_ms": 10,
            "meets_requirement": checks["performance"]
        }
        conn.close()
    except Exception as e:
        details["performance"] = {"error": str(e)}
    
    # Check environment configuration
    import os
    required_env_vars = [
        "DATABASE_URL", "JWT_SECRET_KEY", "INTERNAL_JWT_SECRET_KEY"
    ]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    checks["environment"] = len(missing_vars) == 0
    details["environment"] = {
        "required_vars": required_env_vars,
        "missing": missing_vars,
        "all_present": checks["environment"]
    }
    
    # Overall readiness
    all_ready = all(checks.values())
    
    return {
        "ready": all_ready,
        "status": "healthy" if all_ready else "degraded",
        "checks": checks,
        "details": details,
        "timestamp": asyncio.get_event_loop().time()
    }

@router.get("/live")
async def liveness_check():
    """Simple liveness check for Kubernetes/container orchestration"""
    return {
        "alive": True,
        "service": "firemode-api",
        "timestamp": asyncio.get_event_loop().time()
    }

@router.get("/metrics")
async def performance_metrics():
    """Get current performance metrics"""
    from ..metrics.performance import get_performance_stats
    return get_performance_stats()