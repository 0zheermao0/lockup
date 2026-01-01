#!/bin/bash
#
# Multi-Queue Celery Workers Startup Script for Lockup Backend
#
# This script starts multiple Celery workers for different queues in production.
# Each queue gets its own dedicated worker with optimized concurrency settings.
#
# Author: Claude Code
# Created: 2024-12-19
#

# Exit on any error
set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Start multiple Celery workers for different queues"
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help     Show this help message"
    echo "  -d, --daemon   Run as daemons (background)"
    echo "  --stop         Stop all workers"
    echo "  --status       Show worker status"
    echo "  --restart      Restart all workers"
    echo ""
    echo "QUEUES AND CONCURRENCY:"
    echo "  rewards      - 1 worker  (high frequency rewards)"
    echo "  events       - 1 worker  (real-time events)"
    echo "  settlements  - 1 worker  (financial reliability)"
    echo "  voting       - 1 worker  (community operations)"
    echo "  activity     - 1 worker  (daily processing)"
    echo "  default      - 1 worker  (general tasks)"
    echo ""
}

# Configuration
DAEMON_MODE=false
LOG_DIR="${PROJECT_DIR}/logs"
PID_DIR="${PROJECT_DIR}/run"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -d|--daemon)
            DAEMON_MODE=true
            shift
            ;;
        --stop)
            echo "Stopping all Celery workers..."
            pkill -f "celery.*worker.*lockup_backend" || echo "No workers found to stop"
            exit 0
            ;;
        --status)
            echo "Checking Celery worker status..."
            pgrep -f "celery.*worker.*lockup_backend" | while read pid; do
                echo "Worker PID: $pid"
                ps -p $pid -o pid,ppid,cmd --no-headers
            done || echo "No workers running"
            exit 0
            ;;
        --restart)
            echo "Restarting all Celery workers..."
            $0 --stop
            sleep 3
            $0 -d
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo "Starting Multi-Queue Celery Workers for Lockup Backend..."
echo "Daemon mode: $DAEMON_MODE"
echo ""

# Create required directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Change to project directory
cd "$PROJECT_DIR"

# Check if Redis is running
echo "Checking Redis connection..."
if command -v redis-cli &> /dev/null; then
    if ! redis-cli ping &> /dev/null; then
        echo "Error: Redis server is not responding. Please start Redis first."
        exit 1
    else
        echo "Redis is running ✓"
    fi
fi

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Worker configurations: queue:concurrency:priority
WORKER_CONFIGS=(
    "rewards:1:high"
    "events:1:high"
    "settlements:1:critical"
    "voting:1:normal"
    "activity:1:low"
    "default:1:normal"
)

# Function to start a worker for a specific queue
start_worker() {
    local queue=$1
    local concurrency=$2
    local priority=$3

    local worker_name="lockup-${queue}-worker"
    local log_file="${LOG_DIR}/celery_worker_${queue}.log"
    local pid_file="${PID_DIR}/celery_worker_${queue}.pid"

    echo "Starting $queue worker (concurrency: $concurrency, priority: $priority)..."

    local cmd="celery -A lockup_backend worker \
        --loglevel=info \
        --concurrency=$concurrency \
        --queues=$queue \
        --hostname=${worker_name}@%h \
        --logfile=$log_file \
        --pidfile=$pid_file \
        --time-limit=600 \
        --soft-time-limit=300 \
        --max-tasks-per-child=1000 \
        --prefetch-multiplier=1 \
        --without-gossip \
        --without-mingle \
        --without-heartbeat"

    if [ "$DAEMON_MODE" = true ]; then
        nohup $cmd > "${LOG_DIR}/celery_worker_${queue}_startup.log" 2>&1 &
        local pid=$!
        echo "Started $queue worker as daemon (PID: $pid)"
    else
        $cmd &
        local pid=$!
        echo "Started $queue worker in background (PID: $pid)"
    fi

    # Brief delay to prevent startup conflicts
    sleep 1
}

# Start workers for each queue
for config in "${WORKER_CONFIGS[@]}"; do
    IFS=':' read -r queue concurrency priority <<< "$config"
    start_worker "$queue" "$concurrency" "$priority"
done

echo ""
echo "All workers started successfully!"
echo ""
echo "Monitor logs in: $LOG_DIR"
echo "PID files in: $PID_DIR"
echo ""
echo "Useful commands:"
echo "  $0 --status    # Check worker status"
echo "  $0 --stop      # Stop all workers"
echo "  $0 --restart   # Restart all workers"
echo ""

# If not daemon mode, wait for background jobs
if [ "$DAEMON_MODE" = false ]; then
    echo "Workers running in background. Press Ctrl+C to stop all."
    echo ""

    # Function to handle cleanup on exit
    cleanup() {
        echo ""
        echo "Stopping all workers..."
        pkill -f "celery.*worker.*lockup_backend" || true
        exit 0
    }

    # Set trap for cleanup
    trap cleanup SIGINT SIGTERM

    # Wait for background jobs
    wait
fi