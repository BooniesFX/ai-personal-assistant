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

from .client import ClaudeClient
from ..session.manager import SessionManager
from ..memory.store import JSONMemoryStore
from ..tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ClaudeCodeAgentBot:
    """Main Claude Agent Bot controller."""

    def __init__(self, config=None):
        """
        Initialize Claude Agent Bot.

        Args:
            config: Configuration object (optional)
        """
        self.config = config

        # Initialize components
        self.claude_client = ClaudeClient(config)
        self.memory_store = JSONMemoryStore("data/claude_memory.json")
        self.session_manager = SessionManager(self.memory_store)
        self.tool_registry = ToolRegistry()

        # Load existing tools/plugins
        self._load_tools()

        logger.info("ClaudeCodeAgentBot initialized")

    def _load_tools(self):
        """Load existing tools from plugins."""
        try:
            # Import plugin manager to adapt existing plugins as tools
            from bot.plugin_manager import PluginManager
            from utils.config import load_config

            # Load plugins
            plugin_config = load_config() if not self.config else self.config
            plugin_manager = PluginManager(plugin_config, logger)

            # Adapt plugins to tools
            for plugin in plugin_manager.plugins:
                if plugin.enabled and hasattr(plugin, 'get_tool_definition'):
                    try:
                        tool_def = plugin.get_tool_definition()
                        if tool_def:
                            self.tool_registry.register_tool(tool_def, plugin.handle_tool_call)
                            logger.info(f"Registered tool: {tool_def.get('name', 'unknown')}")
                    except Exception as e:
                        logger.error(f"Error registering tool from plugin {plugin.name}: {e}")

        except Exception as e:
            logger.error(f"Error loading tools: {e}")

    async def process_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[str]:
        """
        Process incoming message with Claude agent.

        Args:
            update: Telegram update
            context: Telegram context

        Returns:
            Response text or None if no response
        """
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            message_text = update.effective_message.text

            # Update session context
            await self.session_manager.update_session_context(
                user_id, chat_id,
                {"role": "user", "content": message_text}
            )

            # Get session context
            context_messages = await self.session_manager.get_session_context(user_id, chat_id)

            # Get available tools
            tools = self.tool_registry.get_tool_definitions()

            # System prompt
            system_prompt = (
                "You are a helpful AI assistant integrated with Telegram. "
                "You can help users with various tasks using available tools. "
                "Respond naturally and concisely. When using tools, explain what you're doing. "
                "If you don't understand a request, ask for clarification."
            )

            # Process with Claude
            if tools:
                # Use tool calling
                result = await self.claude_client.create_tool_message(
                    messages=context_messages,
                    tools=tools,
                    system=system_prompt
                )

                response_text = ""
                tool_calls = result.get('tool_calls', [])

                # Handle tool calls
                if tool_calls:
                    for tool_call in tool_calls:
                        tool_name = tool_call['name']
                        tool_input = tool_call['input']
                        tool_id = tool_call['id']

                        # Execute tool
                        tool_result = await self.tool_registry.execute_tool(
                            tool_name, tool_input, update, context
                        )

                        # Add tool result to context
                        await self.session_manager.update_session_context(
                            user_id, chat_id,
                            {
                                "role": "user",
                                "content": f"[Tool Result for {tool_name}]: {tool_result}"
                            }
                        )

                        response_text += f"Executed {tool_name}: {tool_result}\n"

                    # Get final response
                    final_context = await self.session_manager.get_session_context(user_id, chat_id)
                    final_response = await self.claude_client.create_message(
                        messages=final_context,
                        system=system_prompt
                    )

                    response_text += final_response.content[0].text
                else:
                    # Direct response
                    response_text = result['response'].content[0].text

            else:
                # No tools available, direct response
                response = await self.claude_client.create_message(
                    messages=context_messages,
                    system=system_prompt
                )
                response_text = response.content[0].text

            # Update session with assistant response
            await self.session_manager.update_session_context(
                user_id, chat_id,
                {"role": "assistant", "content": response_text}
            )

            return response_text

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    async def stream_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Stream response to user.

        Args:
            update: Telegram update
            context: Telegram context
        """
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            message_text = update.effective_message.text

            # Update session context
            await self.session_manager.update_session_context(
                user_id, chat_id,
                {"role": "user", "content": message_text}
            )

            # Get session context
            context_messages = await self.session_manager.get_session_context(user_id, chat_id)

            # Get available tools
            tools = self.tool_registry.get_tool_definitions()

            # System prompt
            system_prompt = (
                "You are a helpful AI assistant integrated with Telegram. "
                "You can help users with various tasks using available tools. "
                "Respond naturally and concisely. When using tools, explain what you're doing. "
                "If you don't understand a request, ask for clarification."
            )

            # Send initial thinking message
            thinking_msg = await update.effective_message.reply_text("💭 Thinking...")

            response_text = ""

            if tools:
                # Use tool calling with streaming
                async for chunk in self.claude_client.stream_message(
                    messages=context_messages,
                    tools=tools,
                    system=system_prompt
                ):
                    response_text += chunk

                    # Update message periodically to show progress
                    if len(response_text) % 100 == 0:
                        try:
                            await thinking_msg.edit_text(f"💭 {response_text[:200]}...")
                        except:
                            pass
            else:
                # Direct streaming response
                async for chunk in self.claude_client.stream_message(
                    messages=context_messages,
                    system=system_prompt
                ):
                    response_text += chunk

                    # Update message periodically to show progress
                    if len(response_text) % 100 == 0:
                        try:
                            await thinking_msg.edit_text(f"💭 {response_text[:200]}...")
                        except:
                            pass

            # Delete thinking message and send final response
            await thinking_msg.delete()
            await update.effective_message.reply_text(response_text)

            # Update session with assistant response
            await self.session_manager.update_session_context(
                user_id, chat_id,
                {"role": "assistant", "content": response_text}
            )

        except Exception as e:
            logger.error(f"Error streaming message: {e}")
            await update.effective_message.reply_text(f"Sorry, I encountered an error: {str(e)}")

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