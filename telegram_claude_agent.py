#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Claude Agent Bot Entry Point
New entry point for Claude-powered Telegram bot with natural language understanding.
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from agents.core.bot import ClaudeCodeAgentBot
from bot.core import PersonalAssistantBot
from utils.config import load_config, get_config_value

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class HybridClaudeBot:
    """Hybrid bot that combines traditional command-based bot with Claude agent."""

    def __init__(self):
        """Initialize hybrid bot."""
        self.config = load_config()
        self.claude_agent = ClaudeCodeAgentBot(self.config)
        self.traditional_bot = PersonalAssistantBot()

        # Get bot token
        self.bot_token = get_config_value(self.config, 'telegram', 'bot_token')
        if not self.bot_token:
            raise ValueError("Telegram Bot Token not configured!")

        # Create application with proper lifecycle hooks
        self.application = (
            Application.builder()
            .token(self.bot_token)
            .post_init(self.post_init)
            .post_shutdown(self.post_shutdown)
            .build()
        )

    async def start_command(self, update, context):
        """Handle /start command."""
        user = update.effective_user
        await update.message.reply_html(
            f"Hi {user.mention_html()}! 👋\n\n"
            f"I'm your enhanced Personal Assistant Bot powered by Claude AI!\n\n"
            f"You can talk to me naturally or use traditional commands.\n"
            f"Use /help to see all available capabilities."
        )

    async def help_command(self, update, context):
        """Handle /help command."""
        # Get help from both traditional bot and Claude agent
        traditional_help = self.traditional_bot.plugin_manager.get_help_text()
        agent_help = await self.claude_agent.get_help_text()

        help_text = "*🤖 Claude Agent Bot*\n\n"
        help_text += "You can interact with me in two ways:\n\n"
        help_text += "*🗣 Natural Language Mode:*\n"
        help_text += "Just talk to me naturally and I'll understand!\n\n"
        help_text += "*⌨️ Command Mode:*\n"
        help_text += traditional_help + "\n"
        help_text += agent_help

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_message(self, update, context):
        """Handle incoming messages with Claude agent."""
        # Check permissions first (using traditional bot's permission system)
        if not await self.traditional_bot.check_permissions(update, context):
            return

        message_text = update.effective_message.text

        # If it's a command, let the traditional bot handle it
        if message_text.startswith('/'):
            await self.traditional_bot.handle_command(update, context)
            return

        # Otherwise, process with Claude agent
        try:
            # Stream response for better user experience
            await self.claude_agent.stream_message(update, context)
        except Exception as e:
            logger.error(f"Error in Claude agent: {e}")
            await update.effective_message.reply_text(
                f"❌ Sorry, I had trouble processing that: {str(e)}"
            )

    async def handle_callback(self, update, context):
        """Handle callback queries."""
        # Try Claude agent first
        try:
            # Forward to traditional bot for now (simplified approach)
            await self.traditional_bot.handle_callback(update, context)
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await update.callback_query.answer("Error processing request")

    def setup_handlers(self):
        """Setup command and message handlers."""
        # Core commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))

        # Handle all messages (both commands and regular text)
        self.application.add_handler(
            MessageHandler(filters.ALL, self.handle_message)
        )

        # Callback queries
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def post_init(self, application):
        """Post-initialization hook."""
        # Initialize traditional bot components
        await self.traditional_bot.post_init(application)
        
        # Load agent tools (async)
        await self.claude_agent.load_tools()
        
        logger.info("Hybrid bot initialized")

    async def post_shutdown(self, application):
        """Post-shutdown hook."""
        # Cleanup Claude agent
        self.claude_agent.cleanup()
        # Shutdown traditional bot
        await self.traditional_bot.post_shutdown(application)
        logger.info("Hybrid bot shutdown")

    def run(self):
        """Start the bot."""
        logger.info("Starting Hybrid Claude Agent Bot...")

        # Setup handlers
        self.setup_handlers()

        # Run bot (hooks already set via builder)
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Start the hybrid bot."""
    from dotenv import load_dotenv
    load_dotenv()

    try:
        bot = HybridClaudeBot()
        bot.run()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease ensure you have set the required environment variables:")
        print("  - TELEGRAM_BOT_TOKEN (required)")
        print("  - LLM_API_KEY (required for agent mode, or ANTHROPIC_API_KEY)")
        print("  - IMAGE_API_KEY (required for image generation)")
        print("  - ADMIN_ID (required)")
        print("\nOptional:")
        print("  - LLM_PROVIDER (cas, anthropic, openai)")
        print("  - LLM_MODEL (model name)")
        print("  - IMAGE_PROVIDER (modelscope, etc)")
        print("\nYou can set them in a .env file or export them directly.")
        print("See .env.example for reference.")
    except Exception as e:
        print(f"Error starting bot: {e}")
        logger.exception("Error starting bot")


if __name__ == "__main__":
    main()