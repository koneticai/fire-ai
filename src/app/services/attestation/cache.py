"""
In-memory caching for device attestation results.
"""

import threading
import time
from typing import Optional, Dict, Any
from cachetools import TTLCache
import logging

from .base import AttestationResult

logger = logging.getLogger(__name__)


class AttestationCache:
    """
    Thread-safe TTL cache for attestation results.
    
    Uses cachetools.TTLCache for efficient memory management and automatic expiration.
    """
    
    def __init__(self, maxsize: int = 10000, ttl: int = 3600):
        """
        Initialize attestation cache.
        
        Args:
            maxsize: Maximum number of cached items
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }
        
        logger.info(f"Attestation cache initialized - Max size: {maxsize}, TTL: {ttl}s")
    
    def get(self, token_hash: str) -> Optional[AttestationResult]:
        """
        Get cached attestation result.
        
        Args:
            token_hash: SHA-256 hash of the attestation token
            
        Returns:
            Cached AttestationResult or None if not found/expired
        """
        with self._lock:
            result = self._cache.get(token_hash)
            if result is not None:
                self._stats["hits"] += 1
                logger.debug(f"Cache hit for token hash: {token_hash[:8]}...")
                return result
            else:
                self._stats["misses"] += 1
                logger.debug(f"Cache miss for token hash: {token_hash[:8]}...")
                return None
    
    def set(self, token_hash: str, result: AttestationResult) -> None:
        """
        Cache attestation result.
        
        Args:
            token_hash: SHA-256 hash of the attestation token
            result: AttestationResult to cache
        """
        with self._lock:
            # Check if we're about to evict something
            if len(self._cache) >= self._cache.maxsize and token_hash not in self._cache:
                self._stats["evictions"] += 1
            
            self._cache[token_hash] = result
            self._stats["sets"] += 1
            
            logger.debug(f"Cached result for token hash: {token_hash[:8]}... "
                        f"(Status: {result.status.value})")
    
    def delete(self, token_hash: str) -> bool:
        """
        Remove cached result.
        
        Args:
            token_hash: SHA-256 hash of the attestation token
            
        Returns:
            True if item was removed, False if not found
        """
        with self._lock:
            if token_hash in self._cache:
                del self._cache[token_hash]
                logger.debug(f"Removed cached result for token hash: {token_hash[:8]}...")
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()
            logger.info("Attestation cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "maxsize": self._cache.maxsize,
                "ttl": self._cache.ttl,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "evictions": self._stats["evictions"],
                "hit_rate_percent": round(hit_rate, 2)
            }
    
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._stats = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "evictions": 0
            }
            logger.info("Cache statistics reset")
    
    def is_healthy(self) -> bool:
        """
        Check if cache is healthy.
        
        Returns:
            True if cache is operating normally
        """
        try:
            with self._lock:
                # Basic health check - can we access the cache?
                _ = len(self._cache)
                return True
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get estimated memory usage information.
        
        Returns:
            Dictionary with memory usage estimates
        """
        with self._lock:
            # Rough estimate: each cache entry is ~1KB
            estimated_bytes = len(self._cache) * 1024
            estimated_mb = estimated_bytes / (1024 * 1024)
            
            return {
                "entries": len(self._cache),
                "estimated_bytes": estimated_bytes,
                "estimated_mb": round(estimated_mb, 2),
                "max_entries": self._cache.maxsize
            }
