#!/bin/bash

# FireMode Supervisor Startup Script
# Ensures environment is properly configured before starting supervisor

echo "Starting FireMode Supervisor with environment setup..."

# Set development mode and source environment
export DEV_MODE=true
source setup_env.sh

# Check if environment was set up successfully
if [ -z "$JWT_SECRET_KEY" ]; then
    echo "ERROR: Environment setup failed - JWT_SECRET_KEY not set"
    exit 1
fi

echo "Environment verified. Starting supervisor..."

# Start the supervisor
python src/app/supervisor.py