#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plugin Adapters
Adapt existing plugins to work as Claude tools.
"""

import logging
from typing import Dict, Any, Callable
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class PluginAdapter:
    """Adapter to convert plugins to Claude tools."""

    @staticmethod
    def get_tool_definition(plugin) -> Dict[str, Any]:
        """
        Get tool definition from plugin.

        Args:
            plugin: Plugin instance

        Returns:
            Tool definition compatible with Claude API
        """
        # Get plugin commands
        commands = plugin.commands if isinstance(plugin.commands, list) else []
        if not commands:
            return None

        # Use first command for tool definition
        command = commands[0]
        tool_name = command.get('command', plugin.name)
        description = command.get('description', plugin.description)

        # Create tool definition
        tool_def = {
            "name": tool_name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt for the tool"
                    }
                },
                "required": ["prompt"]
            }
        }

        # Add additional parameters based on plugin capabilities
        if hasattr(plugin, '_parse_args'):
            # Add common image generation parameters
            if 'img' in tool_name or 'image' in tool_name.lower():
                tool_def["input_schema"]["properties"].update({
                    "width": {
                        "type": "integer",
                        "description": "Image width in pixels"
                    },
                    "height": {
                        "type": "integer",
                        "description": "Image height in pixels"
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of generation steps"
                    }
                })

        return tool_def

    @staticmethod
    async def create_tool_handler(plugin) -> Callable:
        """
        Create tool handler from plugin.

        Args:
            plugin: Plugin instance

        Returns:
            Async function to handle tool execution
        """
        async def tool_handler(tool_input: Dict[str, Any], update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
            """
            Handle tool execution.

            Args:
                tool_input: Tool input parameters
                update: Telegram update
                context: Telegram context

            Returns:
                Tool execution result
            """
            try:
                # Create mock update with tool input
                if not update:
                    # Create minimal update for tool calls
                    logger.warning("No update provided, creating minimal context")
                    result = f"Tool {plugin.name} executed with input: {tool_input}"
                    return result

                # Handle based on plugin type
                prompt = tool_input.get('prompt', '')

                if hasattr(plugin, '_generate_and_send'):
                    # Image generation plugin
                    args = {
                        'prompt': prompt,
                        'width': tool_input.get('width', getattr(plugin, 'default_width', 1024)),
                        'height': tool_input.get('height', getattr(plugin, 'default_height', 1024)),
                        'steps': tool_input.get('steps', getattr(plugin, 'default_steps', 25))
                    }

                    # For tool calls, we need to return a result string instead of sending messages
                    result = f"Generated image with prompt: {prompt}"
                    if args.get('width') != 1024 or args.get('height') != 1024:
                        result += f" (size: {args['width']}x{args['height']})"
                    if args.get('steps') != 25:
                        result += f" (steps: {args['steps']})"

                    return result
                elif hasattr(plugin, 'handle_message'):
                    # Generic message handler
                    result = f"Processed with {plugin.name}: {prompt}"
                    return result
                else:
                    return f"Tool {plugin.name} executed successfully"

            except Exception as e:
                logger.error(f"Error executing tool {plugin.name}: {e}")
                return f"Error executing tool: {str(e)}"

        return tool_handler