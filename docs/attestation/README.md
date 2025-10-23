# Device Attestation Implementation

## Overview

This document describes the complete device attestation implementation for the FireMode Compliance Platform, replacing the stub implementation with production-ready iOS and Android validation.

## Architecture

The attestation system consists of:

- **Unified Middleware**: Platform detection, routing, rate limiting, and metrics
- **Platform Validators**: iOS (DeviceCheck, App Attest) and Android (Play Integrity, SafetyNet)
- **Caching Layer**: TTL-based in-memory caching for performance
- **Configuration**: Environment-based configuration with feature flags
- **Database Logging**: Audit trail and trust scoring

## Components

### 1. AttestationMiddleware

The central orchestrator that:
- Detects platform from tokens and headers
- Routes to appropriate validators
- Implements rate limiting (100 requests/hour per device)
- Provides caching with 1-hour TTL
- Collects comprehensive metrics

### 2. Platform Validators

#### iOS Validators
- **DeviceCheckValidator**: Validates DeviceCheck tokens via Apple API
- **AppAttestValidator**: Validates App Attest assertions (iOS 14+)

#### Android Validators
- **PlayIntegrityValidator**: Validates Play Integrity tokens via Google API
- **SafetyNetValidator**: Validates SafetyNet tokens (legacy support)

### 3. Caching System

- **AttestationCache**: Thread-safe TTL cache using cachetools
- 1-hour TTL for validated tokens
- Configurable cache size (default: 10,000 entries)
- Cache statistics and health monitoring

### 4. Configuration

Environment variables for configuration:

```bash
# Feature Flags
ATTESTATION_ENABLED=true
ATTESTATION_STUB_MODE=false
ATTESTATION_STUB_ALLOW_EMULATOR=false
ATTESTATION_FEATURE_FLAG_PERCENTAGE=100

# iOS DeviceCheck
APPLE_TEAM_ID=ABC123XYZ
APPLE_KEY_ID=KEY123456
APPLE_PRIVATE_KEY_PATH=/secrets/apple-private-key.p8

# iOS App Attest
APP_ATTEST_APP_ID=com.firemode.compliance

# Android Play Integrity
GOOGLE_CLOUD_PROJECT_ID=firemode-prod
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-credentials.json

# Android SafetyNet (Legacy)
SAFETYNET_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Cache Settings
ATTESTATION_CACHE_SIZE=10000
ATTESTATION_CACHE_TTL=3600

# Rate Limiting
ATTESTATION_RATE_LIMIT=100
ATTESTATION_RATE_LIMIT_WINDOW=3600
```

## Usage

### Basic Integration

The attestation is automatically integrated into the evidence submission endpoint:

```python
# In evidence router
def validate_device_attestation(headers: dict) -> bool:
    from ..services.attestation import AttestationMiddleware, AttestationConfig
    
    token = headers.get('X-Device-Attestation')
    if not token:
        raise HTTPException(status_code=422, detail="Missing attestation header")
    
    config = AttestationConfig()
    middleware = AttestationMiddleware(config)
    result = middleware.validate_attestation(token, headers)
    
    if not result.is_valid:
        raise HTTPException(status_code=422, detail=f"Attestation failed: {result.error_message}")
    
    return True
```

### Platform Detection

The middleware automatically detects platform from:

1. **X-Platform header**: Explicit platform specification
2. **Token format**: JWT vs Play Integrity format
3. **JWT issuer**: Apple vs Google issuer claims
4. **Additional headers**: X-App-Attest, X-Play-Integrity

### Stub Mode

For testing and development, stub mode is available:

```bash
ATTESTATION_STUB_MODE=true
ATTESTATION_STUB_ALLOW_EMULATOR=false  # Reject emulator tokens
```

In stub mode:
- All validators accept tokens (except emulator if configured)
- No external API calls are made
- Full validation logic is tested

## Database Schema

### attestation_logs Table

```sql
CREATE TABLE attestation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    validator_type VARCHAR(50) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    result VARCHAR(20) NOT NULL,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### device_trust_scores Table

```sql
CREATE TABLE device_trust_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(20) NOT NULL,
    trust_score INTEGER DEFAULT 100,
    total_validations INTEGER DEFAULT 0,
    failed_validations INTEGER DEFAULT 0,
    last_validation_at TIMESTAMP WITH TIME ZONE,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Testing

### Unit Tests

Comprehensive unit tests cover:
- All validators (iOS and Android)
- Caching layer with TTL and thread safety
- Middleware platform detection and routing
- Rate limiting and metrics collection
- Error handling and edge cases

Run tests:
```bash
python3 -m pytest tests/unit/test_attestation_*.py -v
```

