"""
Device Attestation Service Package

This package provides device attestation validation for iOS and Android devices,
replacing the stub implementation with production-ready validators.

Supported platforms:
- iOS: DeviceCheck and App Attest (iOS 14+)
- Android: Play Integrity API and SafetyNet (legacy)

Features:
- Unified middleware with platform detection
- In-memory caching with TTL
- Rate limiting per device
- Feature flags for gradual rollout
- Comprehensive audit logging
"""

from .base import AttestationValidator, AttestationResult
from .cache import AttestationCache
from .config import AttestationConfig
from .middleware import AttestationMiddleware

# Platform-specific validators
from .ios_devicecheck import DeviceCheckValidator
from .ios_appattest import AppAttestValidator
from .android_playintegrity import PlayIntegrityValidator
from .android_safetynet import SafetyNetValidator

__all__ = [
    # Core interfaces
    "AttestationValidator",
    "AttestationResult", 
    "AttestationCache",
    "AttestationConfig",
    "AttestationMiddleware",
    
    # Platform validators
    "DeviceCheckValidator",
    "AppAttestValidator", 
    "PlayIntegrityValidator",
    "SafetyNetValidator",
]
