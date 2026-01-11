#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Anthropic-to-OpenAI Proxy Server (v2.0)

Provides robust conversion between Anthropic and OpenAI API formats,
including native Support for Tool Use and Tool Results.
"""

import os
import json
import asyncio
import logging
from aiohttp import web
import httpx

logger = logging.getLogger(__name__)

# Configuration
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", ""))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", os.getenv("LLM_MODEL", "gpt-4o"))

# Model mapping (Internal names used by Claude SDK -> Your provider model)
MODEL_MAP = {
    "claude-sonnet-4-20250514": OPENAI_MODEL,
    "claude-3-7-sonnet-20250219": OPENAI_MODEL,
    "claude-3-5-sonnet-20241022": OPENAI_MODEL,
    "claude-3-opus-20240229": OPENAI_MODEL,
    "claude-3-haiku-20240307": OPENAI_MODEL,
}

def convert_anthropic_to_openai(anthropic_request: dict) -> dict:
    """
    Advanced conversion of Anthropic messages to OpenAI format.
    Handles system prompts, user/assistant turns, tool definitions, 
    tool calls, and tool results.
    """
    openai_messages = []
    
    # 1. System Prompt
    system = anthropic_request.get("system")
    if system:
        if isinstance(system, list):
            system_text = "\n".join([b.get("text", "") for b in system if b.get("type") == "text"])
        else:
            system_text = str(system)
        openai_messages.append({"role": "system", "content": system_text})
    
    # 2. Iterate through messages
    for msg in anthropic_request.get("messages", []):
        role = msg.get("role")
        content = msg.get("content")
        
        # Normalize content to list
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        
        # Prepare OpenAI message
        openai_msg = {"role": role, "content": ""}
        text_parts = []
        tool_calls = []
        
        for block in content:
            b_type = block.get("type")
            
            if b_type == "text":
                text_parts.append(block.get("text", ""))
                
            elif b_type == "tool_use":
                # Convert to OpenAI tool_calls
                tool_calls.append({
                    "id": block.get("id"),
                    "type": "function",
                    "function": {
                        "name": block.get("name"),
                        "arguments": json.dumps(block.get("input", {}))
                    }
                })
                
            elif b_type == "tool_result":
                # Tool results must be 'role: tool' messages in OpenAI
                # We stop the current message processing and insert tool message
                if text_parts:
                    openai_messages.append({"role": role, "content": "\n".join(text_parts)})
                    text_parts = []
                
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": block.get("tool_use_id"),
                    "content": str(block.get("content", ""))
                })
        
        # Build the message
        if role == "assistant" and tool_calls:
            openai_msg["tool_calls"] = tool_calls
            # If assistant has text before tool call, include it
            openai_msg["content"] = "\n".join(text_parts) if text_parts else None
            openai_messages.append(openai_msg)
        elif text_parts:
            openai_msg["content"] = "\n".join(text_parts)
            openai_messages.append(openai_msg)

    # 3. Model and Tools
    model = anthropic_request.get("model", "claude-sonnet-4-20250514")
    openai_model = MODEL_MAP.get(model, model) # Use provided model if not in map
    
    openai_request = {
        "model": openai_model,
        "messages": openai_messages,
        "max_tokens": anthropic_request.get("max_tokens", 4096),
        "temperature": anthropic_request.get("temperature", 0.7),
        "stream": False # SDK currently doesn't require proxy-level streaming
    }
    
    # 4. Global Tool Definitions
    if "tools" in anthropic_request:
        openai_tools = []
        for tool in anthropic_request["tools"]:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": tool.get("input_schema")
                }
            })
        if openai_tools:
            openai_request["tools"] = openai_tools
            
    return openai_request

def convert_openai_to_anthropic(openai_response_data: dict) -> dict:
    """Convert OpenAI chat completion response back to Anthropic message format."""
    choice = openai_response_data.get("choices", [{}])[0]
    message = choice.get("message", {})
    
    content_blocks = []
    
    # Text content
    if message.get("content"):
        content_blocks.append({
            "type": "text",
            "text": message["content"]
        })
    
    # Tool calls
    if message.get("tool_calls"):
        for tc in message["tool_calls"]:
            func = tc.get("function", {})
            try:
                args = json.loads(func.get("arguments", "{}"))
            except:
                args = {}
                
            content_blocks.append({
                "type": "tool_use",
                "id": tc.get("id"),
                "name": func.get("name"),
                "input": args
            })
            
    # Stop reason
    finish_reason = choice.get("finish_reason")
    stop_reason = "end_turn"
    if finish_reason == "tool_calls":
        stop_reason = "tool_use"
    elif finish_reason == "length":
        stop_reason = "max_tokens"
        
    return {
        "id": openai_response_data.get("id", "proxy_msg"),
        "type": "message",
        "role": "assistant",
        "content": content_blocks,
        "model": openai_response_data.get("model"),
        "stop_reason": stop_reason,
        "usage": {
            "input_tokens": openai_response_data.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": openai_response_data.get("usage", {}).get("completion_tokens", 0)
        }
    }

async def handle_messages(request):
    """Handle /v1/messages POST request."""
    try:
        data = await request.json()
        model = data.get("model", "unknown")
        logger.info(f"Proxy: Incoming request for {model}")
        
        openai_payload = convert_anthropic_to_openai(data)
        
        # Retry with backoff logic
        max_retries = 3
        async with httpx.AsyncClient(timeout=120.0) as client:
            base = OPENAI_BASE_URL.rstrip("/")
            if not base.endswith("/v1"): base = f"{base}/v1"
            url = f"{base}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            for attempt in range(max_retries):
                try:
                    resp = await client.post(url, json=openai_payload, headers=headers)
                    
                    if resp.status_code == 429:
                        wait = 2 ** attempt
                        logger.warning(f"Rate limited (429), retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                    
                    if resp.status_code != 200:
                        logger.error(f"Upstream error {resp.status_code}: {resp.text[:500]}")
                        return web.json_response({
                            "error": {"type": "api_error", "message": f"Upstream error: {resp.status_code}"}
                        }, status=resp.status_code)
                    
                    openai_resp = resp.json()
                    anthropic_resp = convert_openai_to_anthropic(openai_resp)
                    return web.json_response(anthropic_resp)
                    
                except Exception as e:
                    logger.error(f"Request failed: {e}")
                    if attempt == max_retries - 1: raise
                    await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Internal Proxy Error: {e}", exc_info=True)
        return web.json_response({
            "error": {"type": "proxy_error", "message": str(e)}
        }, status=500)

async def handle_health(request):
    return web.json_response({"status": "ok"})

def create_app():
    app = web.Application()
    app.router.add_post("/v1/messages", handle_messages)
    app.router.add_get("/health", handle_health)
    return app

async def run_proxy(host="127.0.0.1", port=4141):
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Anthropic-to-OpenAI Proxy (v2) started on http://{host}:{port}")
    return runner

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(run_proxy())
