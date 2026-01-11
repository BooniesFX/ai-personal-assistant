#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Agent Entry Point
Starts the AgentCore with multiple transport adapters.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Silence noisy background logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def main():
    """Run unified agent with all transports."""
    from utils.config import load_config, get_config_value
    from agents.core.agent_core import get_agent_core, Platform
    from agents.transport.websocket_handler import WebSocketHandler
    from agents.transport.web_server import create_web_server
    from agents.transport.telegram_adapter import TelegramAdapter
    
    from telegram import Update
    from telegram.ext import (
        Application, 
        CommandHandler, 
        MessageHandler, 
        filters
    )
    
    # Load config
    config = load_config()
    
    # Initialize the unified AgentCore
    agent_core = get_agent_core(config)
    await agent_core.initialize()
    
    # Register transports
    agent_core.register_transport(Platform.TELEGRAM, "telegram")
    agent_core.register_transport(Platform.WEB, "web")
    
    # === Start Web Server ===
    ws_handler = WebSocketHandler(agent_core)
    web_port = int(get_config_value(config, 'web', 'port', fallback='8080'))
    web_host = get_config_value(config, 'web', 'host', fallback='0.0.0.0')
    
    web_runner = await create_web_server(
        host=web_host,
        port=web_port,
        ws_handler=ws_handler,
        static_dir='static',
        agent_core=agent_core
    )
    logger.info(f"Web transport started at http://{web_host}:{web_port}")
    
    # === Start Telegram Bot (with background retry) ===
    telegram_adapter = TelegramAdapter(agent_core)
    telegram_app = None  # Will be set if connected
    
    bot_token = get_config_value(config, 'telegram', 'bot_token')
    
    async def start_telegram_with_retry():
        """Start Telegram bot with automatic retry on failure."""
        nonlocal telegram_app
        retry_interval = 10  # seconds
        
        while True:
            try:
                application = Application.builder().token(bot_token).build()
                
                # Add handlers
                async def start_command(update, context):
                    await telegram_adapter.handle_command(update, context, "start")
                
                async def help_command(update, context):
                    await telegram_adapter.handle_command(update, context, "help")
                
                async def history_command(update, context):
                    await telegram_adapter.handle_command(update, context, "history")
                
                async def generic_command_handler(update, context):
                    if update.effective_message and update.effective_message.text:
                        text = update.effective_message.text
                        if text.startswith('/'):
                            command = text.split()[0][1:]
                            await telegram_adapter.handle_command(update, context, command)
                
                async def message_handler(update, context):
                    await telegram_adapter.handle_message(update, context)
                
                application.add_handler(CommandHandler("start", start_command))
                application.add_handler(CommandHandler("help", help_command))
                application.add_handler(CommandHandler("history", history_command))
                application.add_handler(MessageHandler(filters.COMMAND, generic_command_handler))
                application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
                
                # Initialize and start
                await application.initialize()
                await application.start()
                await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
                
                telegram_app = application
                logger.info("✅ Telegram transport connected!")
                return  # Success, exit retry loop
                
            except Exception as e:
                logger.warning(f"⚠️ Telegram connection failed: {e}. Retrying in {retry_interval}s...")
                await asyncio.sleep(retry_interval)
    
    telegram_task = None
    if not bot_token:
        logger.warning("No Telegram bot token configured, skipping TG transport")
    else:
        # Start Telegram connection in background (non-blocking)
        telegram_task = asyncio.create_task(start_telegram_with_retry())
        logger.info("🔄 Telegram transport starting in background...")
    
    logger.info("=" * 50)
    logger.info("Unified Agent is running!")
    logger.info(f"  Web:      http://{web_host}:{web_port}")
    if bot_token:
        logger.info("  Telegram: Connecting (background)...")
    logger.info("=" * 50)
    logger.info("Press Ctrl+C to stop")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        # Cleanup
        if telegram_task and not telegram_task.done():
            telegram_task.cancel()
        if telegram_app:
            await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()
        await web_runner.cleanup()
        await agent_core.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
