#!/bin/bash
# FireMode Compliance Platform Environment Setup

echo "Setting up FireMode environment variables..."

# Check for required environment variables
MISSING_VARS=()

if [ -z "$JWT_SECRET_KEY" ]; then
    MISSING_VARS+=("JWT_SECRET_KEY")
fi

if [ -z "$INTERNAL_JWT_SECRET_KEY" ]; then
    MISSING_VARS+=("INTERNAL_JWT_SECRET_KEY")
fi

if [ -z "$DATABASE_URL" ]; then
    MISSING_VARS+=("DATABASE_URL")
fi

# If in development mode, generate secrets
if [ "${DEV_MODE:-false}" = "true" ] && [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "DEV_MODE enabled: Generating missing secrets..."
    
    if [ -z "$JWT_SECRET_KEY" ]; then
        export JWT_SECRET_KEY="$(openssl rand -hex 32)"
        echo "Generated JWT_SECRET_KEY for development"
    fi
    
    if [ -z "$INTERNAL_JWT_SECRET_KEY" ]; then
        export INTERNAL_JWT_SECRET_KEY="$(openssl rand -hex 32)"
        echo "Generated INTERNAL_JWT_SECRET_KEY for development"
    fi
    
    # DATABASE_URL still required even in dev mode
    if [ -z "$DATABASE_URL" ]; then
        echo "ERROR: DATABASE_URL is required even in development mode"
        exit 1
    fi
else
    # Production mode: require all secrets to be explicitly set
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        echo "ERROR: Missing required environment variables for production deployment:"
        printf " - %s\n" "${MISSING_VARS[@]}"
        echo ""
        echo "To generate secrets for development, set DEV_MODE=true"
        echo "For production, set these environment variables explicitly:"
        echo "  export JWT_SECRET_KEY=\"\$(openssl rand -hex 32)\""
        echo "  export INTERNAL_JWT_SECRET_KEY=\"\$(openssl rand -hex 32)\""
        exit 1
    fi
fi

echo "JWT_SECRET_KEY: Set (${#JWT_SECRET_KEY} characters)"
echo "INTERNAL_JWT_SECRET_KEY: Set (${#INTERNAL_JWT_SECRET_KEY} characters)"
echo "DATABASE_URL: Available"

echo "Environment setup complete."