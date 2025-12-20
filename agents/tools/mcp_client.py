#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP Client Manager
Handles connections to Model Context Protocol servers.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    transport: str = "stdio"  # 'stdio' or 'sse'
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = None
    url: Optional[str] = None

class MCPClientManager:
    """Manages connections to multiple MCP servers."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        
    async def connect_server(self, name: str, config: MCPServerConfig):
        """Register an MCP server configuration."""
        self.servers[name] = config
        logger.info(f"Registered MCP server config: {name} ({config.transport})")

    async def list_tools(self) -> List[Dict]:
        """List all tools from all registered MCP servers."""
        all_tools = []
        
        for name, config in self.servers.items():
            try:
                if config.transport == "sse":
                    async with sse_client(config.url) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            result = await session.list_tools()
                            all_tools.extend(self._namespace_tools(name, result.tools))
                else:
                    # Stdio default
                    async with stdio_client(
                        StdioServerParameters(
                            command=config.command,
                            args=config.args,
                            env=config.env
                        )
                    ) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            result = await session.list_tools()
                            all_tools.extend(self._namespace_tools(name, result.tools))
                            
            except Exception as e:
                logger.error(f"Error listing tools for {name}: {e}")
                
        return all_tools

    def _namespace_tools(self, server_name: str, tools: List[Any]) -> List[Dict]:
        """Helper to namespace tools."""
        namespaced = []
        for tool in tools:
            namespaced.append({
                "name": f"mcp__{server_name}__{tool.name}",
                "description": f"[{server_name}] {tool.description}",
                "input_schema": tool.inputSchema
            })
        return namespaced

    async def execute_tool(self, name: str, tool_name: str, arguments: Dict) -> Any:
        """Execute a tool on a specific MCP server."""
        if name not in self.servers:
            raise ValueError(f"MCP server not found: {name}")
            
        config = self.servers[name]
        
        try:
            logger.info(f"Executing tool {tool_name} on {name} ({config.transport})...")
            if config.transport == "sse":
                 async with sse_client(config.url) as (read, write):
                    async with ClientSession(read, write) as session:
                        logger.info("SSE Session init...")
                        await session.initialize()
                        logger.info("SSE Calling tool...")
                        result = await session.call_tool(tool_name, arguments)
                        logger.info("SSE Tool called. Returning result.")
                        return result.content
            else:
                async with stdio_client(
                    StdioServerParameters(
                        command=config.command,
                        args=config.args,
                        env=config.env
                    )
                ) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        return result.content
                    
        except Exception as e:
            logger.error(f"Error executing tool {tool_name} on {name}: {e}")
            raise