### Integration Tests

End-to-end tests verify:
- Complete validation flows
- Platform detection accuracy
- Caching behavior
- Rate limiting enforcement
- Metrics collection
- Load testing (50 concurrent requests)

Run integration tests:
```bash
python3 -m pytest tests/integration/test_attestation_e2e.py -v
```

## Performance

### Targets

- **p95 latency**: <100ms (cached), <500ms (uncached)
- **Cache hit rate**: >80% after warmup
- **Memory usage**: <100MB for cache
- **Rate limiting**: 100 requests/hour per device
- **Load capacity**: 10,000 requests/hour

### Monitoring

The middleware provides comprehensive metrics:

```python
metrics = middleware.get_metrics()
# Returns:
{
    "total_requests": 1000,
    "valid_attestations": 950,
    "invalid_attestations": 30,
    "errors": 20,
    "cache_hits": 800,
    "cache_misses": 200,
    "rate_limited": 5,
    "platform_breakdown": {"ios": 600, "android": 400},
    "validator_breakdown": {"devicecheck": 500, "playintegrity": 300, ...},
    "cache_stats": {...},
    "success_rate": 95.0,
    "cache_hit_rate": 80.0
}
```

## Migration Guide

### From Stub to Production

1. **Deploy with stub mode enabled**:
   ```bash
   ATTESTATION_ENABLED=true
   ATTESTATION_STUB_MODE=true
   ```

2. **Configure credentials**:
   - Add Apple Team ID and Key ID
   - Upload Apple private key
   - Configure Google credentials

3. **Test with real tokens**:
   - Use test devices to generate tokens
   - Verify validation works
   - Check logs for errors

4. **Gradual rollout**:
   ```bash
   ATTESTATION_FEATURE_FLAG_PERCENTAGE=10  # 10% of traffic
   ```

5. **Full production**:
   ```bash
   ATTESTATION_STUB_MODE=false
   ATTESTATION_FEATURE_FLAG_PERCENTAGE=100
   ```

### Database Migration

Run the Alembic migration to create attestation tables:

```bash
alembic upgrade head
```

## Security Considerations

### Token Validation

- All tokens are validated against platform APIs
- JWT signatures are verified with platform public keys
- Token expiration is enforced
- Nonce validation prevents replay attacks

### Rate Limiting

- Per-device rate limiting prevents abuse
- Sliding window algorithm for accurate limiting
- Configurable limits and windows

### Caching

- Tokens are hashed before caching
- TTL prevents stale cache entries
- Thread-safe operations

### Audit Trail

- All validation attempts are logged
- Trust scores track device reputation
- Comprehensive error logging

## Troubleshooting

### Common Issues

1. **"Configuration incomplete" error**:
   - Check all required environment variables are set
   - Verify credential files exist and are readable

2. **"Platform detection failed" error**:
   - Ensure X-Platform header is set correctly
   - Check token format matches expected platform

3. **"Rate limit exceeded" error**:
   - Device has exceeded 100 requests/hour limit
   - Wait for rate limit window to reset

4. **"Cache miss" performance issues**:
   - Increase cache size if needed
   - Check TTL settings
   - Monitor cache hit rates

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('src.app.services.attestation').setLevel(logging.DEBUG)
```

### Health Checks

Check middleware health:

```python
middleware = AttestationMiddleware(config)
if not middleware.is_healthy():
    # Investigate configuration issues
    status = middleware.get_validator_status()
    print(status)
```

## Future Enhancements

### Planned Features

1. **Redis Caching**: Upgrade from in-memory to Redis for multi-instance deployments
2. **Advanced Metrics**: CloudWatch integration for production monitoring
3. **Device Fingerprinting**: Enhanced device identification
4. **Machine Learning**: Anomaly detection for suspicious devices
5. **Multi-Region**: Support for multiple geographic regions

### Performance Optimizations

1. **Connection Pooling**: Reuse HTTP connections to platform APIs
2. **Batch Validation**: Validate multiple tokens in single API call
3. **Predictive Caching**: Pre-cache tokens for known devices
4. **Async Processing**: Non-blocking validation for high throughput

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review logs in `attestation_logs` table
3. Monitor metrics for performance issues
4. Contact the development team

## References

- [Apple DeviceCheck Documentation](https://developer.apple.com/documentation/devicecheck)
- [Apple App Attest Documentation](https://developer.apple.com/documentation/devicecheck/validating_apps_that_connect_to_your_server)
- [Google Play Integrity API](https://developer.android.com/google/play/integrity)
- [Google SafetyNet API](https://developer.android.com/training/safetynet)
