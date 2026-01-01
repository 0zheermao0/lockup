#!/bin/bash
#
# Celery Flower Monitoring Script for Lockup Backend
#
# This script starts Flower web-based monitoring tool for Celery.
# Provides a web interface to monitor tasks, workers, and queues.
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
FLOWER_PORT="${FLOWER_PORT:-5555}"
FLOWER_ADDRESS="${FLOWER_ADDRESS:-127.0.0.1}"
LOG_DIR="${PROJECT_DIR}/logs"
PID_DIR="${PROJECT_DIR}/run"

# Ensure directories exist
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Log file paths
FLOWER_LOG="${LOG_DIR}/celery_flower.log"

echo "Starting Celery Flower for Lockup Backend..."
echo "Address: $FLOWER_ADDRESS"
echo "Port: $FLOWER_PORT"
echo "Log File: $FLOWER_LOG"
echo "Web Interface: http://$FLOWER_ADDRESS:$FLOWER_PORT"

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Start Flower
exec celery -A lockup_backend flower \
    --address="$FLOWER_ADDRESS" \
    --port="$FLOWER_PORT" \
    --logging=info \
    --logfile="$FLOWER_LOG"