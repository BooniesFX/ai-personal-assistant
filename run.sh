#!/bin/bash

# Personal Assistant Bot Startup Script

case "$1" in
    "bot"|"telegram"|"")
        echo "Starting Personal Assistant Bot..."
        # Load environment variables from .env if it exists
        if [ -f .env ]; then
            echo "Loading environment variables from .env..."
            export $(cat .env | grep -v '^#' | xargs)
        fi
        uv run telegram_bot.py
        ;;
    "install")
        echo "Installing dependencies with uv..."
        uv sync
        ;;
    "help"|"-h"|"--help")
        echo "Personal Assistant Bot Startup Script"
        echo "Usage:"
        echo "  ./run.sh [bot]   - Start Telegram Bot (Default)"
        echo "  ./run.sh install - Install dependencies"
        echo "  ./run.sh help    - Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use './run.sh help' for usage"
        exit 1
        ;;
esac