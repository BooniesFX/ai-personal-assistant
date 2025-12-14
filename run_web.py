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
    from agents.core.client import ClaudeClient
    from agents.core.bot import ClaudeCodeAgentBot
    from agents.session.manager import SessionManager
    from agents.memory.store import JSONMemoryStore
    from agents.tools.registry import ToolRegistry
    from agents.transport.websocket_handler import WebSocketHandler
    from agents.transport.web_server import create_web_server
    from bot.plugin_manager import PluginManager
    
    # Load config
    config = load_config()
    
    # Initialize components
    memory_store = JSONMemoryStore("data/claude_memory.json")
    session_manager = SessionManager(memory_store)
    claude_client = ClaudeClient(config)
    tool_registry = ToolRegistry()
    
    # Load plugins as tools
    plugin_manager = PluginManager(config, logger)
    await plugin_manager.load_plugins()
    
    for plugin in plugin_manager.plugins:
        if plugin.enabled and hasattr(plugin, 'get_tool_definition'):
            tool_def = plugin.get_tool_definition()
            if tool_def:
                tool_registry.register_tool(tool_def, plugin.handle_tool_call)
                logger.info(f"Registered tool: {tool_def.get('name')}")
    
    logger.info(f"Total registered tools: {len(tool_registry.list_tools())}")
    
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
