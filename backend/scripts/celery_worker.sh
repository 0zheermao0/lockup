#!/bin/bash
#
# Celery Worker Startup Script for Lockup Backend
#
# This script starts a Celery worker process for handling asynchronous tasks.
# Designed for production deployment with proper logging and process management.
#
# Author: Claude Code
# Created: 2024-12-19
#

# Exit on any error
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
WORKER_NAME="${CELERY_WORKER_NAME:-lockup-worker}"
LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"
CONCURRENCY="${CELERY_WORKER_CONCURRENCY:-2}"
QUEUES="${CELERY_QUEUES:-rewards,default}"
LOG_DIR="${PROJECT_DIR}/logs"
PID_DIR="${PROJECT_DIR}/run"

# Ensure directories exist
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Log file paths
WORKER_LOG="${LOG_DIR}/celery_worker.log"
PID_FILE="${PID_DIR}/celery_worker.pid"

echo "Starting Celery Worker for Lockup Backend..."
echo "Worker Name: $WORKER_NAME"
echo "Log Level: $LOG_LEVEL"
echo "Concurrency: $CONCURRENCY"
echo "Queues: $QUEUES"
echo "Log File: $WORKER_LOG"
echo "PID File: $PID_FILE"

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Start Celery worker
exec celery -A celery_app worker \
    --loglevel="$LOG_LEVEL" \
    --concurrency="$CONCURRENCY" \
    --queues="$QUEUES" \
    --hostname="$WORKER_NAME@%h" \
    --logfile="$WORKER_LOG" \
    --pidfile="$PID_FILE" \
    --time-limit=600 \
    --soft-time-limit=300 \
    --max-tasks-per-child=1000 \
    --prefetch-multiplier=1 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat