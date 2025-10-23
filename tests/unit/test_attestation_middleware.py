"""
Unit tests for attestation middleware.
"""

import pytest
from unittest.mock import Mock, patch
import threading
from datetime import datetime, timedelta

from src.app.services.attestation.middleware import AttestationMiddleware, RateLimiter
from src.app.services.attestation.config import AttestationConfig
from src.app.services.attestation.base import AttestationResult, AttestationResultStatus


class TestRateLimiter:
    """Test cases for RateLimiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create RateLimiter instance."""
        return RateLimiter(max_requests=5, window_seconds=60)
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_requests=10, window_seconds=3600)
        
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 3600
        assert len(limiter._requests) == 0
    
    def test_rate_limiter_within_limit(self, rate_limiter):
        """Test rate limiter within limit."""
        device_id = "test_device"
        
        # Should allow first 5 requests
        for i in range(5):
            assert rate_limiter.check(device_id) is True
    
    def test_rate_limiter_exceeds_limit(self, rate_limiter):
        """Test rate limiter exceeds limit."""
        device_id = "test_device"
        
        # Use up all requests
        for i in range(5):
            rate_limiter.check(device_id)
        
        # Next request should be rate limited
        assert rate_limiter.check(device_id) is False
    
    def test_rate_limiter_different_devices(self, rate_limiter):
        """Test rate limiter with different devices."""
        device1 = "device_1"
        device2 = "device_2"
        
        # Use up all requests for device1
        for i in range(5):
            rate_limiter.check(device1)
        
        # Device2 should still be able to make requests
        assert rate_limiter.check(device2) is True
    
    def test_rate_limiter_get_remaining_requests(self, rate_limiter):
        """Test getting remaining requests."""
        device_id = "test_device"
        
        # Initially should have 5 remaining
        assert rate_limiter.get_remaining_requests(device_id) == 5
        
        # Make 2 requests
        rate_limiter.check(device_id)
        rate_limiter.check(device_id)
        
        # Should have 3 remaining
        assert rate_limiter.get_remaining_requests(device_id) == 3
    
    def test_rate_limiter_reset(self, rate_limiter):
        """Test rate limiter reset."""
        device_id = "test_device"
        
        # Use up all requests
        for i in range(5):
            rate_limiter.check(device_id)
        
        # Should be rate limited
        assert rate_limiter.check(device_id) is False
        
        # Reset
        rate_limiter.reset(device_id)
        
        # Should be able to make requests again
        assert rate_limiter.check(device_id) is True
    
    def test_rate_limiter_thread_safety(self):
        """Test rate limiter thread safety."""
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        device_id = "test_device"
        results = []
        
        def worker():
            for i in range(20):
                result = limiter.check(device_id)
                results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have exactly 100 True results (max_requests)
        true_count = sum(results)
        assert true_count == 100


