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
    """Manages connections to multiple MCP servers with persistent sessions."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self._sessions: Dict[str, ClientSession] = {}
        self._exit_stacks: Dict[str, Any] = {} # To store context managers
        self._lock = asyncio.Lock()
        
    async def connect_server(self, name: str, config: MCPServerConfig):
        """Register an MCP server configuration."""
        self.servers[name] = config
        logger.info(f"Registered MCP server config: {name} ({config.transport})")

    async def _get_session(self, name: str) -> Optional[ClientSession]:
        """Get or create a persistent session for a server."""
        async with self._lock:
            if name in self._sessions:
                return self._sessions[name]
                
            if name not in self.servers:
                return None
                
            config = self.servers[name]
            try:
                logger.info(f"Initializing persistent MCP session for {name}...")
                from contextlib import AsyncExitStack
                stack = AsyncExitStack()
                self._exit_stacks[name] = stack
                
                if config.transport == "sse":
                    from mcp.client.sse import sse_client
                    read_write = await stack.enter_async_context(sse_client(config.url))
                    read, write = read_write
                else:
                    from mcp.client.stdio import stdio_client, StdioServerParameters
                    read_write = await stack.enter_async_context(stdio_client(
                        StdioServerParameters(
                            command=config.command,
                            args=config.args,
                            env=config.env
                        )
                    ))
                    read, write = read_write
                
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                
                self._sessions[name] = session
                return session
            except Exception as e:
                logger.error(f"Failed to initialize MCP session for {name}: {e}")
                if name in self._exit_stacks:
                    await self._exit_stacks[name].aclose()
                    del self._exit_stacks[name]
                return None

    async def list_tools(self) -> List[Dict]:
        """List all tools from all registered MCP servers using persistent sessions."""
        all_tools = []
        
        for name in list(self.servers.keys()):
            try:
                session = await self._get_session(name)
                if session:
                    result = await session.list_tools()
                    all_tools.extend(self._namespace_tools(name, result.tools))
            except Exception as e:
                logger.error(f"Error listing tools for {name}: {e}")
                # Clear session on error to force reconnect next time
                await self._close_session(name)
                
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
        """Execute a tool on a specific MCP server using a persistent session."""
        session = await self._get_session(name)
        if not session:
            raise ValueError(f"MCP server session not available: {name}")
            
        try:
            logger.info(f"Executing tool {tool_name} on {name} (persistent)...")
            result = await session.call_tool(tool_name, arguments)
            return result.content
        except Exception as e:
            logger.error(f"Error executing tool {tool_name} on {name}: {e}")
            # Clear session on error
            await self._close_session(name)
            raise

    async def _close_session(self, name: str):
        """Close a specific session."""
        if name in self._sessions:
            del self._sessions[name]
        if name in self._exit_stacks:
            await self._exit_stacks[name].aclose()
            del self._exit_stacks[name]

    async def shutdown(self):
        """Shutdown all MCP sessions."""
        logger.info("Shutting down all MCP sessions...")
        for name in list(self._exit_stacks.keys()):
            await self._close_session(name)

