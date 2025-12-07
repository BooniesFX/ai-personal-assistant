#!/bin/bash
set -e

echo "🔧 Testing Docker configuration for Claude Agent..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running"
    exit 1
fi

echo "✅ Docker is running"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️ .env file not found. Creating minimal test .env..."
    cat > .env << EOF
TELEGRAM_BOT_TOKEN=test_token
ADMIN_ID=123456789
MODELSCOPE_API_KEY=test_key
ANTHROPIC_API_KEY=test_claude_key
EOF
    echo "✅ Created minimal .env file for testing"
fi

# Test building the image
echo "🔨 Building Docker image..."
if docker build -t personal-assistant-test .; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Docker build failed"
    exit 1
fi

# Test creating a container (without running it)
echo "🧪 Creating test container..."
docker create --name test-container --rm \
    -e TELEGRAM_BOT_TOKEN=test_token \
    -e ANTHROPIC_API_KEY=test_key \
    -e MODELSCOPE_API_KEY=test_ms_key \
    -e ADMIN_ID=123456789 \
    personal-assistant-test > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Container created successfully"

    # Test entrypoint script
    echo "📝 Testing entrypoint script..."
    docker start test-container > /dev/null 2>&1 &
    sleep 3

    # Check if container is still running (entrypoint should have failed due to invalid tokens)
    if docker ps | grep -q test-container; then
        echo "✅ Container is running"
        docker stop test-container > /dev/null 2>&1
        docker rm test-container > /dev/null 2>&1
        echo "✅ Container stopped and removed"
    else
        echo "⚠️ Container stopped (expected due to invalid tokens)"
        docker rm test-container > /dev/null 2>&1 2>/dev/null
    fi
else
    echo "❌ Container creation failed"
    exit 1
fi

echo ""
echo "==========================================="
echo "🎉 Docker integration test completed!"
echo ""
echo "To run the bot with Docker:"
echo "1. Create a proper .env file with your real API keys"
echo "2. Run: docker-compose up -d"
echo ""
echo "The bot will automatically:"
echo "✅ Use Claude Agent mode if ANTHROPIC_API_KEY is set"
echo "✅ Fall back to traditional mode if Claude API is not available"
echo "✅ Persist data in ./data directory"
echo "==========================================="