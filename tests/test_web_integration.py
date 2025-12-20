#!/usr/bin/env python3
import asyncio
import json
import logging
import websockets
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_weather_and_image():
    uri = "ws://localhost:8080/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket")
            
            # 1. Wait for initial connection state
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                logger.info(f"Received: {data['type']}")
                if data['type'] == 'session_state_changed' and data['state'] == 'connected':
                    break
            
            # 2. Login (Guest)
            # Web client typically sends login, but guest mode might work if allowed. 
            # based on run_web.py, it seems we might need to send a message directly.
            
            # 3. Send Request
            prompt = "请查一下北京现在的天气，并画一张符合这个天气的图片"
            logger.info(f"Sending prompt: {prompt}")
            
            await websocket.send(json.dumps({
                "type": "chat",
                "content": prompt
            }))
            
            # 4. Listen for responses (Thinking, Tool Use, etc.)
            tools_used = []
            final_response = ""
            image_generated = False
            
            # Wait for up to 60 seconds
            try:
                async with asyncio.timeout(60):
                    while True:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        msg_type = data.get('type')
                        
                        if msg_type == 'session_state_changed':
                            state = data.get('state')
                            logger.info(f"State: {state} {data.get('tools', '')}")
                            
                            if state == 'tool_use':
                                tools_used.extend(data.get('tools', []))
                                
                            if state == 'idle':
                                # Interaction finished
                                break
                                
                        elif msg_type == 'message_added':
                            msg = data.get('message', {})
                            role = msg.get('role')
                            content = msg.get('content', '')
                            
                            logger.info(f"Message ({role}): {content[:100]}...")
                            
                            if role == 'assistant':
                                final_response += content
                                # Check for image markdown
                                if '![' in content and '](' in content:
                                    image_generated = True
                                    logger.info("Image markdown detected!")
            
            except asyncio.TimeoutError:
                logger.error("Test timed out!")
            
            # 5. Assertions
            if 'mcp__tavily__search' in [t for t in tools_used if 'tavily' in t]:
                logger.info("✅ PASS: Tavily Search used")
            elif 'mcp__tavily__search' in str(tools_used): # Fuzzy check
                 logger.info("✅ PASS: Tavily Search used")
            else:
                logger.warning(f"⚠️ WARN: Search tool usage not explicitly detected in state updates (Tools: {tools_used})")

            if 'generate_image' in tools_used:
                logger.info("✅ PASS: Image Generation used")
            else:
                 logger.warning(f"⚠️ WARN: Image tool usage not explicitly detected (Tools: {tools_used})")
                 
            if image_generated:
                logger.info("✅ PASS: Image output detected")
            else:
                logger.error("❌ FAIL: No image output detected")
                
    except Exception as e:
        logger.error(f"Connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_weather_and_image())
