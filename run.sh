#!/bin/bash

# FireMode Compliance Platform - Production Entrypoint
# This script handles the hybrid Python/Go architecture startup

echo "Starting FireMode Compliance Platform..."

# Set environment variables for production
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Initialize the database if needed
echo "Initializing database..."
python src/app/database/init.py

if [ $? -ne 0 ]; then
    echo "Database initialization failed"
    exit 1
fi

echo "Database initialized successfully"

# Start the application
echo "Starting FastAPI application..."
python -m uvicorn src.app.main:app --host 0.0.0.0 --port 5000 --log-level info