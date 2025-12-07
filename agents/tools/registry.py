#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tool Registry
Centralized tool/skill management system.
"""

import logging
from typing import Dict, List, Callable, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Centralized tool/skill management system."""

    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.tool_handlers: Dict[str, Callable] = {}

    def register_tool(
        self,
        tool_definition: Dict[str, Any],
        handler: Callable
    ):
        """
        Register a tool with its handler.

        Args:
            tool_definition: Tool definition compatible with Claude API
            handler: Async function to handle tool execution
        """
        tool_name = tool_definition.get('name')
        if not tool_name:
            raise ValueError("Tool definition must include a 'name' field")

        self.tools[tool_name] = tool_definition
        self.tool_handlers[tool_name] = handler
        logger.info(f"Registered tool: {tool_name}")

    def register_plugin_as_tool(self, plugin):
        """
        Register a plugin as a tool.

        Args:
            plugin: Plugin instance to register
        """
        try:
            from .adapters import PluginAdapter

            # Get tool definition
            tool_def = PluginAdapter.get_tool_definition(plugin)
            if not tool_def:
                logger.warning(f"No tool definition for plugin: {plugin.name}")
                return

            # Create tool handler
            tool_handler = PluginAdapter.create_tool_handler(plugin)

            # Register tool
            self.register_tool(tool_def, tool_handler)
        except Exception as e:
            logger.error(f"Error registering plugin {plugin.name} as tool: {e}")

    def unregister_tool(self, tool_name: str):
        """
        Unregister a tool.

        Args:
            tool_name: Name of the tool to unregister
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
        if tool_name in self.tool_handlers:
            del self.tool_handlers[tool_name]
        logger.info(f"Unregistered tool: {tool_name}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all tool definitions.

        Returns:
            List of tool definitions
        """
        return list(self.tools.values())

    def get_tool_definition(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific tool definition.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool definition or None if not found
        """
        return self.tools.get(tool_name)

    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        update: Update = None,
        context: ContextTypes.DEFAULT_TYPE = None
    ) -> str:
        """
        Execute a tool.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            update: Telegram update (optional)
            context: Telegram context (optional)

        Returns:
            Tool execution result as string
        """
        if tool_name not in self.tool_handlers:
            return f"Tool '{tool_name}' not found"

        try:
            handler = self.tool_handlers[tool_name]
            result = await handler(tool_input, update, context)
            return str(result) if result is not None else "Tool executed successfully"
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error executing tool: {str(e)}"

    def list_tools(self) -> List[str]:
        """
        List all registered tools.

        Returns:
            List of tool names
        """
        return list(self.tools.keys())

    def clear(self):
        """Clear all tools."""
        self.tools.clear()
        self.tool_handlers.clear()
        logger.info("Cleared all tools")