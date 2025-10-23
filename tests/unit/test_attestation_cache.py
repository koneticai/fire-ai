"""
Unit tests for attestation cache.
"""

import pytest
import time
import threading
from unittest.mock import Mock

from src.app.services.attestation.cache import AttestationCache
from src.app.services.attestation.base import AttestationResult, AttestationResultStatus


class TestAttestationCache:
    """Test cases for AttestationCache."""
    
    @pytest.fixture
    def cache(self):
        """Create AttestationCache instance."""
        return AttestationCache(maxsize=100, ttl=1)  # 1 second TTL for testing
    
    @pytest.fixture
    def valid_result(self):
        """Create a valid attestation result."""
        return AttestationResult(
            status=AttestationResultStatus.VALID,
            device_id="test_device",
            platform="ios",
            validator_type="devicecheck"
        )
    
    @pytest.fixture
    def invalid_result(self):
        """Create an invalid attestation result."""
        return AttestationResult(
            status=AttestationResultStatus.INVALID,
            device_id="test_device",
            platform="android",
            validator_type="playintegrity",
            error_message="Test error"
        )
    
    def test_cache_initialization(self):
        """Test cache initialization with custom parameters."""
        cache = AttestationCache(maxsize=1000, ttl=3600)
        
        assert cache._cache.maxsize == 1000
        assert cache._cache.ttl == 3600
        assert cache._stats["hits"] == 0
        assert cache._stats["misses"] == 0
        assert cache._stats["sets"] == 0
        assert cache._stats["evictions"] == 0
    
    def test_cache_get_miss(self, cache, valid_result):
        """Test cache get with miss."""
        token_hash = "test_hash_123"
        
        result = cache.get(token_hash)
        
        assert result is None
        assert cache._stats["misses"] == 1
        assert cache._stats["hits"] == 0
    
    def test_cache_set_and_get(self, cache, valid_result):
        """Test cache set and get operations."""
        token_hash = "test_hash_123"
        
        # Set value
        cache.set(token_hash, valid_result)
        
        # Get value
        result = cache.get(token_hash)
        
        assert result is not None
        assert result.status == valid_result.status
        assert result.device_id == valid_result.device_id
        assert result.platform == valid_result.platform
        assert result.validator_type == valid_result.validator_type
        
        # Check stats
        assert cache._stats["sets"] == 1
        assert cache._stats["hits"] == 1
        assert cache._stats["misses"] == 0
    
    def test_cache_ttl_expiration(self, cache, valid_result):
        """Test cache TTL expiration."""
        token_hash = "test_hash_123"
        
        # Set value
        cache.set(token_hash, valid_result)
        
        # Verify value is cached
        result = cache.get(token_hash)
        assert result is not None
        
        # Wait for TTL expiration
        time.sleep(1.1)
        
        # Verify value is expired
        result = cache.get(token_hash)
        assert result is None
        assert cache._stats["misses"] == 1
    
    def test_cache_maxsize_eviction(self, cache, valid_result):
        """Test cache eviction when maxsize is reached."""
        # Fill cache to maxsize
        for i in range(100):
            cache.set(f"hash_{i}", valid_result)
        
        assert cache._stats["sets"] == 100
        
        # Add one more item to trigger eviction
        cache.set("hash_100", valid_result)
        
        assert cache._stats["sets"] == 101
        assert cache._stats["evictions"] == 1
    
    def test_cache_delete(self, cache, valid_result):
        """Test cache delete operation."""
        token_hash = "test_hash_123"
        
        # Set value
        cache.set(token_hash, valid_result)
        
        # Verify value is cached
        result = cache.get(token_hash)
        assert result is not None
        
        # Delete value
        deleted = cache.delete(token_hash)
        assert deleted is True
        
        # Verify value is deleted
        result = cache.get(token_hash)
        assert result is None
        
        # Try to delete non-existent value
        deleted = cache.delete("non_existent_hash")
        assert deleted is False
    
    def test_cache_clear(self, cache, valid_result):
        """Test cache clear operation."""
        # Add some values
        cache.set("hash_1", valid_result)
        cache.set("hash_2", valid_result)
        
        assert len(cache._cache) == 2
        
        # Clear cache
        cache.clear()
        
        assert len(cache._cache) == 0
        
        # Verify values are gone
        result1 = cache.get("hash_1")
        result2 = cache.get("hash_2")
        
        assert result1 is None
        assert result2 is None
    
    def test_cache_stats(self, cache, valid_result):
        """Test cache statistics."""
        # Initial stats
        stats = cache.get_stats()
        assert stats["size"] == 0
        assert stats["maxsize"] == 100
        assert stats["ttl"] == 1
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["sets"] == 0
        assert stats["evictions"] == 0
        assert stats["hit_rate_percent"] == 0.0
        
        # Add some operations
        cache.set("hash_1", valid_result)
        cache.get("hash_1")  # Hit
        cache.get("hash_2")  # Miss
        
        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["hit_rate_percent"] == 50.0
    
    def test_cache_reset_stats(self, cache, valid_result):
        """Test cache statistics reset."""
        # Add some operations
        cache.set("hash_1", valid_result)
        cache.get("hash_1")
        cache.get("hash_2")
        
        # Verify stats are not zero
        stats = cache.get_stats()
        assert stats["hits"] > 0
        assert stats["misses"] > 0
        assert stats["sets"] > 0
        
        # Reset stats
        cache.reset_stats()
        
        # Verify stats are reset
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["sets"] == 0
        assert stats["evictions"] == 0
    
    def test_cache_health_check(self, cache):
        """Test cache health check."""
        # Healthy cache
        assert cache.is_healthy() is True
        
        # Test with corrupted cache (simulate by breaking the lock)
        original_lock = cache._lock
        cache._lock = None
        
        try:
            assert cache.is_healthy() is False
        finally:
            cache._lock = original_lock
    
    def test_cache_memory_usage(self, cache, valid_result):
        """Test cache memory usage estimation."""
        # Empty cache
        memory = cache.get_memory_usage()
        assert memory["entries"] == 0
        assert memory["estimated_bytes"] == 0
        assert memory["estimated_mb"] == 0.0
        assert memory["max_entries"] == 100
        
        # Add some entries
        cache.set("hash_1", valid_result)
        cache.set("hash_2", valid_result)
        
        memory = cache.get_memory_usage()
        assert memory["entries"] == 2
        assert memory["estimated_bytes"] == 2048  # 2 * 1024
        assert memory["estimated_mb"] == 2.0
        assert memory["max_entries"] == 100
    
    def test_cache_thread_safety(self, cache, valid_result):
        """Test cache thread safety."""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    token_hash = f"worker_{worker_id}_hash_{i}"
                    cache.set(token_hash, valid_result)
                    result = cache.get(token_hash)
                    results.append(result is not None)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0
        
        # Verify all operations succeeded
        assert len(results) == 50  # 5 workers * 10 operations
        assert all(results)  # All should be True
    
    def test_cache_concurrent_access(self, cache, valid_result):
        """Test concurrent cache access."""
        def setter():
            for i in range(100):
                cache.set(f"concurrent_hash_{i}", valid_result)
        
        def getter():
            for i in range(100):
                cache.get(f"concurrent_hash_{i}")
        
        # Create threads for concurrent access
        setter_thread = threading.Thread(target=setter)
        getter_thread = threading.Thread(target=getter)
        
        # Start threads
        setter_thread.start()
        getter_thread.start()
        
        # Wait for completion
        setter_thread.join()
        getter_thread.join()
        
        # Verify cache is in consistent state
        assert cache.is_healthy() is True
        stats = cache.get_stats()
        assert stats["sets"] >= 0
        assert stats["hits"] >= 0
        assert stats["misses"] >= 0
    
    def test_cache_with_different_result_types(self, cache):
        """Test cache with different result types."""
        # Valid result
        valid_result = AttestationResult(
            status=AttestationResultStatus.VALID,
            device_id="device_1",
            platform="ios",
            validator_type="devicecheck"
        )
        
        # Invalid result
        invalid_result = AttestationResult(
            status=AttestationResultStatus.INVALID,
            device_id="device_2",
            platform="android",
            validator_type="playintegrity",
            error_message="Test error"
        )
        
        # Error result
        error_result = AttestationResult(
            status=AttestationResultStatus.ERROR,
            device_id="device_3",
            platform="ios",
            validator_type="appattest",
            error_message="Test error"
        )
        
        # Store all results
        cache.set("valid_hash", valid_result)
        cache.set("invalid_hash", invalid_result)
        cache.set("error_hash", error_result)
        
        # Retrieve and verify
        retrieved_valid = cache.get("valid_hash")
        retrieved_invalid = cache.get("invalid_hash")
        retrieved_error = cache.get("error_hash")
        
        assert retrieved_valid.status == AttestationResultStatus.VALID
        assert retrieved_invalid.status == AttestationResultStatus.INVALID
        assert retrieved_error.status == AttestationResultStatus.ERROR
        
        assert retrieved_valid.is_valid is True
        assert retrieved_invalid.is_invalid is True
        assert retrieved_error.is_error is True
    
    def test_cache_large_metadata(self, cache):
        """Test cache with large metadata."""
        large_metadata = {
            "large_field": "x" * 10000,  # 10KB string
            "nested": {
                "level1": {
                    "level2": {
                        "level3": "deep_value"
                    }
                }
            },
            "array": list(range(1000))
        }
        
        result = AttestationResult(
            status=AttestationResultStatus.VALID,
            device_id="test_device",
            platform="ios",
            validator_type="devicecheck",
            metadata=large_metadata
        )
        
        token_hash = "large_metadata_hash"
        
        # Set and get large result
        cache.set(token_hash, result)
        retrieved = cache.get(token_hash)
        
        assert retrieved is not None
        assert retrieved.metadata == large_metadata
        assert retrieved.metadata["large_field"] == "x" * 10000
        assert retrieved.metadata["nested"]["level1"]["level2"]["level3"] == "deep_value"
        assert len(retrieved.metadata["array"]) == 1000
