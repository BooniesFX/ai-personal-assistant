#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from claude_agent_sdk import tool, create_sdk_mcp_server
from utils.api_client import ModelScopeClient
import os
import uuid
import logging
import httpx

logger = logging.getLogger(__name__)

# Global clients
_modelscope_client = None
_butler_url = "http://localhost:8080"

def init_tools(config):
    global _modelscope_client, _butler_url
    api_key = config.get('image', {}).get('api_key')
    base_url = config.get('image', {}).get('base_url')
    _modelscope_client = ModelScopeClient(api_key=api_key, base_url=base_url, logger=logger)
    
    # Butler URL for A2A (self-reference when running as Butler)
    web_port = config.get('web', {}).get('port', 8080)
    _butler_url = f"http://localhost:{web_port}"

@tool("generate_image", "Generate an AI image based on a text prompt. ONLY use this when the user explicitly requests to draw or generate an image.", {
    "prompt": str,
    "width": int,
    "height": int,
    "steps": int
})
async def generate_image(args):
    """SDK tool wrapper for image generation"""
    if not _modelscope_client:
        return {"content": [{"type": "text", "text": "Error: Image client not initialized."}]}
    
    prompt = args.get("prompt")
    width = args.get("width", 1024)
    height = args.get("height", 1024)
    steps = args.get("steps", 15)
    
    try:
        image_bio = await _modelscope_client.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            steps=steps
        )
        
        if image_bio:
            images_dir = "static/images"
            os.makedirs(images_dir, exist_ok=True)
            
            filename = f"img_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(images_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_bio.read())
            
            image_url = f"/images/{filename}"
            return {
                "content": [
                    {"type": "text", "text": f"✨ Image Generated for prompt: {prompt}"},
                    {"type": "text", "text": f"![Result]({image_url})"}
                ]
            }
        else:
            return {"content": [{"type": "text", "text": "Failed: Image data is empty."}]}
            
    except Exception as e:
        logger.error(f"Tool error in generate_image: {e}")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


# ============ A2A Network Tools ============

@tool("list_agents", "List all registered agents in the A2A network. Returns agent IDs, names, URLs, and capabilities.", {})
async def list_agents(args):
    """List all agents registered with Butler."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{_butler_url}/api/agents")
            resp.raise_for_status()
            data = resp.json()
            agents = data.get("agents", [])
            
            if not agents:
                return {"content": [{"type": "text", "text": "No agents currently registered in the network."}]}
            
            result = "## Registered Agents\n\n"
            for agent in agents:
                result += f"- **{agent['name']}** (ID: `{agent['id']}`)\n"
                result += f"  - URL: {agent['url']}\n"
                caps = agent.get('capabilities', ['general'])
                result += f"  - Capabilities: {', '.join(caps) if caps else 'general'}\n\n"
            
            return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool("dispatch_to_agent", "Send a task or message to a specific agent and get its response. Use list_agents first to see available agents.", {
    "agent_id": str,
    "message": str
})
async def dispatch_to_agent(args):
    """Send a message to a specific agent."""
    agent_id = args.get("agent_id")
    message = args.get("message")
    
    if not agent_id or not message:
        return {"content": [{"type": "text", "text": "Error: agent_id and message are required"}]}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get agent info
            resp = await client.get(f"{_butler_url}/api/agents")
            agents = resp.json().get("agents", [])
            agent = next((a for a in agents if a["id"] == agent_id), None)
            
            if not agent:
                available = [a['id'] for a in agents]
                return {"content": [{"type": "text", "text": f"Error: Agent '{agent_id}' not found. Available: {available}"}]}
            
            # Send to agent
            agent_url = agent["url"].rstrip("/")
            resp = await client.post(
                f"{agent_url}/chat",
                json={"message": message},
                timeout=120.0
            )
            resp.raise_for_status()
            response = resp.json().get("response", "No response")
            
            return {"content": [{"type": "text", "text": f"## Response from {agent['name']}\n\n{response}"}]}
            
    except httpx.TimeoutException:
        return {"content": [{"type": "text", "text": f"Error: Agent '{agent_id}' timed out"}]}
    except Exception as e:
        logger.error(f"Error dispatching to agent: {e}")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


# ============ Web Search Tool ============

_tavily_api_key = None

def init_tavily(api_key: str):
    global _tavily_api_key
    _tavily_api_key = api_key

@tool("web_search", "Search the web for current information. Use this for weather, news, real-time data, etc.", {
    "query": str
})
async def web_search(args):
    """Search the web using Tavily API."""
    query = args.get("query")
    if not query:
        return {"content": [{"type": "text", "text": "Error: query is required"}]}
    
    api_key = _tavily_api_key or os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"content": [{"type": "text", "text": "⚠️ Web search not configured. Please set TAVILY_API_KEY."}]}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "max_results": 5
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Format results
            result = f"## Search Results for: {query}\n\n"
            
            if data.get("answer"):
                result += f"**Summary:** {data['answer']}\n\n"
            
            result += "### Sources:\n"
            for item in data.get("results", [])[:5]:
                result += f"- [{item.get('title', 'No title')}]({item.get('url', '')})\n"
                if item.get("content"):
                    result += f"  {item['content'][:150]}...\n\n"
            
            return {"content": [{"type": "text", "text": result}]}
            
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return {"content": [{"type": "text", "text": f"Search error: {str(e)}"}]}


def get_butler_mcp_server():
    """Create and return the SDK MCP server containing all Butler tools"""
    server = create_sdk_mcp_server(
        name="butler-local-tools",
        version="1.0.0",
        tools=[generate_image, list_agents, dispatch_to_agent, web_search]
    )
    return server

