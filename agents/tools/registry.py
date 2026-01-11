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

    def get_tool_definition(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific tool definition.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool definition or None if not found
        """
        return self.tools.get(tool_name)

    async def register_mcp_source(self, mcp_client_manager):
        """Register MCP client manager as a tool source."""
        self.mcp_client_manager = mcp_client_manager
        self._cached_definitions = None  # Reset cache when new source is registered
        logger.info("Registered MCP source in ToolRegistry")

    def register_skill_manager(self, skill_manager):
        """Register skill manager as a source for business SOPs."""
        self.skill_manager = skill_manager
        self._cached_definitions = None  # Reset cache
        logger.info("Registered SkillManager in ToolRegistry")

    async def get_tool_definitions(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get all tool definitions (Local + Skills + MCP).
        Uses caching to avoid repeated network calls.
        
        Args:
            force_refresh: If True, ignore cache and refetch everything
        
        Returns:
            List of tool definitions
        """
        # Return cached if available
        if not force_refresh and hasattr(self, '_cached_definitions') and self._cached_definitions is not None:
            return self._cached_definitions
        
        # Build fresh definitions
        definitions = list(self.tools.values())
        
        # Get business skills (SOPs)
        if hasattr(self, 'skill_manager') and self.skill_manager:
            definitions.extend(self.skill_manager.get_skill_definitions())
            
        # Get MCP tools (only fetch once, then cache)
        if hasattr(self, 'mcp_client_manager') and self.mcp_client_manager:
            try:
                mcp_tools = await self.mcp_client_manager.list_tools()
                definitions.extend(mcp_tools)
                logger.info(f"Cached {len(mcp_tools)} MCP tools")
            except Exception as e:
                logger.error(f"Error fetching MCP tools: {e}")
        
        self._cached_definitions = definitions
        return definitions


    def is_skill(self, tool_name: str) -> bool:
        """Check if a capability is a high-level Skill (SOP)."""
        if hasattr(self, 'skill_manager') and self.skill_manager:
            return self.skill_manager.get_skill(tool_name) is not None
        return False

    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        update: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a tool by name."""
        # 1. Check for Business Skills (SOPs) - High Priority
        if hasattr(self, 'skill_manager') and self.skill_manager:
            skill = self.skill_manager.get_skill(tool_name)
            if skill:
                logger.debug(f"Executing skill: {tool_name}")
                return await self.skill_manager.execute_skill(tool_name, tool_input, {"platform": update})

        # 2. Check for MCP Tools
        if tool_name.startswith("mcp__") and hasattr(self, 'mcp_client_manager') and self.mcp_client_manager:
            try:
                parts = tool_name.split("__")
                if len(parts) >= 3:
                    server_name = parts[1]
                    real_tool_name = "__".join(parts[2:])
                    return await self.mcp_client_manager.execute_tool(server_name, real_tool_name, tool_input)
            except Exception as e:
                logger.error(f"Error executing MCP tool {tool_name}: {e}")
                return f"Error executing MCP tool: {str(e)}"

        # 3. Check for Local Tools (Technical Plugins)
        if tool_name in self.tool_handlers:
            try:
                handler = self.tool_handlers[tool_name]
                result = await handler(tool_input, update, context)
                return str(result) if result is not None else "Tool executed successfully"
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                return f"Error executing tool: {str(e)}"

        return f"Capability '{tool_name}' not found"

    def list_tools(self) -> List[str]:
        """
        List all registered local tools.
        (Sync method only lists local tools for backward compatibility if needed, 
         but ideally should use get_tool_definitions)
        """
        return list(self.tools.keys())

    def clear(self):
        """Clear all tools."""
        self.tools.clear()
        self.tool_handlers.clear()
        logger.info("Cleared all tools")