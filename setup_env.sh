#!/bin/bash
# FireMode Compliance Platform Environment Setup

echo "Setting up FireMode environment variables..."

# Generate secure random keys if not already set
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(openssl rand -hex 32)}"
export INTERNAL_JWT_SECRET_KEY="${INTERNAL_JWT_SECRET_KEY:-$(openssl rand -hex 32)}"

# Ensure DATABASE_URL is available (should be set by Replit)
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not set. This is required for the application to run."
    exit 1
fi

echo "JWT_SECRET_KEY: Set (${#JWT_SECRET_KEY} characters)"
echo "INTERNAL_JWT_SECRET_KEY: Set (${#INTERNAL_JWT_SECRET_KEY} characters)"
echo "DATABASE_URL: Available"

# Export to persistent env (if running in Replit)
if [ -n "$REPL_ID" ]; then
    echo "export JWT_SECRET_KEY=\"$JWT_SECRET_KEY\"" >> ~/.bashrc
    echo "export INTERNAL_JWT_SECRET_KEY=\"$INTERNAL_JWT_SECRET_KEY\"" >> ~/.bashrc
fi

echo "Environment setup complete."