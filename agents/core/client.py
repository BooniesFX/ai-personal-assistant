#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Claude Client Wrapper
Provides a simplified interface to LLM APIs (Anthropic or OpenAI-compatible).
"""

import os
import json
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
from utils.config import get_config_value, get_llm_provider

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for LLM API with tool support."""

    def __init__(self, config=None):
        """
        Initialize LLM client.

        Args:
            config: Configuration object (optional)
        """
        self.config = config
        self.llm_provider = get_llm_provider(config)

        # Get API key from LLM_API_KEY (unified)
        self.api_key = get_config_value(config, 'llm', 'api_key', fallback=os.getenv('LLM_API_KEY'))

        if not self.api_key:
            raise ValueError(f"{self.llm_provider.upper()} API key not configured!")

        # Get base URL
        self.base_url = get_config_value(config, 'llm', 'base_url')

        # Get default model from environment or config
        self.default_model = get_config_value(config, 'llm', 'model', fallback='claude-3-5-sonnet-20241022')

        # Get default max tokens
        self.default_max_tokens = int(get_config_value(config, 'llm', 'max_tokens', fallback='4096'))

        # Initialize appropriate client based on provider
        if self.llm_provider in ('cas', 'openai'):
            self._init_openai_client()
        else:
            self._init_anthropic_client()

    def _init_openai_client(self):
        """Initialize OpenAI-compatible client."""
        from openai import AsyncOpenAI
        
        # Ensure base_url includes /v1 for OpenAI SDK
        base_url = self.base_url
        if base_url:
            base_url = base_url.rstrip('/')
            if not base_url.endswith('/v1'):
                base_url = f"{base_url}/v1"
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url if base_url else None
        )
        self.client_type = 'openai'
        logger.info(f"Initialized OpenAI-compatible client with base_url: {base_url}")

    def _init_anthropic_client(self):
        """Initialize Anthropic client."""
        from anthropic import AsyncAnthropic
        if self.base_url:
            self.client = AsyncAnthropic(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)
        self.client_type = 'anthropic'
        logger.info("Initialized Anthropic client")

    async def create_message(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ):
        """
        Create a message with the LLM.

        Returns:
            Response object (format depends on client type)
        """
        if self.client_type == 'openai':
            return await self._create_message_openai(
                messages, model, max_tokens, temperature, system, tools, **kwargs
            )
        else:
            return await self._create_message_anthropic(
                messages, model, max_tokens, temperature, system, tools, **kwargs
            )

    async def _create_message_openai(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ):
        """Create message using OpenAI-compatible API."""
        # Prepare messages with system prompt
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        # Convert messages to OpenAI format
        for msg in messages:
            role = msg.get('role')
            content = msg.get('content')

            if isinstance(content, list):
                # Handle complex content (tool results, etc.)
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        elif item.get('type') == 'tool_result':
                            text_parts.append(f"[Tool Result]: {item.get('content', '')}")
                    else:
                        text_parts.append(str(item))
                content = '\n'.join(text_parts)

            openai_messages.append({"role": role, "content": content})

        params = {
            'model': model or self.default_model,
            'messages': openai_messages,
            'max_tokens': max_tokens or self.default_max_tokens,
            'temperature': temperature,
        }

        # Convert Anthropic-style tools to OpenAI format
        if tools:
            openai_tools = []
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.get('name'),
                        "description": tool.get('description'),
                        "parameters": tool.get('input_schema', {})
                    }
                })
            params['tools'] = openai_tools
            params['tool_choice'] = 'auto'  # Let model decide when to use tools
            logger.info(f"Tools being sent to API: {[t['function']['name'] for t in openai_tools]}")
            logger.debug(f"Full tools payload: {openai_tools}")

        try:
            logger.info(f"Sending request to OpenAI-compatible API with model: {params['model']}")
            logger.debug(f"Messages: {openai_messages[-1] if openai_messages else 'empty'}")  # Log last message
            response = await self.client.chat.completions.create(**params)
            
            # Debug log the response
            if response.choices:
                choice = response.choices[0]
                logger.info(f"Response finish_reason: {choice.finish_reason}")
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    logger.info(f"Tool calls in response: {[tc.function.name for tc in choice.message.tool_calls]}")
                else:
                    logger.info("No tool_calls in response")
                    
            # Wrap response in a compatible format
            return OpenAIResponseWrapper(response)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def _create_message_anthropic(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ):
        """Create message using Anthropic API."""
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
            logger.error(f"Anthropic API error: {e}")
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

        Returns:
            Dictionary with response and tool calls if any
        """
        if self.client_type == 'openai':
            return await self._create_tool_message_openai(
                messages, tools, model, max_tokens, temperature, system, **kwargs
            )
        else:
            return await self._create_tool_message_anthropic(
                messages, tools, model, max_tokens, temperature, system, **kwargs
            )

    async def _create_tool_message_openai(
        self,
        messages: List[Dict],
        tools: List[Dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create tool message using OpenAI-compatible API."""
        response = await self._create_message_openai(
            messages, model, max_tokens, temperature, system, tools, **kwargs
        )

        result = {
            'response': response,
            'tool_calls': []
        }

        # Check for tool calls in OpenAI format
        if response.content and len(response.content) > 0:
            first_choice = response._raw_response.choices[0]
            if hasattr(first_choice.message, 'tool_calls') and first_choice.message.tool_calls:
                for tool_call in first_choice.message.tool_calls:
                    result['tool_calls'].append({
                        'name': tool_call.function.name,
                        'input': json.loads(tool_call.function.arguments),
                        'id': tool_call.id
                    })

        return result

    async def _create_tool_message_anthropic(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create tool message using Anthropic API."""
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
            logger.error(f"Anthropic API tool error: {e}")
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
        Stream a message from the LLM.

        Yields:
            Text chunks from response
        """
        if self.client_type == 'openai':
            async for chunk in self._stream_message_openai(
                messages, model, max_tokens, temperature, system, tools, **kwargs
            ):
                yield chunk
        else:
            async for chunk in self._stream_message_anthropic(
                messages, model, max_tokens, temperature, system, tools, **kwargs
            ):
                yield chunk

    async def _stream_message_openai(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream message using OpenAI-compatible API."""
        # Prepare messages with system prompt
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg.get('role')
            content = msg.get('content')
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                content = '\n'.join(text_parts)
            openai_messages.append({"role": role, "content": content})

        params = {
            'model': model or self.default_model,
            'messages': openai_messages,
            'max_tokens': max_tokens or self.default_max_tokens,
            'temperature': temperature,
            'stream': True
        }

        try:
            stream = await self.client.chat.completions.create(**params)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI API streaming error: {e}")
            raise

    async def _stream_message_anthropic(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream message using Anthropic API."""
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

            try:
                async with self.client.messages.stream(**params) as stream:
                    async for chunk in stream.text_stream:
                        yield chunk

            except Exception as e:
                logger.error(f"Anthropic API streaming error: {e}")
                raise

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class OpenAIResponseWrapper:
    """Wrapper to make OpenAI responses compatible with Anthropic-style access."""

    def __init__(self, response):
        self._raw_response = response
        self.content = []

        # Extract content from OpenAI response
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if message.content:
                self.content.append(TextBlock(message.content))

            # Handle tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    self.content.append(ToolUseBlock(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        input=json.loads(tool_call.function.arguments)
                    ))

        self.stop_reason = 'tool_use' if (
            response.choices and
            response.choices[0].finish_reason == 'tool_calls'
        ) else 'end_turn'


class TextBlock:
    """Represents a text content block."""

    def __init__(self, text: str):
        self.type = 'text'
        self.text = text


class ToolUseBlock:
    """Represents a tool use content block."""

    def __init__(self, id: str, name: str, input: dict):
        self.type = 'tool_use'
        self.id = id
        self.name = name
        self.input = input