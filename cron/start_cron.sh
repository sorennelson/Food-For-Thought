#!/bin/bash

# Wait for FastAPI to be ready
echo "Waiting for FastAPI..."

until curl -sf -H "Content-Type: application/json" \
        -H "IFTTT-Service-Key: $IFTTT_SERVICE_KEY" \
        http://fastapi:8000/ifttt/v1/status; do
  echo "FastAPI not ready yet..."
  sleep 2
done

echo "FastAPI is up, starting cron..."
# python scripts/test.py
cron -f
