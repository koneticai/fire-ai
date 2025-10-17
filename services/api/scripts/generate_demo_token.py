#!/usr/bin/env python3
"""
Demo JWT Token Generator for FIRE-AI Backend
Generates a valid JWT token for investor demos and testing
"""

import os
import sys
from datetime import datetime, timedelta
from jose import jwt
import uuid

def generate_demo_token():
    """Generate a demo JWT token with all required claims"""
    
    # Get JWT secret from environment
    jwt_secret = os.getenv('JWT_SECRET_KEY')
    if not jwt_secret:
        print("ERROR: JWT_SECRET_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Generate token with required claims
    now = datetime.utcnow()
    exp = now + timedelta(hours=24)
    
    # Demo user ID and JWT ID (valid UUID formats)
    demo_user_id = "00000000-0000-0000-0000-000000000001"
    demo_jti = str(uuid.uuid4())  # Generate a real UUID for JTI
    
    payload = {
        "sub": "demo-user",                    # Subject (username)
        "user_id": demo_user_id,               # User ID (required by backend)
        "jti": demo_jti,                       # JWT ID (for revocation tracking)
        "exp": int(exp.timestamp()),           # Expiration (24 hours)
        "iat": int(now.timestamp()),           # Issued at
    }
    
    # Create JWT token
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    
    # Print token info
    print("=" * 80)
    print("🔑 FIRE-AI DEMO JWT TOKEN GENERATED")
    print("=" * 80)
    print()
    print("Token Details:")
    print(f"  User:       {payload['sub']}")
    print(f"  User ID:    {payload['user_id']}")
    print(f"  JWT ID:     {payload['jti']}")
    print(f"  Issued:     {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Expires:    {exp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Valid for:  24 hours")
    print()
    print("=" * 80)
    print("JWT TOKEN (copy this):")
    print("=" * 80)
    print(token)
    print("=" * 80)
    print()
    print("Usage:")
    print('  export JWT_TOKEN="' + token + '"')
    print('  curl -H "Authorization: Bearer $JWT_TOKEN" <endpoint>')
    print()
    
    return token

if __name__ == "__main__":
    generate_demo_token()
