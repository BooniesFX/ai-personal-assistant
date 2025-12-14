#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Transport Adapter
Converts between Telegram messages and AgentCore format.
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from agents.core.agent_core import AgentCore, Message, Response, Platform

logger = logging.getLogger(__name__)


class TelegramAdapter:
    """
    Telegram transport adapter.
    
    Converts Telegram Update objects to unified Message format
    and Response objects back to Telegram messages.
    """
    
    def __init__(self, agent_core: AgentCore):
        """
        Initialize adapter.
        
        Args:
            agent_core: The unified AgentCore instance
        """
        self.agent_core = agent_core
    
    async def handle_message(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        Handle incoming Telegram message.
        
        Args:
            update: Telegram Update
            context: Telegram context
            
        Returns:
            Response text or None
        """
        if not update.effective_message or not update.effective_message.text:
            return None
        
        user_id = str(update.effective_user.id)
        text = update.effective_message.text
        
        # Skip command messages (handled elsewhere)
        if text.startswith('/'):
            return None
        
        # Convert to unified message format
        message = Message(
            user_id=user_id,
            platform=Platform.TELEGRAM,
            content=text,
            metadata={
                'chat_id': update.effective_chat.id,
                'message_id': update.effective_message.message_id,
                'username': update.effective_user.username
            }
        )
        
        # Send thinking indicator
        thinking_msg = await update.effective_message.reply_text("💭 Thinking...")
        
        try:
            # Process via AgentCore
            response = await self.agent_core.process_message(
                message,
                platform_context=update
            )
            
            # Delete thinking message
            try:
                await thinking_msg.delete()
            except:
                pass
            
            # Send response
            if response.content:
                await update.effective_message.reply_text(response.content)
            
            # Log tool usage if any
            if response.tool_calls:
                logger.info(f"Tools used: {[tc.get('name') for tc in response.tool_calls]}")
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error in TelegramAdapter: {e}")
            try:
                await thinking_msg.edit_text(f"❌ Error: {str(e)}")
            except:
                pass
            return None
    
    async def handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        command: str
    ) -> Optional[str]:
        """
        Handle Telegram command.
        
        Args:
            update: Telegram Update
            context: Telegram context
            command: Command name (without /)
            
        Returns:
            Response text or None
        """
        user_id = str(update.effective_user.id)
        
        if command == "start":
            return await self._handle_start(update)
        elif command == "help":
            return await self._handle_help(update)
        elif command == "history":
            return await self._handle_history(update, user_id)
        
        # Route to plugins
        plugins_map = self.agent_core.plugin_manager.get_all_commands()
        if command in plugins_map:
            plugin = plugins_map[command]
            
            # Ensure context.args is populated
            if not context.args and update.effective_message and update.effective_message.text:
                parts = update.effective_message.text.split()
                if len(parts) > 1:
                    context.args = parts[1:]
            
            await plugin.handle_command(command, update, context)
            return "Handled by plugin"
        
        return None
    
    async def _handle_start(self, update: Update) -> str:
        """Handle /start command."""
        text = (
            "👋 Welcome to Claude Agent!\n\n"
            "I'm an AI assistant that can help you with various tasks.\n\n"
            "Just send me a message to chat, or use /help for more info."
        )
        await update.effective_message.reply_text(text)
        return text
    
    async def _handle_help(self, update: Update) -> str:
        """Handle /help command."""
        tools = self.agent_core.tool_registry.list_tools()
        tool_list = "\n".join([f"  • {t}" for t in tools]) if tools else "  (none)"
        
        text = (
            "🤖 *Claude Agent Help*\n\n"
            "*Commands:*\n"
            "  /start - Welcome message\n"
            "  /help - This help\n"
            "  /history - View chat history\n\n"
            f"*Available Tools:*\n{tool_list}\n\n"
            "Send any message to chat with me!"
        )
        await update.effective_message.reply_text(text, parse_mode='Markdown')
        return text
    
    async def _handle_history(self, update: Update, user_id: str) -> str:
        """Handle /history command."""
        history = await self.agent_core.get_session_history(user_id, Platform.TELEGRAM)
        
        if not history:
            text = "No conversation history yet."
        else:
            lines = []
            for msg in history[-10:]:  # Last 10 messages
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:100]  # Truncate
                if len(msg.get('content', '')) > 100:
                    content += "..."
                lines.append(f"*{role}*: {content}")
            text = "📜 *Recent History:*\n\n" + "\n\n".join(lines)
        
        await update.effective_message.reply_text(text, parse_mode='Markdown')
        return text
