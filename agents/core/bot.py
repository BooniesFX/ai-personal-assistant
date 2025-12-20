#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Claude Code Agent Bot
Main controller for Claude-powered Telegram bot with natural language understanding.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any
from telegram import Update
from telegram.ext import Application, ContextTypes

from .agent_core import get_agent_core, Message, Platform

class ClaudeCodeAgentBot:
    """Main Claude Agent Bot controller (Wrapper around AgentCore)."""

    def __init__(self, config=None):
        """
        Initialize Claude Agent Bot.

        Args:
            config: Configuration object (optional)
        """
        self.config = config
        self.agent_core = get_agent_core(config)
        logger.info("ClaudeCodeAgentBot initialized (Using Unified AgentCore)")

    async def load_tools(self):
        """Deprecated: AgentCore handles tool loading."""
        if not self.agent_core._initialized:
             await self.agent_core.initialize()

    async def process_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        Process incoming message with Claude agent via AgentCore.
        """
        try:
            user_id = str(update.effective_user.id)
            message_text = update.effective_message.text
            
            # Create Thinking Message
            status_msg = await update.effective_message.reply_text("💭 Thinking...")
            
            async def status_callback(status: str):
                """Update status message."""
                try:
                    # Edit message with current status
                    # To avoid spamming edits (Telegram limit), we might want to debounce,
                    # but for now direct edit is fine for low volume.
                    if status_msg:
                        await status_msg.edit_text(status)
                except Exception as e:
                    logger.warning(f"Failed to update status message: {e}")

            # Create unified message
            msg = Message(
                user_id=user_id,
                platform=Platform.TELEGRAM,
                content=message_text,
                metadata={"update": update, "context": context}
            )
            
            # Process via AgentCore
            response = await self.agent_core.process_message(
                msg, 
                platform_context=update,
                status_callback=status_callback
            )
            
            # Delete thinking message
            try:
                await status_msg.delete()
            except:
                pass
                
            # Reply with final content
            if response.content:
                await update.effective_message.reply_text(response.content)
            
            # If there were errors
            if response.metadata.get("error"):
                logger.error(f"AgentCore returned error: {response.content}")
                
            return response.content

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"



    async def get_help_text(self) -> str:
        """
        Get help text for available tools.

        Returns:
            Help text string
        """
        tools = self.tool_registry.get_tool_definitions()
        if not tools:
            return "No tools available."

        help_text = "*Available Tools:*\n\n"
        for tool in tools:
            name = tool.get('name', 'Unknown')
            description = tool.get('description', 'No description')
            help_text += f"• `{name}` - {description}\n"

        return help_text

    def cleanup(self):
        """Cleanup resources."""
        try:
            self.session_manager.cleanup_expired_sessions()
            self.memory_store.save()
            logger.info("ClaudeCodeAgentBot cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")