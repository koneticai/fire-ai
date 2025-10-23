"""
Unified device attestation middleware.

Provides platform detection, routing to appropriate validators, rate limiting,
and comprehensive metrics collection for device attestation.
"""

import hashlib
import logging
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from .base import AttestationValidator, AttestationResult, AttestationResultStatus
from .config import AttestationConfig
from .cache import AttestationCache
from .ios_devicecheck import DeviceCheckValidator
from .ios_appattest import AppAttestValidator
from .android_playintegrity import PlayIntegrityValidator
from .android_safetynet import SafetyNetValidator

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Per-device rate limiter with sliding window.
    
    Tracks requests per device and enforces rate limits to prevent abuse.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = defaultdict(list)
        self._lock = threading.RLock()
    
    def check(self, device_id: str) -> bool:
        """
        Check if device is within rate limit.
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if within rate limit, False if rate limited
        """
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=self.window_seconds)
            
            # Clean old requests
            self._requests[device_id] = [
                ts for ts in self._requests[device_id] 
                if ts > cutoff
            ]
            
            # Check if within limit
            if len(self._requests[device_id]) >= self.max_requests:
                return False
            
            # Add current request
            self._requests[device_id].append(now)
            return True
    
    def get_remaining_requests(self, device_id: str) -> int:
        """
        Get remaining requests for device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Number of remaining requests
        """
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=self.window_seconds)
            
            # Clean old requests
            self._requests[device_id] = [
                ts for ts in self._requests[device_id] 
                if ts > cutoff
            ]
            
            return max(0, self.max_requests - len(self._requests[device_id]))
    
    def reset(self, device_id: str) -> None:
        """
        Reset rate limit for device.
        
        Args:
            device_id: Device identifier
        """
        with self._lock:
            if device_id in self._requests:
                del self._requests[device_id]


