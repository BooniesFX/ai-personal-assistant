#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web Server for Claude Agent
Provides HTTP + WebSocket interface.
"""

import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import websockets
    from websockets.server import serve
except ImportError:
    websockets = None
    logger.warning("websockets package not installed. Run: pip install websockets")

try:
    from aiohttp import web
except ImportError:
    web = None
    logger.warning("aiohttp package not installed. Run: pip install aiohttp")


async def create_web_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    ws_handler = None,
    static_dir: str = None
):
    """
    Create and start web server with WebSocket support.
    
    Args:
        host: Bind host
        port: Bind port
        ws_handler: WebSocketHandler instance
        static_dir: Directory for static files (web client)
    """
    if web is None:
        raise RuntimeError("aiohttp not installed")
    
    app = web.Application()
    
    # Store handler
    app['ws_handler'] = ws_handler
    app['ws_clients'] = {}
    
    # Routes
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/api/health', health_handler)
    
    # Serve generated images
    images_dir = os.path.join(os.getcwd(), 'data', 'generated_images')
    if os.path.isdir(images_dir):
        app.router.add_static('/images', images_dir, name='images')
    
    # Static files for web client
    if static_dir and os.path.isdir(static_dir):
        app.router.add_static('/', static_dir, name='static')
    else:
        # Serve a simple index page
        app.router.add_get('/', index_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Web server started at http://{host}:{port}")
    logger.info(f"WebSocket endpoint: ws://{host}:{port}/ws")
    
    return runner


async def websocket_handler(request):
    """Handle WebSocket upgrade and connection."""
    ws_handler = request.app['ws_handler']
    
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    # Register client
    client_id = await ws_handler.on_open(ws)
    request.app['ws_clients'][client_id] = ws
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                await ws_handler.on_message(client_id, msg.data)
            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f'WebSocket error: {ws.exception()}')
    finally:
        await ws_handler.on_close(client_id)
        if client_id in request.app['ws_clients']:
            del request.app['ws_clients'][client_id]
    
    return ws


async def health_handler(request):
    """Health check endpoint."""
    return web.json_response({"status": "ok"})


async def index_handler(request):
    """Serve simple index page."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Agent</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        h1 {
            text-align: center;
            padding: 20px;
            color: #fff;
            font-size: 1.5rem;
        }
        .session-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        .session-bar input {
            flex: 1;
            padding: 10px;
            border: 1px solid #444;
            border-radius: 8px;
            background: #2a2a4a;
            color: #fff;
        }
        .session-bar button {
            padding: 10px 20px;
            background: #4a4aff;
            color: #fff;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            margin-bottom: 10px;
        }
        .message {
            margin: 10px 0;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 80%;
        }
        .message.user {
            background: #4a4aff;
            margin-left: auto;
        }
        .message.assistant {
            background: #3a3a5a;
        }
        .message.tool {
            background: #2a4a2a;
            font-size: 0.9em;
        }
        .message.system {
            background: #4a4a2a;
            text-align: center;
            max-width: 100%;
            font-size: 0.9em;
        }
        .input-bar {
            display: flex;
            gap: 10px;
        }
        .input-bar input {
            flex: 1;
            padding: 15px;
            border: 1px solid #444;
            border-radius: 12px;
            background: #2a2a4a;
            color: #fff;
            font-size: 1rem;
        }
        .input-bar button {
            padding: 15px 30px;
            background: #4a4aff;
            color: #fff;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-size: 1rem;
        }
        .input-bar button:disabled {
            background: #3a3a5a;
            cursor: not-allowed;
        }
        .status {
            text-align: center;
            padding: 5px;
            font-size: 0.8rem;
            color: #888;
        }
        /* Modal Styles */
        .modal {
            display: none; 
            position: fixed; 
            z-index: 1000; 
            left: 0;
            top: 0;
            width: 100%; 
            height: 100%; 
            background-color: rgba(0,0,0,0.8);
            align-items: center;
            justify-content: center;
        }
        .modal-content {
            background-color: #2a2a4a;
            padding: 30px;
            border-radius: 12px;
            width: 300px;
            text-align: center;
            border: 1px solid #4a4aff;
        }
        .modal input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border-radius: 6px;
            border: 1px solid #444;
            background: #1a1a2a;
            color: white;
            box-sizing: border-box;
        }
        .modal button {
            width: 100%;
            padding: 10px;
            background: #4a4aff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            margin-top: 10px;
        }
        .user-info {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 0.8rem;
            color: #aaa;
        }
    </style>
