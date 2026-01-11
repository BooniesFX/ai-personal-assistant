#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import AsyncIterator, Optional, List, Dict, Any

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from agents.sdk.tools import get_butler_mcp_server, init_tools
from agents.sdk.hooks import get_butler_hooks

logger = logging.getLogger(__name__)

class ButlerSDKAgent:
    """
    High-level wrapper around ClaudeSDKClient for the Butler Assistant.
    This replaces the old AgentCore logic.
    """
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.options = None
        
        # Initialize tool clients (like ModelScope)
        init_tools(config)
        
        # Initialize hooks (Memory and Identity)
        from agents.sdk.hooks import init_hooks
        init_hooks(config)
    
    def _build_options(self, user_id: str) -> ClaudeAgentOptions:
        """Create configuration options for the SDK client"""
        from agents.sdk.llm_provider import get_llm_env_config
        
        # 1. Get our local MCP server (in-process, no subprocess needed)
        local_server = get_butler_mcp_server()
        
        mcp_servers = {
            "butler": local_server
        }
        
        # Note: External MCP servers like Tavily need specific format
        # For now, we only use the in-process butler tools
        # Tavily can be added later with correct mcp-remote configuration
        
        # 2. Define allowed tools
        allowed_tools = [
            "mcp__butler__generate_image",
            "mcp__butler__list_agents",
            "mcp__butler__dispatch_to_agent",
            "mcp__butler__web_search"
        ]
            
        # 3. Global system prompt
        system_prompt = self.config.get('agent', {}).get('system_prompt', "You are Butler, a helpful AI assistant.")
        
        # 4. Build options
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            mcp_servers=mcp_servers,
            allowed_tools=allowed_tools,
            # hooks=get_butler_hooks(user_id, self.config),  # Hooks need proper SDK format
            env=get_llm_env_config(self.config),
            model=self.config.get('llm', {}).get('model', "claude-sonnet-4-20250514"),
        )
        return options

    async def process_message(self, user_id: str, prompt: str) -> AsyncIterator[Any]:
        """Process a message and yield response messages/blocks"""
        options = self._build_options(user_id)
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                yield message

    async def run_one_shot(self, user_id: str, prompt: str) -> str:
        """Helper to get a full text response in one go (for simple adapters)"""
        full_text = ""
        async for msg in self.process_message(user_id, prompt):
            # SDK messages have different formats, we'll need to parse them
            # This is a placeholder for actual block extraction
            if hasattr(msg, 'content'):
                for block in msg.content:
                    if hasattr(block, 'text'):
                        full_text += block.text
        return full_text
