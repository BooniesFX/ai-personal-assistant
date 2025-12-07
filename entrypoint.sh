#!/bin/bash
set -e

echo "Starting Personal Assistant Bot..."

# Check for required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN is not set"
    exit 1
fi

# Check for Claude API key if using agent mode
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️ WARNING: ANTHROPIC_API_KEY is not set"
    echo "Will fall back to traditional command-based bot mode"
    AGENT_MODE=false
else
    echo "✅ Claude API key configured"
    AGENT_MODE=true
fi

# Check for ModelScope API key (required for image generation)
if [ -z "$MODELSCOPE_API_KEY" ]; then
    echo "⚠️ WARNING: MODELSCOPE_API_KEY is not set"
    echo "Image generation plugin will not work"
fi

# Check for admin ID
if [ -z "$ADMIN_ID" ]; then
    echo "⚠️ WARNING: ADMIN_ID is not set"
    echo "Permission system will have limited functionality"
fi

# Create data directory if it doesn't exist
mkdir -p /app/data

# Set up permissions for data directory
chmod 755 /app/data

echo ""
echo "=== Environment Summary ==="
echo "Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}... (hidden)"
if [ "$AGENT_MODE" = true ]; then
    echo "Claude API: ${ANTHROPIC_API_KEY:0:10}... (hidden)"
    echo "Agent Mode: ✅ ENABLED"
else
    echo "Claude API: ❌ NOT CONFIGURED"
    echo "Agent Mode: ❌ DISABLED (traditional commands only)"
fi
echo "ModelScope: ${MODELSCOPE_API_KEY:0:10}... (hidden)"
echo "Admin ID: $ADMIN_ID"
echo "==========================="
echo ""

# Choose which bot to run based on agent mode
if [ "$AGENT_MODE" = true ]; then
    echo "🚀 Starting Hybrid Claude Agent Bot..."
    echo "Features: Natural language + Traditional commands"
    exec uv run telegram_claude_agent.py
else
    echo "🚀 Starting Traditional Command Bot..."
    echo "Features: Traditional commands only"
    exec uv run telegram_bot.py
fi