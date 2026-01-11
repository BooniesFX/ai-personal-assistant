#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for running both Telegram bot and Web server.
"""

import asyncio
import logging
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run both Telegram bot and Web server."""
    from utils.config import load_config, get_config_value
    from agents.core.client import ClaudeClient
    from agents.session.manager import SessionManager
    from agents.memory.store import JSONMemoryStore
    from agents.tools.registry import ToolRegistry
    from agents.transport.websocket_handler import WebSocketHandler
    from agents.transport.web_server import create_web_server
    
    # Load config
    config = load_config()
    
    # Initialize shared components
    memory_store = JSONMemoryStore("data/claude_memory.json")
    session_manager = SessionManager(memory_store)
    claude_client = ClaudeClient(config)
    tool_registry = ToolRegistry()
    
    # Create WebSocket handler
    ws_handler = WebSocketHandler(session_manager, claude_client, tool_registry)
    
    # Start web server
    web_port = int(get_config_value(config, 'web', 'port', fallback='8080'))
    web_host = get_config_value(config, 'web', 'host', fallback='0.0.0.0')
    
    runner = await create_web_server(
        host=web_host,
        port=web_port,
        ws_handler=ws_handler
    )
    
    logger.info(f"Web server started on http://{web_host}:{web_port}")
    
    # Import and configure Telegram bot
    try:
        from telegram_claude_agent import HybridClaudeBot
        
        # Create bot with shared components
        bot = HybridClaudeBot(
            config=config,
            session_manager=session_manager,
            claude_client=claude_client,
            tool_registry=tool_registry
        )
        
        # Run bot
        logger.info("Starting Telegram bot...")
        await bot.run_async()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