class AttestationMiddleware:
    """
    Unified device attestation middleware.
    
    Handles platform detection, routing to appropriate validators,
    rate limiting, caching, and metrics collection.
    """
    
    def __init__(self, config: AttestationConfig):
        """
        Initialize attestation middleware.
        
        Args:
            config: Attestation configuration
        """
        self.config = config
        self.cache = AttestationCache(
            maxsize=config.cache_size,
            ttl=config.cache_ttl
        )
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_per_device,
            window_seconds=config.rate_limit_window
        )
        
        # Initialize validators
        self.validators = {
            "devicecheck": DeviceCheckValidator(config),
            "appattest": AppAttestValidator(config),
            "playintegrity": PlayIntegrityValidator(config),
            "safetynet": SafetyNetValidator(config)
        }
        
        # Metrics tracking
        self._metrics = {
            "total_requests": 0,
            "valid_attestations": 0,
            "invalid_attestations": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "rate_limited": 0,
            "platform_breakdown": defaultdict(int),
            "validator_breakdown": defaultdict(int)
        }
        
        logger.info(f"Attestation middleware initialized - "
                   f"Cache: {config.cache_size} entries, {config.cache_ttl}s TTL, "
                   f"Rate limit: {config.rate_limit_per_device}/hour")
    
    def validate_attestation(self, token: str, headers: Dict[str, str], 
                           device_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> AttestationResult:
        """
        Validate device attestation with unified middleware.
        
        Args:
            token: Attestation token
            headers: HTTP headers (for platform detection)
            device_id: Optional device identifier
            metadata: Optional additional metadata
            
        Returns:
            AttestationResult with validation status
        """
        self._metrics["total_requests"] += 1
        
        try:
            # Check if attestation is enabled
            if not self.config.enabled:
                return self._create_disabled_result(device_id, metadata)
            
            # Check feature flag
            if not self._check_feature_flag():
                return self._create_feature_flag_result(device_id, metadata)
            
            # Generate device ID if not provided
            if not device_id:
                device_id = self._generate_device_id(token, headers)
            
            # Check rate limit
            if not self.rate_limiter.check(device_id):
                self._metrics["rate_limited"] += 1
                return self._create_rate_limited_result(device_id, metadata)
            
            # Check cache first
            token_hash = self._calculate_token_hash(token)
            cached_result = self.cache.get(token_hash)
            if cached_result:
                self._metrics["cache_hits"] += 1
                self._update_metrics(cached_result)
                return cached_result
            
            self._metrics["cache_misses"] += 1
            
            # Detect platform and select validator
            platform, validator_type = self._detect_platform_and_validator(token, headers)
            if not platform or not validator_type:
                return self._create_platform_detection_error(device_id, metadata)
            
            # Get validator
            validator = self.validators.get(validator_type)
            if not validator:
                return self._create_validator_not_found_error(validator_type, device_id, metadata)
            
            # Validate attestation
            result = validator.validate(token, device_id, metadata)
            
            # Update platform and validator info
            result.platform = platform
            result.validator_type = validator_type
            
            # Cache result if valid
            if result.is_valid:
                self.cache.set(token_hash, result)
            
            # Update metrics
            self._update_metrics(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Attestation middleware error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._metrics["errors"] += 1
            
            return self._create_error_result(error_msg, device_id, metadata)
    
    def _detect_platform_and_validator(self, token: str, headers: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
        """
        Detect platform and validator type from token and headers.
        
        Args:
            token: Attestation token
            headers: HTTP headers
            
        Returns:
            Tuple of (platform, validator_type) or (None, None) if detection fails
        """
        # Check X-Platform header first
        platform_header = headers.get('X-Platform', '').lower()
        if platform_header in ['ios', 'android']:
            return self._select_validator_for_platform(platform_header, token, headers)
        
        # Detect from token format
        if token.startswith('eyJ'):  # JWT format
            # Could be iOS DeviceCheck, App Attest, or SafetyNet
            return self._detect_jwt_platform(token, headers)
        elif '.' in token and len(token) > 100:
            # Likely Play Integrity token
            return 'android', 'playintegrity'
        elif token == 'emulator':
            # Emulator token - try to detect from headers
            return self._detect_emulator_platform(headers)
        
        logger.warning(f"Could not detect platform for token format: {token[:20]}...")
        return None, None
    
    def _select_validator_for_platform(self, platform: str, token: str, headers: Dict[str, str]) -> tuple[str, str]:
        """
        Select appropriate validator for detected platform.
        
        Args:
            platform: Detected platform ('ios' or 'android')
            token: Attestation token
            headers: HTTP headers
            
        Returns:
            Tuple of (platform, validator_type)
        """
        if platform == 'ios':
            # Check for App Attest vs DeviceCheck
            if headers.get('X-App-Attest') == 'true':
                return 'ios', 'appattest'
            else:
                return 'ios', 'devicecheck'
        elif platform == 'android':
            # Check for Play Integrity vs SafetyNet
            if headers.get('X-Play-Integrity') == 'true':
                return 'android', 'playintegrity'
            else:
                return 'android', 'safetynet'
        
        return platform, 'devicecheck'  # Default fallback
    
    def _detect_jwt_platform(self, token: str, headers: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
        """
        Detect platform for JWT tokens.
        
        Args:
            token: JWT token
            headers: HTTP headers
            
        Returns:
            Tuple of (platform, validator_type) or (None, None) if detection fails
        """
        try:
            # Decode JWT header without verification
            import jwt
            header = jwt.get_unverified_header(token)
            
            # Check issuer or other JWT claims
            issuer = header.get('iss', '').lower()
            if 'apple' in issuer or 'ios' in issuer:
                return 'ios', 'devicecheck'
            elif 'google' in issuer or 'android' in issuer:
                return 'android', 'safetynet'
            
            # Fallback to header-based detection
            if headers.get('X-Platform') == 'ios':
                return 'ios', 'devicecheck'
            elif headers.get('X-Platform') == 'android':
                return 'android', 'safetynet'
            
        except Exception as e:
            logger.warning(f"Failed to decode JWT header for platform detection: {str(e)}")
        
        return None, None
    
    def _detect_emulator_platform(self, headers: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
        """
        Detect platform for emulator tokens.
        
        Args:
            headers: HTTP headers
            
        Returns:
            Tuple of (platform, validator_type) or (None, None) if detection fails
        """
        platform = headers.get('X-Platform', '').lower()
        if platform == 'ios':
            return 'ios', 'devicecheck'
        elif platform == 'android':
            return 'android', 'playintegrity'
        
        # Default to iOS for emulator
        return 'ios', 'devicecheck'
    
    def _generate_device_id(self, token: str, headers: Dict[str, str]) -> str:
        """
        Generate device ID from token and headers.
        
        Args:
            token: Attestation token
            headers: HTTP headers
            
        Returns:
            Generated device ID
        """
        # Use User-Agent and other headers to generate device fingerprint
        user_agent = headers.get('User-Agent', '')
        device_info = f"{token[:20]}:{user_agent}"
        
        return hashlib.sha256(device_info.encode('utf-8')).hexdigest()[:16]
    
    def _calculate_token_hash(self, token: str) -> str:
        """Calculate SHA-256 hash of token for caching."""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    def _check_feature_flag(self) -> bool:
        """
        Check if attestation is enabled via feature flag.
        
        Returns:
            True if attestation should be enabled
        """
        if self.config.feature_flag_percentage >= 100:
            return True
        
        # Simple hash-based feature flag (not cryptographically secure)
        import random
        return random.randint(1, 100) <= self.config.feature_flag_percentage
    
    def _update_metrics(self, result: AttestationResult) -> None:
        """
        Update metrics based on validation result.
        
        Args:
            result: Attestation validation result
        """
        if result.is_valid:
            self._metrics["valid_attestations"] += 1
        elif result.is_invalid:
            self._metrics["invalid_attestations"] += 1
        elif result.is_error:
            self._metrics["errors"] += 1
        
        if result.platform:
            self._metrics["platform_breakdown"][result.platform] += 1
        
        if result.validator_type:
            self._metrics["validator_breakdown"][result.validator_type] += 1
    
    def _create_disabled_result(self, device_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> AttestationResult:
        """Create result for disabled attestation."""
        return AttestationResult(
            status=AttestationResultStatus.ERROR,
            device_id=device_id,
            platform=None,
            validator_type=None,
            error_message="Device attestation is disabled",
            metadata=metadata
        )
    
    def _create_feature_flag_result(self, device_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> AttestationResult:
        """Create result for feature flag disabled."""
        return AttestationResult(
            status=AttestationResultStatus.ERROR,
            device_id=device_id,
            platform=None,
            validator_type=None,
            error_message="Device attestation feature flag disabled",
            metadata=metadata
        )
    
    def _create_rate_limited_result(self, device_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> AttestationResult:
        """Create result for rate limited request."""
        remaining = self.rate_limiter.get_remaining_requests(device_id or "unknown")
        return AttestationResult(
            status=AttestationResultStatus.ERROR,
            device_id=device_id,
            platform=None,
            validator_type=None,
            error_message=f"Rate limit exceeded. Try again later. Remaining: {remaining}",
            metadata={**(metadata or {}), "rate_limited": True, "remaining_requests": remaining}
        )
    
    def _create_platform_detection_error(self, device_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> AttestationResult:
        """Create result for platform detection error."""
        return AttestationResult(
            status=AttestationResultStatus.ERROR,
            device_id=device_id,
            platform=None,
            validator_type=None,
            error_message="Could not detect device platform",
            metadata=metadata
        )
    
    def _create_validator_not_found_error(self, validator_type: str, device_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> AttestationResult:
        """Create result for validator not found error."""
        return AttestationResult(
            status=AttestationResultStatus.ERROR,
            device_id=device_id,
            platform=None,
            validator_type=validator_type,
            error_message=f"Validator not found: {validator_type}",
            metadata=metadata
        )
    
    def _create_error_result(self, error_message: str, device_id: Optional[str], metadata: Optional[Dict[str, Any]]) -> AttestationResult:
        """Create result for general error."""
        return AttestationResult(
            status=AttestationResultStatus.ERROR,
            device_id=device_id,
            platform=None,
            validator_type=None,
            error_message=error_message,
            metadata=metadata
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.
        
        Returns:
            Dictionary with current metrics
        """
        cache_stats = self.cache.get_stats()
        
        return {
            "total_requests": self._metrics["total_requests"],
            "valid_attestations": self._metrics["valid_attestations"],
            "invalid_attestations": self._metrics["invalid_attestations"],
            "errors": self._metrics["errors"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "rate_limited": self._metrics["rate_limited"],
            "platform_breakdown": dict(self._metrics["platform_breakdown"]),
            "validator_breakdown": dict(self._metrics["validator_breakdown"]),
            "cache_stats": cache_stats,
            "success_rate": self._calculate_success_rate(),
            "cache_hit_rate": cache_stats.get("hit_rate_percent", 0)
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        total = self._metrics["valid_attestations"] + self._metrics["invalid_attestations"]
        if total == 0:
            return 0.0
        return (self._metrics["valid_attestations"] / total) * 100
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics = {
            "total_requests": 0,
            "valid_attestations": 0,
            "invalid_attestations": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "rate_limited": 0,
            "platform_breakdown": defaultdict(int),
            "validator_breakdown": defaultdict(int)
        }
        self.cache.reset_stats()
        logger.info("Attestation metrics reset")
    
    def is_healthy(self) -> bool:
        """
        Check if middleware is healthy.
        
        Returns:
            True if middleware is operating normally
        """
        try:
            # Check cache health
            if not self.cache.is_healthy():
                return False
            
            # Check validators
            for validator in self.validators.values():
                if not validator.is_configured():
                    logger.warning(f"Validator {validator.get_validator_type()} not configured")
            
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    def get_validator_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all validators.
        
        Returns:
            Dictionary with validator status information
        """
        status = {}
        for name, validator in self.validators.items():
            status[name] = validator.get_configuration_status()
        return status
