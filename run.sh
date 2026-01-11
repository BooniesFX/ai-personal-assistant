#!/bin/bash

# Butler Agent Startup Script (SDK Mode)

# Load environment variables from .env if it exists
load_env() {
    if [ -f .env ]; then
        echo "Loading environment variables from .env..."
        set -a
        source .env
        set +a
    fi
}

case "$1" in
    ""|"sdk"|"agent")
        echo "Starting Butler Agent (SDK Mode)..."
        load_env
        uv run python run_sdk.py
        ;;
    "legacy")
        echo "Starting Legacy Agent (deprecated)..."
        load_env
        uv run python run_unified.py
        ;;
    "install")
        echo "Installing dependencies with uv..."
        uv sync
        ;;
    "help"|"-h"|"--help")
        echo "Butler Agent Startup Script"
        echo "Usage:"
        echo "  ./run.sh [sdk]    - Start Butler Agent (SDK Mode) [Default]"
        echo "  ./run.sh legacy   - Start Legacy Agent (deprecated)"
        echo "  ./run.sh install  - Install dependencies"
        echo "  ./run.sh help     - Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use './run.sh help' for usage"
        exit 1
        ;;
esac