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

        # Tools will be loaded asynchronously via load_tools()

        logger.info("ClaudeCodeAgentBot initialized (tools will be loaded async)")

    async def load_tools(self):
        """Load existing tools from plugins (async)."""
        try:
            # Import plugin manager to adapt existing plugins as tools
            from bot.plugin_manager import PluginManager
            from utils.config import load_config

            # Load plugins
            plugin_config = load_config() if not self.config else self.config
            plugin_manager = PluginManager(plugin_config, logger)

            # Actually load the plugins (this is async!)
            await plugin_manager.load_plugins()

            logger.info(f"PluginManager loaded {len(plugin_manager.plugins)} plugins")

            # Adapt plugins to tools
            for plugin in plugin_manager.plugins:
                logger.info(f"Checking plugin: {plugin.name}, enabled={plugin.enabled}, has_tool_def={hasattr(plugin, 'get_tool_definition')}")
                if plugin.enabled and hasattr(plugin, 'get_tool_definition'):
                    try:
                        tool_def = plugin.get_tool_definition()
                        if tool_def:
                            self.tool_registry.register_tool(tool_def, plugin.handle_tool_call)
                            logger.info(f"Registered tool: {tool_def.get('name', 'unknown')}")
                        else:
                            logger.warning(f"Plugin {plugin.name} returned None tool definition")
                    except Exception as e:
                        logger.error(f"Error registering tool from plugin {plugin.name}: {e}")
                        import traceback
                        traceback.print_exc()

            logger.info(f"Total registered tools: {len(self.tool_registry.list_tools())}")

        except Exception as e:
            logger.error(f"Error loading tools: {e}")
            import traceback
            traceback.print_exc()

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
        Process message with Claude, handling tool calls.

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
            
            logger.info(f"Available tools: {[t.get('name') for t in tools]}")

            # System prompt with explicit tool usage instructions
            tool_descriptions = "\n".join([
                f"- {t['name']}: {t['description']}" 
                for t in tools
            ])
            
            system_prompt = (
                "You are a helpful AI assistant with powerful tools integrated into Telegram.\n\n"
                "AVAILABLE TOOLS:\n"
                f"{tool_descriptions}\n\n"
                "CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE:\n\n"
                "1. **Image Generation** (generate_image):\n"
                "   - When user asks to draw/paint/create/generate/make an image (画/生成/创建图片/图像)\n"
                "   - Call immediately without asking\n\n"
                "2. **OPS Problem Analysis** (ops_analyze):\n"
                "   - ONLY call when user explicitly requests: '用OPS', '记录问题', '帮我分析', '给我建议'\n"
                "   - For casual complaints/venting, respond with empathy first\n"
                "   - If problem seems serious, suggest: '需要我用OPS系统帮你分析这个问题吗？'\n"
                "   - Don't auto-trigger on every problem description\n\n"
                "3. **Admin Management** (admin_manage):\n"
                "   - When user asks about permissions/user management (权限/用户管理)\n\n"
                "4. NEVER say you cannot do something if a tool exists for it.\n"
                "5. After tool execution, give a brief friendly response.\n\n"
                "Remember: Be conversational first, use tools when appropriate!"
            )

            # Send initial thinking message
            thinking_msg = await update.effective_message.reply_text("💭 Thinking...")

            if tools:
                # Use tool calling (non-streaming for proper tool handling)
                result = await self.claude_client.create_tool_message(
                    messages=context_messages,
                    tools=tools,
                    system=system_prompt
                )

                response = result.get('response')
                tool_calls = result.get('tool_calls', [])

                logger.info(f"Tool calls detected: {tool_calls}")

                # Handle tool calls
                if tool_calls:
                    # Tools that output directly to user (no need for model follow-up)
                    direct_output_tools = ['generate_image', 'ops_analyze']
                    
                    # Tools that need model to process results
                    needs_followup = []
                    direct_outputs = []
                    
                    for tool_call in tool_calls:
                        tool_name = tool_call['name']
                        tool_input = tool_call['input']
                        tool_id = tool_call['id']

                        await thinking_msg.edit_text(f"🔧 Using tool: {tool_name}...")

                        # Execute tool
                        tool_result = await self.tool_registry.execute_tool(
                            tool_name, tool_input, update, context
                        )

                        if tool_name in direct_output_tools:
                            # Tool already sent output to user, just record result
                            direct_outputs.append({
                                'name': tool_name,
                                'result': tool_result
                            })
                        else:
                            # Tool result needs to be processed by model
                            needs_followup.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": tool_result
                            })

                    # Delete thinking message
                    await thinking_msg.delete()

                    # If we have tools that need follow-up, get model response
                    if needs_followup:
                        # Build messages for follow-up
                        assistant_content = []
                        for content_block in response.content:
                            if content_block.type == 'text':
                                assistant_content.append({"type": "text", "text": content_block.text})
                            elif content_block.type == 'tool_use':
                                assistant_content.append({
                                    "type": "tool_use",
                                    "id": content_block.id,
                                    "name": content_block.name,
                                    "input": content_block.input
                                })
                        
                        follow_up_messages = context_messages + [
                            {"role": "assistant", "content": assistant_content},
                            {"role": "user", "content": needs_followup}
                        ]

                        # Get final response after tool execution
                        final_response = await self.claude_client.create_message(
                            messages=follow_up_messages,
                            system=system_prompt
                        )

                        response_text = ""
                        for content_block in final_response.content:
                            if hasattr(content_block, 'text'):
                                response_text += content_block.text
                        
                        # Send model's response
                        if response_text.strip():
                            await update.effective_message.reply_text(response_text)
                    
                    # For direct output tools, don't save to session (tool already sent output)
                    elif direct_outputs:
                        # Tool already handled the output, no need to save anything
                        response_text = None  # Don't save to session
                    else:
                        response_text = None  # Don't save to session

                else:
                    # No tool calls, extract text response
                    response_text = ""
                    for content_block in response.content:
                        if hasattr(content_block, 'text'):
                            response_text += content_block.text
                    
                    # Delete thinking message and send response
                    await thinking_msg.delete()
                    if response_text.strip():
                        await update.effective_message.reply_text(response_text)
            else:
                # No tools available, direct response
                response = await self.claude_client.create_message(
                    messages=context_messages,
                    system=system_prompt
                )
                response_text = ""
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        response_text += content_block.text
                
                # Delete thinking message and send response
                await thinking_msg.delete()
                if response_text.strip():
                    await update.effective_message.reply_text(response_text)

            # Update session with assistant response (for context tracking)
            # Only save meaningful responses, not internal "Completed" messages
            if 'response_text' in locals() and response_text and response_text.strip():
                await self.session_manager.update_session_context(
                    user_id, chat_id,
                    {"role": "assistant", "content": response_text}
                )

        except Exception as e:
            logger.error(f"Error streaming message: {e}")
            import traceback
            traceback.print_exc()
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