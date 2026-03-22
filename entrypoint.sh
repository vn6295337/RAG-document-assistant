#!/bin/bash
echo "Starting debug entrypoint..."
echo "Environment:"
env
echo "Checking python3..."
python3 --version
echo "Checking uvicorn..."
python3 -m uvicorn --version
echo "Starting app..."
exec python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080
