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
# SQLite optimization: Use single process to avoid database locking issues
CONCURRENCY="${CELERY_WORKER_CONCURRENCY:-1}"
QUEUES="${CELERY_QUEUES:-rewards,default,activity,events,settlements,voting}"
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

# Start Celery worker with SQLite-optimized settings
exec celery -A lockup_backend worker \
    --loglevel="$LOG_LEVEL" \
    --concurrency="$CONCURRENCY" \
    --queues="$QUEUES" \
    --hostname="$WORKER_NAME@%h" \
    --logfile="$WORKER_LOG" \
    --pidfile="$PID_FILE" \
    --time-limit=1200 \
    --soft-time-limit=600 \
    --max-tasks-per-child=500 \
    --prefetch-multiplier=1 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --pool=solo