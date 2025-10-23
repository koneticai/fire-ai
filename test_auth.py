#!/usr/bin/env python3
"""Test authentication with detailed debugging"""

import os
import sys
import jwt
import asyncio
import json
from datetime import datetime

# Add path to src/app
sys.path.insert(0, 'src')

from app.dependencies import verify_token
from app.config import settings

def test_token_decode():
    """Test token decoding with the demo token"""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZW1vLXVzZXIiLCJ1c2VyX2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAxIiwianRpIjoiYjAwZmMzZDgtOTJmYi00MDEzLTk1ZTMtOWM3MjNlOTZjYjdmIiwiZXhwIjoxNzYwNzU4NjE0LCJpYXQiOjE3NjA2NzIyMTR9.mq2-fR0uUAgZWg2GPbMek4E80yqgfcsJya4Bh-WXyOk"
    
    print("=" * 60)
    print("TOKEN DECODE TEST")
    print("=" * 60)
    
    # 1. Decode without verification
    payload = jwt.decode(token, options={'verify_signature': False})
    print("\n1. Token payload (unverified):")
    print(json.dumps(payload, indent=2))
    
    # 2. Check expiration
    exp_timestamp = payload.get('exp')
    exp_datetime = datetime.fromtimestamp(exp_timestamp)
    now = datetime.utcnow()
    print(f"\n2. Expiration check:")
    print(f"   Token expires: {exp_datetime}")
    print(f"   Current time:  {now}")
    print(f"   Is expired: {now > exp_datetime}")
    
    # 3. Check JWT_SECRET_KEY
    print(f"\n3. JWT_SECRET_KEY check:")
    print(f"   From environment: {bool(os.getenv('JWT_SECRET_KEY'))}")
    print(f"   From settings: {bool(settings.jwt_secret_key)}")
    print(f"   Algorithm: {settings.algorithm}")
    
    # 4. Try verification with settings
    print(f"\n4. Verification with settings:")
    try:
        verified = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.algorithm])
        print("   SUCCESS - Token verified with settings.jwt_secret_key")
    except Exception as e:
        print(f"   FAILED - {e}")
    
    # 5. Try verify_token function
    print(f"\n5. Using verify_token function:")
    try:
        token_data = verify_token(token)
        print(f"   SUCCESS - Token data returned:")
        print(f"   - username: {token_data.username}")
        print(f"   - user_id: {token_data.user_id}")
        print(f"   - jti: {token_data.jti}")
    except Exception as e:
        print(f"   FAILED - {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_token_decode()