</head>
<body>
    <!-- Login Modal -->
    <div id="loginModal" class="modal">
        <div class="modal-content">
            <h2>🔐 Login</h2>
            <p style="color: #aaa; font-size: 0.9rem;">Enter your email to sync memory</p>
            <input type="email" id="emailInput" placeholder="Email Address">
            <input type="password" id="codeInput" placeholder="Access Code (default: password)">
            <button onclick="login()">Login</button>
        </div>
    </div>

    <div class="container">
        <h1>🤖 Claude Agent</h1>
        <div class="user-info" id="userInfo">Guest</div>
        
        <div class="status" id="status">Connecting...</div>
        
        <div class="messages" id="messages"></div>
        
        <div class="input-bar">
            <input type="text" id="input" placeholder="Type a message..." onkeypress="handleKeyPress(event)">
            <button id="sendBtn" onclick="sendMessage()">Send</button>
        </div>
    </div>
    
    <script>
        let ws = null;
        let state = 'connecting';
        let currentUser = null;
        
        function connect() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            
            ws.onopen = () => {
                updateStatus('Connected', '#4a4aff');
                state = 'idle';
                attemptAutoLogin();
            };
            
            ws.onclose = () => {
                updateStatus('Disconnected. Reconnecting...', '#ff4a4a');
                state = 'connecting';
                setTimeout(connect, 3000);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
        
        function attemptAutoLogin() {
            const email = localStorage.getItem('email');
            const code = localStorage.getItem('code');
            if (email && code) {
                ws.send(JSON.stringify({ type: 'login', email, code }));
            } else {
                document.getElementById('loginModal').style.display = 'flex';
            }
        }
        
        function login() {
            const email = document.getElementById('emailInput').value.trim();
            const code = document.getElementById('codeInput').value.trim();
            
            if (!email || !code) {
                alert("Please fill in all fields");
                return;
            }
            
            localStorage.setItem('email', email);
            localStorage.setItem('code', code);
            
            ws.send(JSON.stringify({ type: 'login', email, code }));
        }
        
        function handleMessage(data) {
            switch(data.type) {
                case 'message_added':
                    addMessage(data.message);
                    break;
                case 'session_state_changed':
                    handleStateChange(data.state, data);
                    break;
                case 'login_success':
                    document.getElementById('loginModal').style.display = 'none';
                    currentUser = data.email;
                    document.getElementById('userInfo').textContent = `👤 ${data.email}`;
                    addSystemMessage(`Logged in as ${data.email}`);
                    break;
                case 'error':
                    if (data.code === 'auth_failed') {
                        document.getElementById('loginModal').style.display = 'flex';
                        alert('Login Failed: ' + data.message);
                    } else {
                        addSystemMessage(`Error: ${data.message}`);
                    }
                    break;
            }
        }
        
        function handleStateChange(newState, data) {
            state = newState;
            switch(newState) {
                case 'connected':
                    state = 'idle';  // Treat connected as idle
                    updateStatus('Connected', '#4a4aff');
                    document.getElementById('sendBtn').disabled = false;
                    break;
                case 'thinking':
                    updateStatus('Thinking...', '#ffaa00');
                    document.getElementById('sendBtn').disabled = true;
                    break;
                case 'tool_use':
                    const tools = data.tools ? data.tools.join(', ') : 'unknown';
                    updateStatus(`Using tool: ${tools}`, '#00aaff');
                    break;
                case 'idle':
                    updateStatus('Ready', '#4a4aff');
                    document.getElementById('sendBtn').disabled = false;
                    break;
                case 'error':
                    updateStatus('Error', '#ff4a4a');
                    document.getElementById('sendBtn').disabled = false;
                    break;
            }
        }
        
        function addMessage(msg) {
            const div = document.createElement('div');
            div.className = `message ${msg.role}`;
            
            // Check for markdown image syntax: ![alt](url)
            const content = msg.content;
            const imageRegex = /!\\[([^\\]]*)\\]\\(([^)]+)\\)/g;
            
            if (imageRegex.test(content)) {
                // Reset regex
                imageRegex.lastIndex = 0;
                // Replace markdown images with img tags
                let html = content.replace(imageRegex, '<br><img src="$2" alt="$1" style="max-width:100%;border-radius:8px;margin-top:8px;"><br>');
                // Also convert newlines
                html = html.replace(/\\n/g, '<br>');
                div.innerHTML = html;
            } else {
                div.textContent = content;
            }
            
            document.getElementById('messages').appendChild(div);
            div.scrollIntoView({ behavior: 'smooth' });
        }
        
        function addSystemMessage(text) {
            const div = document.createElement('div');
            div.className = 'message system';
            div.textContent = text;
            document.getElementById('messages').appendChild(div);
        }
        
        function clearMessages() {
            document.getElementById('messages').innerHTML = '';
        }
        
        function updateStatus(text, color) {
            const status = document.getElementById('status');
            status.textContent = text;
            status.style.color = color;
        }
        
        function sendMessage() {
            const input = document.getElementById('input');
            const content = input.value.trim();
            if (!content || state !== 'idle') return;
            
            addMessage({ role: 'user', content });
            ws.send(JSON.stringify({ type: 'chat', content }));
            input.value = '';
        }
        
        function resumeSession() {
            const telegramId = document.getElementById('telegramId').value.trim();
            if (!telegramId) return;
            
            ws.send(JSON.stringify({ type: 'resume', telegramId }));
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') sendMessage();
        }
        
        // Connect on load
        connect();
    </script>
</body>
</html>
    """
    return web.Response(text=html, content_type='text/html')


def run_standalone(host="0.0.0.0", port=8080):
    """Run web server standalone (for testing)."""
    from dotenv import load_dotenv
    load_dotenv()
    
    from agents.core.agent_core import get_agent_core
    from agents.transport.websocket_handler import WebSocketHandler
    
    # Initialize components using unified AgentCore
    from utils.config import load_config
    config = load_config()
    agent_core = get_agent_core(config)
    
    # Create handler
    ws_handler = WebSocketHandler(agent_core)
    
    async def main():
        await agent_core.initialize()
        runner = await create_web_server(
            host=host,
            port=port,
            ws_handler=ws_handler
        )
        
        try:
            # Keep running
            while True:
                await asyncio.sleep(3600)
        finally:
            await runner.cleanup()
    
    asyncio.run(main())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_standalone()
