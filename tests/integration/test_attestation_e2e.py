"""
End-to-end integration tests for device attestation.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.app.services.attestation import AttestationMiddleware, AttestationConfig
from src.app.services.attestation.base import AttestationResult, AttestationResultStatus


class TestAttestationE2E:
    """End-to-end tests for device attestation integration."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AttestationConfig(
            enabled=True,
            stub_mode=True,
            stub_allow_emulator=False,
            feature_flag_percentage=100,
            cache_size=1000,
            cache_ttl=3600,
            rate_limit_per_device=100,
            rate_limit_window=3600
        )
    
    @pytest.fixture
    def middleware(self, config):
        """Create AttestationMiddleware instance."""
        return AttestationMiddleware(config)
    
    def test_ios_devicecheck_validation_flow(self, middleware):
        """Test complete iOS DeviceCheck validation flow."""
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "valid_ios_token",
            "User-Agent": "FireModeApp/1.0 (iOS 15.0)"
        }
        
        result = middleware.validate_attestation("valid_ios_token", headers)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.platform == "ios"
        assert result.validator_type == "devicecheck"
        assert result.device_id is not None
        assert result.metadata["stub_mode"] is True
    
    def test_ios_appattest_validation_flow(self, middleware):
        """Test complete iOS App Attest validation flow."""
        headers = {
            "X-Platform": "ios",
            "X-App-Attest": "true",
            "X-Device-Attestation": "valid_appattest_token",
            "User-Agent": "FireModeApp/1.0 (iOS 16.0)"
        }
        
        result = middleware.validate_attestation("valid_appattest_token", headers)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.platform == "ios"
        assert result.validator_type == "appattest"
        assert result.device_id is not None
        assert result.metadata["stub_mode"] is True
    
    def test_android_playintegrity_validation_flow(self, middleware):
        """Test complete Android Play Integrity validation flow."""
        headers = {
            "X-Platform": "android",
            "X-Play-Integrity": "true",
            "X-Device-Attestation": "valid_playintegrity_token",
            "User-Agent": "FireModeApp/1.0 (Android 13)"
        }
        
        result = middleware.validate_attestation("valid_playintegrity_token", headers)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.platform == "android"
        assert result.validator_type == "playintegrity"
        assert result.device_id is not None
        assert result.metadata["stub_mode"] is True
    
    def test_android_safetynet_validation_flow(self, middleware):
        """Test complete Android SafetyNet validation flow."""
        headers = {
            "X-Platform": "android",
            "X-Device-Attestation": "valid_safetynet_token",
            "User-Agent": "FireModeApp/1.0 (Android 12)"
        }
        
        result = middleware.validate_attestation("valid_safetynet_token", headers)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.platform == "android"
        assert result.validator_type == "safetynet"
        assert result.device_id is not None
        assert result.metadata["stub_mode"] is True
    
    def test_emulator_rejection_flow(self, middleware):
        """Test emulator token rejection flow."""
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "emulator",
            "User-Agent": "FireModeApp/1.0 (iOS Simulator)"
        }
        
        result = middleware.validate_attestation("emulator", headers)
        
        assert result.status == AttestationResultStatus.INVALID
        assert "emulator" in result.error_message.lower()
        assert result.metadata["stub_mode"] is True
        assert result.metadata["reason"] == "emulator_rejected"
    
    def test_emulator_allowed_flow(self, config):
        """Test emulator token allowed flow when configured."""
        config.stub_allow_emulator = True
        middleware = AttestationMiddleware(config)
        
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "emulator",
            "User-Agent": "FireModeApp/1.0 (iOS Simulator)"
        }
        
        result = middleware.validate_attestation("emulator", headers)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["stub_mode"] is True
        assert result.metadata["reason"] == "stub_accepted"
    
    def test_caching_flow(self, middleware):
        """Test attestation result caching flow."""
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "cached_token",
            "User-Agent": "FireModeApp/1.0 (iOS 15.0)"
        }
        
        # First request
        result1 = middleware.validate_attestation("cached_token", headers)
        assert result1.status == AttestationResultStatus.VALID
        
        # Second request with same token
        result2 = middleware.validate_attestation("cached_token", headers)
        assert result2.status == AttestationResultStatus.VALID
        
        # Results should be identical (cached)
        assert result1.status == result2.status
        assert result1.platform == result2.platform
        assert result1.validator_type == result2.validator_type
        assert result1.device_id == result2.device_id
    
    def test_rate_limiting_flow(self, config):
        """Test rate limiting flow."""
        config.rate_limit_per_device = 2  # Very low limit for testing
        middleware = AttestationMiddleware(config)
        
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "rate_limit_token",
            "User-Agent": "FireModeApp/1.0 (iOS 15.0)"
        }
        
        # First two requests should succeed
        result1 = middleware.validate_attestation("rate_limit_token", headers)
        result2 = middleware.validate_attestation("rate_limit_token", headers)
        
        assert result1.status == AttestationResultStatus.VALID
        assert result2.status == AttestationResultStatus.VALID
        
        # Third request should be rate limited
        result3 = middleware.validate_attestation("rate_limit_token", headers)
        assert result3.status == AttestationResultStatus.ERROR
        assert "rate limit" in result3.error_message.lower()
        assert result3.metadata["rate_limited"] is True
    
    def test_platform_detection_flow(self, middleware):
        """Test automatic platform detection flow."""
        # Test JWT token detection
        jwt_token = "eyJ.test.token"
        headers = {"User-Agent": "FireModeApp/1.0"}
        
        with patch('src.app.services.attestation.middleware.jwt.get_unverified_header') as mock_header:
            mock_header.return_value = {"iss": "apple.com"}
            
            result = middleware.validate_attestation(jwt_token, headers)
            
            assert result.platform == "ios"
            assert result.validator_type == "devicecheck"
    
    def test_play_integrity_token_detection_flow(self, middleware):
        """Test Play Integrity token format detection."""
        # Long token with dots (Play Integrity format)
        play_integrity_token = "a" * 200 + "." + "b" * 200 + "." + "c" * 200
        headers = {"User-Agent": "FireModeApp/1.0 (Android 13)"}
        
        result = middleware.validate_attestation(play_integrity_token, headers)
        
        assert result.platform == "android"
        assert result.validator_type == "playintegrity"
    
    def test_metrics_collection_flow(self, middleware):
        """Test metrics collection flow."""
        # Make various requests
        middleware.validate_attestation("token1", {"X-Platform": "ios"})
        middleware.validate_attestation("token2", {"X-Platform": "android"})
        middleware.validate_attestation("emulator", {"X-Platform": "ios"})
        
        metrics = middleware.get_metrics()
        
        assert metrics["total_requests"] >= 3
        assert "platform_breakdown" in metrics
        assert "validator_breakdown" in metrics
        assert "cache_stats" in metrics
        assert "success_rate" in metrics
        assert "cache_hit_rate" in metrics
        
        # Should have both iOS and Android requests
        assert metrics["platform_breakdown"]["ios"] >= 1
        assert metrics["platform_breakdown"]["android"] >= 1
    
    def test_error_handling_flow(self, middleware):
        """Test error handling flow."""
        # Test with invalid token format
        result = middleware.validate_attestation("invalid_format", {})
        
        assert result.status == AttestationResultStatus.ERROR
        assert "could not detect" in result.error_message.lower()
    
    def test_feature_flag_flow(self, config):
        """Test feature flag flow."""
        config.feature_flag_percentage = 0  # Disable feature flag
        middleware = AttestationMiddleware(config)
        
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "test_token"
        }
        
        result = middleware.validate_attestation("test_token", headers)
        
        assert result.status == AttestationResultStatus.ERROR
        assert "feature flag disabled" in result.error_message.lower()
    
    def test_disabled_attestation_flow(self, config):
        """Test disabled attestation flow."""
        config.enabled = False
        middleware = AttestationMiddleware(config)
        
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "test_token"
        }
        
        result = middleware.validate_attestation("test_token", headers)
        
        assert result.status == AttestationResultStatus.ERROR
        assert "disabled" in result.error_message.lower()
    
    def test_health_check_flow(self, middleware):
        """Test health check flow."""
        assert middleware.is_healthy() is True
        
        # Test validator status
        status = middleware.get_validator_status()
        assert "devicecheck" in status
        assert "appattest" in status
        assert "playintegrity" in status
        assert "safetynet" in status
    
    def test_load_simulation_flow(self, middleware):
        """Test load simulation with multiple concurrent requests."""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    headers = {
                        "X-Platform": "ios",
                        "X-Device-Attestation": f"load_test_token_{worker_id}_{i}",
                        "User-Agent": f"FireModeApp/1.0 (iOS 15.0) Worker-{worker_id}"
                    }
                    
                    result = middleware.validate_attestation(f"load_test_token_{worker_id}_{i}", headers)
                    results.append(result)
                    
                    # Small delay to simulate real usage
                    time.sleep(0.01)
                    
            except Exception as e:
                errors.append(e)
        
        # Create multiple worker threads
        threads = []
        for i in range(5):  # 5 workers
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0
        
        # Verify all requests were processed
        assert len(results) == 50  # 5 workers * 10 requests each
        
        # Verify middleware is still healthy
        assert middleware.is_healthy() is True
        
        # Check metrics
        metrics = middleware.get_metrics()
        assert metrics["total_requests"] >= 50
    
    def test_metadata_preservation_flow(self, middleware):
        """Test metadata preservation through validation flow."""
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "metadata_test_token",
            "User-Agent": "FireModeApp/1.0 (iOS 15.0)"
        }
        
        metadata = {
            "test_key": "test_value",
            "nested": {"level1": {"level2": "deep_value"}},
            "array": [1, 2, 3, 4, 5]
        }
        
        result = middleware.validate_attestation("metadata_test_token", headers, metadata=metadata)
        
        assert result.status == AttestationResultStatus.VALID
        assert result.metadata["test_key"] == "test_value"
        assert result.metadata["nested"]["level1"]["level2"] == "deep_value"
        assert result.metadata["array"] == [1, 2, 3, 4, 5]
        assert result.metadata["stub_mode"] is True
    
    def test_device_id_consistency_flow(self, middleware):
        """Test device ID consistency across requests."""
        headers = {
            "X-Platform": "ios",
            "X-Device-Attestation": "consistency_test_token",
            "User-Agent": "FireModeApp/1.0 (iOS 15.0)"
        }
        
        # Multiple requests with same token and headers
        results = []
        for i in range(5):
            result = middleware.validate_attestation("consistency_test_token", headers)
            results.append(result)
        
        # All results should have the same device ID
        device_ids = [result.device_id for result in results]
        assert len(set(device_ids)) == 1  # All device IDs should be the same
        assert device_ids[0] is not None
        assert len(device_ids[0]) == 16  # SHA-256 hash truncated to 16 chars
