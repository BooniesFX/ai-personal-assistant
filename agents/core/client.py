#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Claude Client Wrapper
Provides a simplified interface to the Anthropic Claude API with streaming and error handling.
"""

import os
import json
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
from anthropic import AsyncAnthropic
from anthropic.types import Message
from utils.config import get_config_value, get_llm_provider

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for Anthropic Claude API with streaming and error handling."""

    def __init__(self, config=None):
        """
        Initialize Claude client.

        Args:
            config: Configuration object (optional)
        """
  
        llm_provider = get_llm_provider(config)

        # Get API key from LLM_API_KEY (unified)
        api_key = get_config_value(config, 'llm', 'api_key', fallback=os.getenv('LLM_API_KEY'))

        if not api_key:
            raise ValueError(f"{llm_provider.upper()} API key not configured!")

        # Initialize async client
        self.client = AsyncAnthropic(api_key=api_key)

        # Get default model from environment or config
        self.default_model = get_config_value(config, 'llm', 'model', fallback='claude-3-5-sonnet-20241022')

        # Get default max tokens
        self.default_max_tokens = int(get_config_value(config, 'llm', 'max_tokens', fallback='4096'))

    async def create_message(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Message:
        """
        Create a message with Claude.

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (defaults to self.default_model)
            max_tokens: Maximum tokens to generate (defaults to self.default_max_tokens)
            temperature: Sampling temperature
            system: System message
            tools: List of tool definitions
            **kwargs: Additional arguments to pass to the API

        Returns:
            Message response from Claude

        Raises:
            Exception: If API call fails
        """
        try:
            params = {
                'model': model or self.default_model,
                'messages': messages,
                'max_tokens': max_tokens or self.default_max_tokens,
                'temperature': temperature,
                **kwargs
            }

            if system:
                params['system'] = system

            if tools:
                params['tools'] = tools

            response = await self.client.messages.create(**params)
            return response

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def stream_message(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream a message from Claude.

        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (defaults to self.default_model)
            max_tokens: Maximum tokens to generate (defaults to self.default_max_tokens)
            temperature: Sampling temperature
            system: System message
            tools: List of tool definitions
            **kwargs: Additional arguments to pass to the API

        Yields:
            Text chunks from Claude response

        Raises:
            Exception: If API call fails
        """
        try:
            params = {
                'model': model or self.default_model,
                'messages': messages,
                'max_tokens': max_tokens or self.default_max_tokens,
                'temperature': temperature,
                'stream': True,
                **kwargs
            }

            if system:
                params['system'] = system

            if tools:
                params['tools'] = tools

            try:
                async with self.client.messages.stream(**params) as stream:
                    async for chunk in stream.text_stream:
                        yield chunk

            except Exception as e:
                logger.error(f"Claude API streaming error: {e}")
                raise

    async def create_tool_message(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a message with tool calling.

        Args:
            messages: List of message dictionaries with role and content
            tools: List of tool definitions
            model: Model to use (defaults to self.default_model)
            max_tokens: Maximum tokens to generate (defaults to self.default_max_tokens)
            temperature: Sampling temperature
            system: System message
            **kwargs: Additional arguments to pass to the API

        Returns:
            Dictionary with response and tool calls if any

        Raises:
            Exception: If API call fails
        """
        try:
            params = {
                'model': model or self.default_model,
                'messages': messages,
                'tools': tools,
                'max_tokens': max_tokens or self.default_max_tokens,
                'temperature': temperature,
                **kwargs
            }

            if system:
                params['system'] = system

            response = await self.client.messages.create(**params)

            # Extract tool calls if present
            result = {
                'response': response,
                'tool_calls': []
            }

            if response.stop_reason == 'tool_use':
                for content in response.content:
                    if content.type == 'tool_use':
                        result['tool_calls'].append({
                            'name': content.name,
                            'input': content.input,
                            'id': content.id
                        })

            return result

        except Exception as e:
            logger.error(f"Claude API tool error: {e}")
            raise