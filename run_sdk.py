#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Agent Entry Point - Using Claude Agent SDK
This replaces the old run_unified.py with the new SDK-based architecture.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce noise from verbose loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("aiohttp.server").setLevel(logging.WARNING)

# Load environment
from dotenv import load_dotenv
load_dotenv()

def build_config():
    """Build configuration from environment variables"""
    return {
        'llm': {
            'provider': os.getenv('LLM_PROVIDER', 'anthropic'),
            'api_key': os.getenv('LLM_API_KEY') or os.getenv('ANTHROPIC_API_KEY'),
            'base_url': os.getenv('LLM_BASE_URL') or os.getenv('LLM_API_BASE_URL') or os.getenv('ANTHROPIC_BASE_URL'),
            'model': os.getenv('LLM_MODEL', 'claude-sonnet-4-20250514'),
        },
        'image': {
            'api_key': os.getenv('IMAGE_API_KEY'),
            'base_url': os.getenv('IMAGE_BASE_URL', 'https://api.modelscope.cn/api/v1'),
            'model_id': os.getenv('IMAGE_MODEL_ID', 'Tongyi-MAI/Z-Image-Turbo'),
        },
        'telegram': {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
        },
        'web': {
            'host': os.getenv('WEB_HOST', '0.0.0.0'),
            'port': int(os.getenv('WEB_PORT', '8080')),
        },
        'mcp': {
            'tavily_url': os.getenv('TAVILY_MCP_URL'),
            'tavily_api_key': os.getenv('TAVILY_API_KEY'),
        },
        'agent': {
            'system_prompt': os.getenv('SYSTEM_PROMPT', 'You are Butler, a helpful AI assistant.'),
        },
        'admin': {
            'id': os.getenv('ADMIN_ID'),
        }
    }

async def main():
    logger.info("=" * 50)
    logger.info("Starting Butler Agent (SDK Mode)")
    logger.info("=" * 50)
    
    config = build_config()
    
    # === Start Anthropic-to-OpenAI Proxy if using third-party LLM ===
    proxy_runner = None
    llm_provider = config['llm']['provider']
    
    if llm_provider != 'anthropic' and config['llm']['base_url']:
        logger.info("🔄 Starting Anthropic-to-OpenAI proxy for third-party LLM...")
        
        # Set env vars for proxy
        os.environ["OPENAI_BASE_URL"] = config['llm']['base_url']
        os.environ["OPENAI_API_KEY"] = config['llm']['api_key'] or ""
        os.environ["OPENAI_MODEL"] = config['llm']['model']
        
        from agents.network.anthropic_proxy import run_proxy
        proxy_runner = await run_proxy(host="127.0.0.1", port=4141)
        
        # Point SDK to local proxy
        os.environ["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:4141"
        os.environ["ANTHROPIC_API_KEY"] = "proxy-key"  # Proxy doesn't check this
        
        # Update config to use proxy
        config['llm']['base_url'] = "http://127.0.0.1:4141"
        config['llm']['api_key'] = "proxy-key"
    
    # Import SDK agent
    from agents.sdk.agent import ButlerSDKAgent
    
    agent = ButlerSDKAgent(config)
    logger.info("ButlerSDKAgent initialized")
    
    # === Start Web Server ===
    from aiohttp import web
    from agents.transport.web_server import create_web_app
    from agents.transport.websocket_handler_sdk import WebSocketHandlerSDK
    
    ws_handler = WebSocketHandlerSDK(agent)
    app = create_web_app(ws_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    web_host = config['web']['host']
    web_port = config['web']['port']
    site = web.TCPSite(runner, web_host, web_port)
    await site.start()
    
    logger.info(f"Web server started at http://{web_host}:{web_port}")
    
    # === Start Telegram Bot (optional, background) ===
    bot_token = config['telegram']['bot_token']
    telegram_task = None
    
    if bot_token:
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
        from telegram import Update
        
        async def start_telegram():
            while True:
                try:
                    application = Application.builder().token(bot_token).build()
                    
                    async def handle_message(update: Update, context):
                        user_id = str(update.effective_user.id)
                        text = update.effective_message.text
                        
                        await update.effective_message.reply_text("💭 Thinking...")
                        
                        try:
                            response = await agent.run_one_shot(user_id, text)
                            await update.effective_message.reply_text(response or "No response.")
                        except Exception as e:
                            logger.error(f"Telegram error: {e}")
                            await update.effective_message.reply_text(f"Error: {e}")
                    
                    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
                    
                    await application.initialize()
                    await application.start()
                    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
                    
                    logger.info("✅ Telegram transport connected!")
                    return
                    
                except Exception as e:
                    logger.warning(f"⚠️ Telegram connection failed: {e}. Retrying in 10s...")
                    await asyncio.sleep(10)
        
        telegram_task = asyncio.create_task(start_telegram())
        logger.info("🔄 Telegram transport starting in background...")
    
    logger.info("=" * 50)
    logger.info("Butler Agent (SDK Mode) is running!")
    logger.info(f"  Web: http://{web_host}:{web_port}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 50)
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        if telegram_task and not telegram_task.done():
            telegram_task.cancel()
        await runner.cleanup()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
