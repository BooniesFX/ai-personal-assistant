#!/bin/bash
# Start Sidecar with Cloudflared Tunnel
# Usage: ./start_sidecar_with_tunnel.sh --command "echo hello" --butler-url "http://cloud:8080"

set -e

# Default values
SIDECAR_PORT=8001
COMMAND=""
BUTLER_URL=""
ADAPTER="cli"
NAME="Tunneled Agent"

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --command) COMMAND="$2"; shift ;;
        --butler-url) BUTLER_URL="$2"; shift ;;
        --port) SIDECAR_PORT="$2"; shift ;;
        --adapter) ADAPTER="$2"; shift ;;
        --name) NAME="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Validate
if [ -z "$BUTLER_URL" ]; then
    echo "❌ Error: --butler-url is required"
    echo "Usage: $0 --command 'echo hello' --butler-url 'http://your-butler:8080'"
    exit 1
fi

if [ "$ADAPTER" == "cli" ] && [ -z "$COMMAND" ]; then
    echo "❌ Error: --command is required for CLI adapter"
    exit 1
fi

# Check cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared not found. Install with: brew install cloudflare/cloudflare/cloudflared"
    exit 1
fi

echo "🚀 Starting Cloudflared Tunnel on port $SIDECAR_PORT..."

# Start cloudflared in background and capture URL
TUNNEL_OUTPUT=$(mktemp)
cloudflared tunnel --url "http://localhost:$SIDECAR_PORT" 2>&1 | tee "$TUNNEL_OUTPUT" &
CLOUDFLARED_PID=$!

# Wait for tunnel URL to appear
echo "⏳ Waiting for tunnel URL..."
TUNNEL_URL=""
for i in {1..30}; do
    TUNNEL_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_OUTPUT" | head -1 || true)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    echo "❌ Failed to get tunnel URL after 30 seconds"
    kill $CLOUDFLARED_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Tunnel created: $TUNNEL_URL"
echo ""
echo "📡 Starting Sidecar..."

# Cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $CLOUDFLARED_PID 2>/dev/null || true
    rm -f "$TUNNEL_OUTPUT"
}
trap cleanup EXIT

# Start sidecar
uv run sidecar/app.py \
    --adapter "$ADAPTER" \
    --command "$COMMAND" \
    --port "$SIDECAR_PORT" \
    --butler-url "$BUTLER_URL" \
    --announced-url "$TUNNEL_URL" \
    --name "$NAME"
