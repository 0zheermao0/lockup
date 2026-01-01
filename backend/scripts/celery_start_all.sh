#!/bin/bash
#
# Comprehensive Celery Startup Script for Lockup Backend
#
# This script starts all Celery components (worker, beat, flower) for development
# or production deployment. It can run components individually or all together.
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
    echo "Usage: $0 [OPTIONS] [COMPONENTS]"
    echo ""
    echo "Start Celery components for Lockup Backend"
    echo ""
    echo "COMPONENTS:"
    echo "  worker    Start Celery worker"
    echo "  beat      Start Celery beat scheduler"
    echo "  flower    Start Flower monitoring"
    echo "  all       Start all components (default)"
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help     Show this help message"
    echo "  -d, --daemon   Run as daemon (background)"
    echo "  --dev          Development mode (more verbose logging)"
    echo "  --prod         Production mode (optimized settings)"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                    # Start all components in foreground"
    echo "  $0 worker             # Start only worker (all queues: rewards,default,activity,events)"
    echo "  $0 -d all             # Start all as daemons"
    echo "  $0 --dev worker beat  # Start worker and beat in dev mode"
    echo ""
}

# Default settings
DAEMON_MODE=false
DEV_MODE=false
COMPONENTS=()

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
        --dev)
            DEV_MODE=true
            export CELERY_LOG_LEVEL="debug"
            shift
            ;;
        --prod)
            DEV_MODE=false
            export CELERY_LOG_LEVEL="info"
            shift
            ;;
        worker|beat|flower|all)
            COMPONENTS+=("$1")
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Default to all components if none specified
if [ ${#COMPONENTS[@]} -eq 0 ]; then
    COMPONENTS=("all")
fi

# Expand 'all' to individual components
if [[ " ${COMPONENTS[@]} " =~ " all " ]]; then
    COMPONENTS=("worker" "beat" "flower")
fi

echo "Starting Celery components for Lockup Backend..."
echo "Components: ${COMPONENTS[*]}"
echo "Daemon mode: $DAEMON_MODE"
echo "Development mode: $DEV_MODE"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Check if Redis is running
echo "Checking Redis connection..."
if command -v redis-cli &> /dev/null; then
    if ! redis-cli ping &> /dev/null; then
        echo "Warning: Redis server is not responding. Please start Redis first:"
        echo "  brew services start redis  # macOS with Homebrew"
        echo "  sudo systemctl start redis  # Linux with systemd"
        echo "  docker run -d -p 6379:6379 redis:alpine  # Docker"
        echo ""
    else
        echo "Redis is running ✓"
    fi
else
    echo "Warning: redis-cli not found. Please ensure Redis is installed and running."
fi

# Function to start component
start_component() {
    local component=$1
    local script_path="${SCRIPT_DIR}/celery_${component}.sh"

    if [ ! -f "$script_path" ]; then
        echo "Error: Script not found: $script_path"
        return 1
    fi

    echo "Starting Celery $component..."

    if [ "$DAEMON_MODE" = true ]; then
        nohup "$script_path" > "${PROJECT_DIR}/logs/celery_${component}_startup.log" 2>&1 &
        local pid=$!
        echo "Started Celery $component as daemon (PID: $pid)"
    else
        if [ ${#COMPONENTS[@]} -eq 1 ]; then
            # Single component - run in foreground
            exec "$script_path"
        else
            # Multiple components - run in background
            "$script_path" &
            local pid=$!
            echo "Started Celery $component in background (PID: $pid)"
        fi
    fi
}

# Create required directories
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${PROJECT_DIR}/run"

# Start components
for component in "${COMPONENTS[@]}"; do
    start_component "$component"
    sleep 2  # Brief delay between starts
done

# If running multiple components in foreground, wait for them
if [ "$DAEMON_MODE" = false ] && [ ${#COMPONENTS[@]} -gt 1 ]; then
    echo ""
    echo "All components started. Press Ctrl+C to stop all."
    echo "Monitoring logs in ${PROJECT_DIR}/logs/"
    echo ""

    # Wait for background jobs
    wait
fi