class TestAttestationMiddleware:
    """Test cases for AttestationMiddleware."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AttestationConfig(
            enabled=True,
            stub_mode=True,
            stub_allow_emulator=False,
            feature_flag_percentage=100,
            cache_size=100,
            cache_ttl=3600,
            rate_limit_per_device=10,
            rate_limit_window=3600
        )
    
    @pytest.fixture
    def middleware(self, config):
        """Create AttestationMiddleware instance."""
        return AttestationMiddleware(config)
    
    def test_middleware_initialization(self, config):
        """Test middleware initialization."""
        middleware = AttestationMiddleware(config)
        
        assert middleware.config == config
        assert middleware.cache is not None
        assert middleware.rate_limiter is not None
        assert len(middleware.validators) == 4
        assert "devicecheck" in middleware.validators
        assert "appattest" in middleware.validators
        assert "playintegrity" in middleware.validators
        assert "safetynet" in middleware.validators
    
    def test_validate_attestation_disabled(self, config):
        """Test validation when attestation is disabled."""
        config.enabled = False
        middleware = AttestationMiddleware(config)
        
        result = middleware.validate_attestation("test_token", {})
        
        assert result.status == AttestationResultStatus.ERROR
        assert "disabled" in result.error_message.lower()
    
    def test_validate_attestation_feature_flag_disabled(self, config):
        """Test validation when feature flag is disabled."""
        config.feature_flag_percentage = 0
        middleware = AttestationMiddleware(config)
        
        result = middleware.validate_attestation("test_token", {})
        
        assert result.status == AttestationResultStatus.ERROR
        assert "feature flag disabled" in result.error_message.lower()
    
    def test_validate_attestation_rate_limited(self, config):
        """Test validation when rate limited."""
        config.rate_limit_per_device = 1
        middleware = AttestationMiddleware(config)
        
        # First request should succeed
        result1 = middleware.validate_attestation("test_token", {})
        assert result1.status != AttestationResultStatus.ERROR or "rate limit" not in result1.error_message.lower()
        
        # Second request should be rate limited
        result2 = middleware.validate_attestation("test_token", {})
        assert result2.status == AttestationResultStatus.ERROR
        assert "rate limit" in result2.error_message.lower()
    
    def test_validate_attestation_platform_detection_ios(self, middleware):
        """Test platform detection for iOS."""
        headers = {"X-Platform": "ios"}
        
        result = middleware.validate_attestation("test_token", headers)
        
        # Should detect iOS platform
        assert result.platform == "ios"
        assert result.validator_type in ["devicecheck", "appattest"]
    
    def test_validate_attestation_platform_detection_android(self, middleware):
        """Test platform detection for Android."""
        headers = {"X-Platform": "android"}
        
        result = middleware.validate_attestation("test_token", headers)
        
        # Should detect Android platform
        assert result.platform == "android"
        assert result.validator_type in ["playintegrity", "safetynet"]
    
    def test_validate_attestation_platform_detection_jwt(self, middleware):
        """Test platform detection for JWT tokens."""
        # Mock JWT header
        with patch('jwt.get_unverified_header') as mock_header:
            mock_header.return_value = {"iss": "apple.com"}
            
            result = middleware.validate_attestation("eyJ.test.token", {})
            
            # Should detect iOS platform from JWT issuer
            assert result.platform == "ios"
            assert result.validator_type == "devicecheck"
    
    def test_validate_attestation_platform_detection_play_integrity(self, middleware):
        """Test platform detection for Play Integrity tokens."""
        # Long token with dots (Play Integrity format)
        play_integrity_token = "a" * 200 + "." + "b" * 200 + "." + "c" * 200
        
        result = middleware.validate_attestation(play_integrity_token, {})
        
        # Should detect Android platform
        assert result.platform == "android"
        assert result.validator_type == "playintegrity"
    
    def test_validate_attestation_platform_detection_emulator(self, middleware):
        """Test platform detection for emulator tokens."""
        headers = {"X-Platform": "ios"}
        
        result = middleware.validate_attestation("emulator", headers)
        
        # Should detect platform from headers
        assert result.platform == "ios"
        assert result.validator_type == "devicecheck"
    
    def test_validate_attestation_platform_detection_failed(self, middleware):
        """Test platform detection failure."""
        # Unknown token format
        result = middleware.validate_attestation("unknown_format", {})
        
        assert result.status == AttestationResultStatus.ERROR
        assert "could not detect" in result.error_message.lower()
    
    def test_validate_attestation_caching(self, middleware):
        """Test attestation result caching."""
        headers = {"X-Platform": "ios"}
        token = "test_token_123"
        
        # First request
        result1 = middleware.validate_attestation(token, headers)
        
        # Second request with same token
        result2 = middleware.validate_attestation(token, headers)
        
        # Should use cached result
        assert result1.status == result2.status
        assert result1.platform == result2.platform
        assert result1.validator_type == result2.validator_type
    
    def test_validate_attestation_device_id_generation(self, middleware):
        """Test device ID generation."""
        headers = {"User-Agent": "TestApp/1.0"}
        token = "test_token_123"
        
        result = middleware.validate_attestation(token, headers)
        
        # Should generate device ID
        assert result.device_id is not None
        assert len(result.device_id) == 16  # SHA-256 hash truncated to 16 chars
    
    def test_validate_attestation_with_provided_device_id(self, middleware):
        """Test validation with provided device ID."""
        headers = {"X-Platform": "ios"}
        device_id = "provided_device_id"
        
        result = middleware.validate_attestation("test_token", headers, device_id=device_id)
        
        # Should use provided device ID
        assert result.device_id == device_id
    
    def test_validate_attestation_with_metadata(self, middleware):
        """Test validation with metadata."""
        headers = {"X-Platform": "ios"}
        metadata = {"test_key": "test_value"}
        
        result = middleware.validate_attestation("test_token", headers, metadata=metadata)
        
        # Should include metadata in result
        assert result.metadata is not None
        assert result.metadata.get("test_key") == "test_value"
    
    def test_get_metrics(self, middleware):
        """Test metrics collection."""
        # Make some requests
        middleware.validate_attestation("token1", {"X-Platform": "ios"})
        middleware.validate_attestation("token2", {"X-Platform": "android"})
        
        metrics = middleware.get_metrics()
        
        assert "total_requests" in metrics
        assert "valid_attestations" in metrics
        assert "invalid_attestations" in metrics
        assert "errors" in metrics
        assert "cache_hits" in metrics
        assert "cache_misses" in metrics
        assert "rate_limited" in metrics
        assert "platform_breakdown" in metrics
        assert "validator_breakdown" in metrics
        assert "cache_stats" in metrics
        assert "success_rate" in metrics
        assert "cache_hit_rate" in metrics
        
        assert metrics["total_requests"] >= 2
    
    def test_reset_metrics(self, middleware):
        """Test metrics reset."""
        # Make some requests
        middleware.validate_attestation("token1", {"X-Platform": "ios"})
        
        # Get initial metrics
        initial_metrics = middleware.get_metrics()
        assert initial_metrics["total_requests"] > 0
        
        # Reset metrics
        middleware.reset_metrics()
        
        # Get metrics after reset
        reset_metrics = middleware.get_metrics()
        assert reset_metrics["total_requests"] == 0
        assert reset_metrics["valid_attestations"] == 0
        assert reset_metrics["invalid_attestations"] == 0
        assert reset_metrics["errors"] == 0
    
    def test_is_healthy(self, middleware):
        """Test health check."""
        # Should be healthy by default
        assert middleware.is_healthy() is True
    
    def test_get_validator_status(self, middleware):
        """Test validator status reporting."""
        status = middleware.get_validator_status()
        
        assert "devicecheck" in status
        assert "appattest" in status
        assert "playintegrity" in status
        assert "safetynet" in status
        
        # Check each validator has required fields
        for validator_name, validator_status in status.items():
            assert "validator_type" in validator_status
            assert "platform" in validator_status
            assert "stub_mode" in validator_status
            assert "configured" in validator_status
    
    def test_detect_platform_and_validator_ios_devicecheck(self, middleware):
        """Test platform detection for iOS DeviceCheck."""
        headers = {"X-Platform": "ios"}
        
        platform, validator_type = middleware._detect_platform_and_validator("test_token", headers)
        
        assert platform == "ios"
        assert validator_type == "devicecheck"
    
    def test_detect_platform_and_validator_ios_appattest(self, middleware):
        """Test platform detection for iOS App Attest."""
        headers = {"X-Platform": "ios", "X-App-Attest": "true"}
        
        platform, validator_type = middleware._detect_platform_and_validator("test_token", headers)
        
        assert platform == "ios"
        assert validator_type == "appattest"
    
    def test_detect_platform_and_validator_android_playintegrity(self, middleware):
        """Test platform detection for Android Play Integrity."""
        headers = {"X-Platform": "android", "X-Play-Integrity": "true"}
        
        platform, validator_type = middleware._detect_platform_and_validator("test_token", headers)
        
        assert platform == "android"
        assert validator_type == "playintegrity"
    
    def test_detect_platform_and_validator_android_safetynet(self, middleware):
        """Test platform detection for Android SafetyNet."""
        headers = {"X-Platform": "android"}
        
        platform, validator_type = middleware._detect_platform_and_validator("test_token", headers)
        
        assert platform == "android"
        assert validator_type == "safetynet"
    
    def test_generate_device_id(self, middleware):
        """Test device ID generation."""
        token = "test_token_123"
        headers = {"User-Agent": "TestApp/1.0"}
        
        device_id = middleware._generate_device_id(token, headers)
        
        assert device_id is not None
        assert len(device_id) == 16
        assert isinstance(device_id, str)
    
    def test_calculate_token_hash(self, middleware):
        """Test token hash calculation."""
        token = "test_token_123"
        hash1 = middleware._calculate_token_hash(token)
        hash2 = middleware._calculate_token_hash(token)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
        assert hash1 != token  # Should be hashed
    
    def test_check_feature_flag_100_percent(self, middleware):
        """Test feature flag check at 100%."""
        middleware.config.feature_flag_percentage = 100
        
        assert middleware._check_feature_flag() is True
    
    def test_check_feature_flag_0_percent(self, middleware):
        """Test feature flag check at 0%."""
        middleware.config.feature_flag_percentage = 0
        
        assert middleware._check_feature_flag() is False
    
    def test_check_feature_flag_50_percent(self, middleware):
        """Test feature flag check at 50%."""
        middleware.config.feature_flag_percentage = 50
        
        # Should be True or False randomly
        result = middleware._check_feature_flag()
        assert isinstance(result, bool)
    
    def test_create_disabled_result(self, middleware):
        """Test disabled result creation."""
        result = middleware._create_disabled_result("test_device", {"test": "value"})
        
        assert result.status == AttestationResultStatus.ERROR
        assert result.device_id == "test_device"
        assert "disabled" in result.error_message.lower()
        assert result.metadata == {"test": "value"}
    
    def test_create_feature_flag_result(self, middleware):
        """Test feature flag result creation."""
        result = middleware._create_feature_flag_result("test_device", {"test": "value"})
        
        assert result.status == AttestationResultStatus.ERROR
        assert result.device_id == "test_device"
        assert "feature flag disabled" in result.error_message.lower()
        assert result.metadata == {"test": "value"}
    
    def test_create_rate_limited_result(self, middleware):
        """Test rate limited result creation."""
        result = middleware._create_rate_limited_result("test_device", {"test": "value"})
        
        assert result.status == AttestationResultStatus.ERROR
        assert result.device_id == "test_device"
        assert "rate limit" in result.error_message.lower()
        assert result.metadata["rate_limited"] is True
        assert "remaining_requests" in result.metadata
    
    def test_create_platform_detection_error(self, middleware):
        """Test platform detection error result creation."""
        result = middleware._create_platform_detection_error("test_device", {"test": "value"})
        
        assert result.status == AttestationResultStatus.ERROR
        assert result.device_id == "test_device"
        assert "could not detect" in result.error_message.lower()
        assert result.metadata == {"test": "value"}
    
    def test_create_validator_not_found_error(self, middleware):
        """Test validator not found error result creation."""
        result = middleware._create_validator_not_found_error("unknown_validator", "test_device", {"test": "value"})
        
        assert result.status == AttestationResultStatus.ERROR
        assert result.device_id == "test_device"
        assert result.validator_type == "unknown_validator"
        assert "not found" in result.error_message.lower()
        assert result.metadata == {"test": "value"}
    
    def test_create_error_result(self, middleware):
        """Test general error result creation."""
        result = middleware._create_error_result("Test error", "test_device", {"test": "value"})
        
        assert result.status == AttestationResultStatus.ERROR
        assert result.device_id == "test_device"
        assert result.error_message == "Test error"
        assert result.metadata == {"test": "value"}
    
    def test_calculate_success_rate(self, middleware):
        """Test success rate calculation."""
        # Initially should be 0
        assert middleware._calculate_success_rate() == 0.0
        
        # Add some metrics
        middleware._metrics["valid_attestations"] = 8
        middleware._metrics["invalid_attestations"] = 2
        
        # Should be 80%
        assert middleware._calculate_success_rate() == 80.0
