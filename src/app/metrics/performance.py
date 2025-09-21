"""
Performance monitoring and metrics for FireMode Compliance Platform
"""

import time
import uuid
import logging
from contextvars import ContextVar
from typing import Optional

logger = logging.getLogger(__name__)

# Context for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

# Simplified metrics without prometheus dependency
class MetricsCollector:
    """Simplified metrics collection for performance monitoring"""
    
    def __init__(self):
        self.request_durations = []
        self.crdt_conflicts = 0
        self.sync_latencies = []
        self.bundle_sizes = []
        self.active_connections = 0
    
    def observe_request_duration(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request duration"""
        self.request_durations.append({
            'method': method,
            'endpoint': endpoint,
            'status': status,
            'duration': duration,
            'timestamp': time.time()
        })
        logger.info(f"Request {method} {endpoint} [{status}] took {duration:.3f}s")
    
    def increment_crdt_conflicts(self, session_id: str):
        """Record CRDT merge conflict"""
        self.crdt_conflicts += 1
        logger.warning(f"CRDT conflict detected for session {session_id}")
    
    def observe_sync_latency(self, client_type: str, latency: float):
        """Record offline sync latency"""
        self.sync_latencies.append({
            'client_type': client_type,
            'latency': latency,
            'timestamp': time.time()
        })
    
    def observe_bundle_size(self, session_id: str, size_bytes: int):
        """Record offline bundle size"""
        self.bundle_sizes.append({
            'session_id': session_id,
            'size_bytes': size_bytes,
            'timestamp': time.time()
        })
        
        # Check 50MB limit
        if size_bytes > 50 * 1024 * 1024:
            logger.warning(f"Bundle size {size_bytes} bytes exceeds 50MB limit for session {session_id}")
    
    def increment_connections(self):
        """Increment active connections"""
        self.active_connections += 1
    
    def decrement_connections(self):
        """Decrement active connections"""
        self.active_connections = max(0, self.active_connections - 1)

# Global metrics collector
metrics = MetricsCollector()

async def track_performance(request, call_next):
    """Performance tracking middleware"""
    start = time.time()
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    # Track active connections
    metrics.increment_connections()
    
    try:
        response = await call_next(request)
        duration = time.time() - start
        
        # Record metrics
        metrics.observe_request_duration(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration
        )
        
        # Check p95 latency requirement for critical endpoints
        critical_endpoints = ["/v1/tests/sessions/results", "/v1/classify", "/v1/evidence"]
        if any(endpoint in request.url.path for endpoint in critical_endpoints) and duration > 0.3:
            logger.warning(f"Performance violation: {duration:.3f}s > 300ms requirement for {request.url.path}")
        
        return response
    except Exception as e:
        duration = time.time() - start
        logger.error(f"Request failed after {duration:.3f}s: {e}")
        raise
    finally:
        metrics.decrement_connections()

def get_performance_stats():
    """Get current performance statistics"""
    if not metrics.request_durations:
        return {"message": "No requests recorded yet"}
    
    durations = [r['duration'] for r in metrics.request_durations[-1000:]]  # Last 1000 requests
    durations.sort()
    
    return {
        "total_requests": len(metrics.request_durations),
        "active_connections": metrics.active_connections,
        "crdt_conflicts": metrics.crdt_conflicts,
        "avg_duration": sum(durations) / len(durations) if durations else 0,
        "p95_duration": durations[int(len(durations) * 0.95)] if durations else 0,
        "p99_duration": durations[int(len(durations) * 0.99)] if durations else 0,
        "recent_bundle_count": len(metrics.bundle_sizes)
    }