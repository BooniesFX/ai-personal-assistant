#!/bin/bash
set -e

echo "Starting Personal Assistant Bot..."

# Check for required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN is not set"
    exit 1
fi

# Check for LLM API key (supports multiple providers)
if [ -z "$LLM_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️ WARNING: LLM_API_KEY or ANTHROPIC_API_KEY is not set"
    echo "Will fall back to traditional command-based bot mode"
    AGENT_MODE=false
else
    if [ -n "$LLM_API_KEY" ]; then
        echo "✅ LLM API key configured (Provider: ${LLM_PROVIDER:-cas})"
    else
        echo "✅ Anthropic API key configured"
    fi
    AGENT_MODE=true
fi

# Check for Image API key (required for image generation)
if [ -z "$IMAGE_API_KEY" ] && [ -z "$MODELSCOPE_API_KEY" ]; then
    echo "⚠️ WARNING: IMAGE_API_KEY is not set"
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
    if [ -n "$LLM_API_KEY" ]; then
        echo "LLM API: ${LLM_API_KEY:0:10}... (hidden)"
        echo "LLM Provider: ${LLM_PROVIDER:-cas}"
        echo "LLM Model: ${LLM_MODEL:-deepseek-ai/DeepSeek-V3.2}"
    else
        echo "Claude API: ${ANTHROPIC_API_KEY:0:10}... (hidden)"
    fi
    echo "Agent Mode: ✅ ENABLED"
else
    echo "LLM API: ❌ NOT CONFIGURED"
    echo "Agent Mode: ❌ DISABLED (traditional commands only)"
fi
if [ -n "$IMAGE_API_KEY" ]; then
    echo "Image API: ${IMAGE_API_KEY:0:10}... (hidden)"
    echo "Image Provider: ${IMAGE_PROVIDER:-modelscope}"
elif [ -n "$MODELSCOPE_API_KEY" ]; then
    echo "Image API: ${MODELSCOPE_API_KEY:0:10}... (hidden)"
else
    echo "Image API: ❌ NOT CONFIGURED"
fi
echo "Admin ID: ${ADMIN_ID:-not set}"
echo "==========================="
echo ""

# Choose which bot to run based on agent mode
if [ "$AGENT_MODE" = true ]; then
    echo "🚀 Starting Unified Agent (Web + Telegram)..."
    echo "Features: Natural language + Traditional commands + Web UI"
    exec uv run python run_unified.py
else
    echo "🚀 Starting Traditional Command Bot..."
    echo "Features: Traditional commands only"
    exec uv run telegram_bot.py
fi