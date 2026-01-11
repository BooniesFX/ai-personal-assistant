#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP HTTP Endpoint for Butler

This module adds an SSE (Server-Sent Events) based MCP endpoint to Butler,
allowing remote agents to connect via mcp-remote.

Usage on remote device:
  In Claude Code's ~/.claude.json:
  {
    "mcpServers": {
      "butler-a2a": {
        "command": "npx",
        "args": ["-y", "mcp-remote", "http://YOUR_BUTLER_IP:8080/mcp"]
      }
    }
  }
"""

import json
import asyncio
import logging
from typing import Dict, Any, List
from aiohttp import web
from aiohttp_sse import sse_response

logger = logging.getLogger(__name__)

# Tool definitions for A2A
MCP_TOOLS = [
    {
        "name": "list_agents",
        "description": "List all registered agents in the A2A network. Returns agent IDs, names, URLs, and capabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "dispatch_to_agent",
        "description": "Send a task or message to a specific agent and get its response. Use list_agents first to see available agents.",
        "inputSchema": {
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
    },
    {
        "name": "get_agent_status",
        "description": "Get detailed status and health information of a specific agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "The ID of the agent to check"
                }
            },
            "required": ["agent_id"]
        }
    }
]


async def handle_mcp_sse(request):
    """
    Handle MCP requests over SSE (Server-Sent Events).
    This is the Streamable HTTP Transport for MCP.
    """
    async with sse_response(request) as resp:
        # Send server info
        server_info = {
            "jsonrpc": "2.0",
            "id": 0,
            "result": {
                "protocolVersion": "2025-11-25",
                "serverInfo": {
                    "name": "butler-a2a",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }
        await resp.send(json.dumps(server_info), event="message")
        
        # Keep connection alive and handle requests
        while True:
            await asyncio.sleep(30)  # Keep-alive
            await resp.send(json.dumps({"type": "ping"}), event="ping")


async def handle_mcp_post(request):
    """
    Handle MCP JSON-RPC requests via POST.
    This is the simpler HTTP transport for tools/call.
    """
    try:
        data = await request.json()
        method = data.get("method", "")
        params = data.get("params", {})
        req_id = data.get("id", 0)
        
        if method == "initialize":
            return web.json_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2025-11-25",
                    "serverInfo": {"name": "butler-a2a", "version": "1.0.0"},
                    "capabilities": {"tools": {}}
                }
            })
        
        elif method == "tools/list":
            return web.json_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": MCP_TOOLS}
            })
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            result = await execute_tool(request.app, tool_name, tool_args)
            
            return web.json_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result}]
                }
            })
        
        else:
            return web.json_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })
            
    except Exception as e:
        logger.error(f"MCP error: {e}")
        return web.json_response({
            "jsonrpc": "2.0",
            "id": 0,
            "error": {"code": -32603, "message": str(e)}
        })


async def execute_tool(app, tool_name: str, args: Dict[str, Any]) -> str:
    """Execute an A2A tool and return result."""
    import httpx
    
    butler_url = "http://localhost:8080"  # Self-reference
    
    if tool_name == "list_agents":
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{butler_url}/api/agents")
                agents = resp.json().get("agents", [])
                
                if not agents:
                    return "No agents currently registered."
                
                result = "## Registered Agents\n\n"
                for agent in agents:
                    result += f"- **{agent['name']}** (ID: `{agent['id']}`)\n"
                    result += f"  - URL: {agent['url']}\n"
                    caps = agent.get('capabilities', ['general'])
                    result += f"  - Capabilities: {', '.join(caps)}\n\n"
                return result
        except Exception as e:
            return f"Error: {e}"
    
    elif tool_name == "dispatch_to_agent":
        agent_id = args.get("agent_id")
        message = args.get("message")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{butler_url}/api/agents")
                agents = resp.json().get("agents", [])
                agent = next((a for a in agents if a["id"] == agent_id), None)
                
                if not agent:
                    return f"Agent '{agent_id}' not found. Available: {[a['id'] for a in agents]}"
                
                agent_url = agent["url"].rstrip("/")
                resp = await client.post(
                    f"{agent_url}/chat",
                    json={"message": message},
                    timeout=120.0
                )
                return resp.json().get("response", "No response")
        except Exception as e:
            return f"Error: {e}"
    
    elif tool_name == "get_agent_status":
        agent_id = args.get("agent_id")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{butler_url}/api/agents")
                agents = resp.json().get("agents", [])
                agent = next((a for a in agents if a["id"] == agent_id), None)
                
                if not agent:
                    return f"Agent '{agent_id}' not found"
                
                return json.dumps(agent, indent=2)
        except Exception as e:
            return f"Error: {e}"
    
    return f"Unknown tool: {tool_name}"


def add_mcp_routes(app: web.Application):
    """Add MCP routes to an existing aiohttp app."""
    app.router.add_get('/mcp', handle_mcp_sse)
    app.router.add_post('/mcp', handle_mcp_post)
    logger.info("MCP endpoint added at /mcp")
