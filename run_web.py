#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web-only entry point for Claude Agent.
Runs web server without Telegram bot.
"""

import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run web server only."""
    from utils.config import load_config, get_config_value
    from agents.core.agent_core import get_agent_core
    from agents.transport.websocket_handler import WebSocketHandler
    from agents.transport.web_server import create_web_server
    
    # Load config
    config = load_config()
    
    # Initialize Unified Agent Core
    # This handles memory, tools, plugins, and MCP automatically
    agent_core = get_agent_core(config)
    await agent_core.initialize()
    
    # Create WebSocket handler with AgentCore
    ws_handler = WebSocketHandler(agent_core)
    
    # Start web server
    web_port = int(get_config_value(config, 'web', 'port', fallback='8080'))
    web_host = get_config_value(config, 'web', 'host', fallback='0.0.0.0')
    
    runner = await create_web_server(
        host=web_host,
        port=web_port,
        ws_handler=ws_handler
    )
    
    logger.info(f"Web server running at http://{web_host}:{web_port}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
