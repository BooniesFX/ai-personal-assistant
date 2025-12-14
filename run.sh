#!/bin/bash

# Personal Assistant Bot Startup Script

# Load environment variables from .env if it exists
load_env() {
    if [ -f .env ]; then
        echo "Loading environment variables from .env..."
        while IFS='=' read -r key value; do
            key="${key##*( )}"
            key="${key%%*( )}"
            value="${value##*( )}"
            value="${value%%*( )}"
            if [[ ! $key =~ ^# ]] && [ -n "$key" ]; then
                export "$key=$value"
            fi
        done < .env
    fi
}

case "$1" in
    ""|"agent")
        echo "Starting Unified Agent (Web + Telegram)..."
        load_env
        uv run python run_unified.py
        ;;
    "bot"|"telegram")
        echo "Starting Telegram Bot only..."
        load_env
        uv run telegram_claude_agent.py
        ;;
    "web")
        echo "Starting Web Server only..."
        load_env
        uv run python run_web.py
        ;;
    "install")
        echo "Installing dependencies with uv..."
        uv sync
        ;;
    "help"|"-h"|"--help")
        echo "Personal Assistant Bot Startup Script"
        echo "Usage:"
        echo "  ./run.sh [agent] - Start Unified Agent (Web + TG) [Default]"
        echo "  ./run.sh bot     - Start Telegram Bot only"
        echo "  ./run.sh web     - Start Web Server only"
        echo "  ./run.sh install - Install dependencies"
        echo "  ./run.sh help    - Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use './run.sh help' for usage"
        exit 1
        ;;
esac