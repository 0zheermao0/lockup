#!/bin/bash
#
# Celery Beat Startup Script for Lockup Backend
#
# This script starts the Celery Beat scheduler for periodic tasks.
# Uses django-celery-beat for database-backed scheduling.
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
LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"
LOG_DIR="${PROJECT_DIR}/logs"
PID_DIR="${PROJECT_DIR}/run"

# Ensure directories exist
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Log file paths
BEAT_LOG="${LOG_DIR}/celery_beat.log"
PID_FILE="${PID_DIR}/celery_beat.pid"
SCHEDULE_FILE="${PID_DIR}/celerybeat-schedule"

echo "Starting Celery Beat for Lockup Backend..."
echo "Log Level: $LOG_LEVEL"
echo "Log File: $BEAT_LOG"
echo "PID File: $PID_FILE"
echo "Schedule File: $SCHEDULE_FILE"

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Start Celery Beat
exec celery -A celery_app beat \
    --loglevel="$LOG_LEVEL" \
    --scheduler=django_celery_beat.schedulers:DatabaseScheduler \
    --logfile="$BEAT_LOG" \
    --pidfile="$PID_FILE" \
    --schedule="$SCHEDULE_FILE"