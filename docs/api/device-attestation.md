# Device Attestation API

## Overview

The FireMode Compliance Platform requires device attestation for evidence submission to ensure chain-of-custody integrity and prevent emulator-based evidence tampering.

## Current Implementation (Week 1 - MVP)

### Header Validation

All evidence submission requests must include the `X-Device-Attestation` header:

```
X-Device-Attestation: <device_token>
```

### Validation Rules

- **Required**: Header must be present
- **Rejected**: `emulator` value (prevents emulator uploads)
- **Accepted**: Any non-empty string (MVP stub)

### Error Response

```json
{
  "detail": "ATTESTATION_FAILED: Emulator not allowed"
}
```

**Status Code**: `422 Unprocessable Entity`

## Future Implementation (Week 4)

### Apple DeviceCheck Integration

The MVP stub will be replaced with real Apple DeviceCheck validation:

```python
async def validate_device_attestation(token: str) -> bool:
    """Real DeviceCheck validation - Week 4 implementation"""
    # Validate with Apple DeviceCheck API
    # Check device integrity and attestation
    # Return True if device is genuine and trusted
    pass
```

### Android SafetyNet Integration

For Android devices, SafetyNet attestation will be implemented:

```python
async def validate_android_attestation(token: str) -> bool:
    """Android SafetyNet validation - Week 4 implementation"""
    # Validate with Google SafetyNet API
    # Check device integrity and attestation
    # Return True if device is genuine and trusted
    pass
```

## Mobile Integration Guide

### iOS Implementation

```swift
// Generate device attestation token
let attestationToken = try await DeviceCheck.generateToken()
request.setValue(attestationToken, forHTTPHeaderField: "X-Device-Attestation")
```

### Android Implementation

```kotlin
// Generate SafetyNet attestation token
val attestationToken = SafetyNet.getAttestationToken()
request.setHeader("X-Device-Attestation", attestationToken)
```

## Security Considerations

1. **Chain of Custody**: Device attestation ensures evidence originates from genuine devices
2. **Tamper Prevention**: Prevents evidence manipulation through emulators
3. **Audit Trail**: All attestation failures are logged for compliance
4. **Rate Limiting**: Attestation failures trigger rate limiting to prevent abuse

## Testing

### Development Mode

For development and testing, use a non-emulator token:

```bash
curl -X POST /v1/evidence/submit \
  -H "X-Device-Attestation: dev-test-token" \
  -F "file=@evidence.jpg"
```

### Production Mode

In production, only genuine device attestation tokens will be accepted.

## Migration Timeline

- **Week 1**: MVP stub implementation (current)
- **Week 4**: Real DeviceCheck/SafetyNet integration
- **Week 6**: Enhanced attestation with additional device metrics
- **Week 8**: Biometric attestation for high-security evidence
