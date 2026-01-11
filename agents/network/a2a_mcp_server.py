#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A2A MCP Server - Agent-to-Agent Communication as MCP Tools

This MCP server exposes A2A capabilities that can be used by ANY MCP-compatible agent:
- Claude Code
- Gemini CLI  
- Codex
- Any other MCP client

Usage:
  1. As stdio server: python -m agents.network.a2a_mcp_server
  2. As HTTP server: python -m agents.network.a2a_mcp_server --http --port 8090
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from typing import Optional, List, Dict, Any

import httpx

# Try to import MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("Warning: mcp package not installed. Run: pip install mcp", file=sys.stderr)

logger = logging.getLogger(__name__)

# Configuration
BUTLER_URL = os.getenv("BUTLER_URL", "http://localhost:8080")

class A2AClient:
    """HTTP client for communicating with Butler and Sidecar agents."""
    
    def __init__(self, butler_url: str = BUTLER_URL):
        self.butler_url = butler_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """Get list of registered agents from Butler."""
        try:
            resp = await self.client.get(f"{self.butler_url}/api/agents")
            resp.raise_for_status()
            data = resp.json()
            return data.get("agents", [])
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []
    
    async def dispatch_to_agent(self, agent_id: str, message: str) -> str:
        """Send a message to a specific agent and get response."""
        try:
            # First get agent info
            agents = await self.list_agents()
            agent = next((a for a in agents if a["id"] == agent_id), None)
            
            if not agent:
                return f"Error: Agent '{agent_id}' not found. Available agents: {[a['id'] for a in agents]}"
            
            # Send request to agent's URL
            agent_url = agent["url"].rstrip("/")
            resp = await self.client.post(
                f"{agent_url}/chat",
                json={"message": message},
                timeout=120.0  # Longer timeout for agent processing
            )
            resp.raise_for_status()
            return resp.json().get("response", "No response from agent")
            
        except httpx.TimeoutException:
            return f"Error: Agent '{agent_id}' timed out"
        except Exception as e:
            logger.error(f"Failed to dispatch to agent {agent_id}: {e}")
            return f"Error: {str(e)}"
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed status of a specific agent."""
        try:
            agents = await self.list_agents()
            agent = next((a for a in agents if a["id"] == agent_id), None)
            
            if not agent:
                return {"error": f"Agent '{agent_id}' not found"}
            
            # Try to ping the agent
            agent_url = agent["url"].rstrip("/")
            try:
                resp = await self.client.get(f"{agent_url}/health", timeout=5.0)
                health = resp.json() if resp.status_code == 200 else {"status": "unknown"}
            except:
                health = {"status": "unreachable"}
            
            return {
                "id": agent["id"],
                "name": agent["name"],
                "url": agent["url"],
                "capabilities": agent.get("capabilities", []),
                "health": health
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        await self.client.aclose()


def create_a2a_mcp_server() -> Server:
    """Create the A2A MCP server with all tools."""
    server = Server("a2a-network")
    client = A2AClient()
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="list_agents",
                description="List all registered agents in the A2A network. Returns agent IDs, names, URLs, and capabilities.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="dispatch_to_agent",
                description="Send a task or message to a specific agent and get its response. Use list_agents first to see available agents.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The ID of the target agent"
                        },
                        "message": {
                            "type": "string",
                            "description": "The message or task to send to the agent"
                        }
                    },
                    "required": ["agent_id", "message"]
                }
            ),
            Tool(
                name="get_agent_status",
                description="Get detailed status and health information of a specific agent.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "The ID of the agent to check"
                        }
                    },
                    "required": ["agent_id"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        if name == "list_agents":
            agents = await client.list_agents()
            if not agents:
                return [TextContent(type="text", text="No agents currently registered in the network.")]
            
            result = "## Registered Agents\n\n"
            for agent in agents:
                result += f"- **{agent['name']}** (ID: `{agent['id']}`)\n"
                result += f"  - URL: {agent['url']}\n"
                result += f"  - Capabilities: {', '.join(agent.get('capabilities', ['general']))}\n\n"
            
            return [TextContent(type="text", text=result)]
        
        elif name == "dispatch_to_agent":
            agent_id = arguments.get("agent_id")
            message = arguments.get("message")
            
            if not agent_id or not message:
                return [TextContent(type="text", text="Error: agent_id and message are required")]
            
            response = await client.dispatch_to_agent(agent_id, message)
            return [TextContent(type="text", text=f"## Response from {agent_id}\n\n{response}")]
        
        elif name == "get_agent_status":
            agent_id = arguments.get("agent_id")
            if not agent_id:
                return [TextContent(type="text", text="Error: agent_id is required")]
            
            status = await client.get_agent_status(agent_id)
            return [TextContent(type="text", text=f"## Agent Status\n\n```json\n{json.dumps(status, indent=2)}\n```")]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    return server


async def run_stdio_server():
    """Run the MCP server in stdio mode (for Claude Code, etc.)"""
    server = create_a2a_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    parser = argparse.ArgumentParser(description="A2A MCP Server")
    parser.add_argument("--http", action="store_true", help="Run as HTTP server instead of stdio")
    parser.add_argument("--port", type=int, default=8090, help="HTTP server port")
    parser.add_argument("--butler-url", type=str, default=BUTLER_URL, help="Butler registry URL")
    args = parser.parse_args()
    
    if not HAS_MCP:
        print("Error: mcp package required. Install with: pip install mcp")
        sys.exit(1)
    
    logging.basicConfig(level=logging.INFO)
    
    if args.http:
        # HTTP mode - for remote access
        print(f"Starting A2A MCP HTTP server on port {args.port}...")
        # TODO: Implement HTTP transport
        print("HTTP mode not yet implemented. Use stdio mode.")
    else:
        # stdio mode - for local MCP clients like Claude Code
        asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
