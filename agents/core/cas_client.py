import os
import json
import logging
from typing import Dict, List, Optional, AsyncGenerator
from anthropic.types import Message
from anthropic.types.message import ContentBlock
from .llm_adapter import LLMClient

logger = logging.getLogger(__name__)

class CASClient(LLMClient):
    """Client for interacting with CAS (Claude Agent Server) compatible endpoints."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

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
        # Implementation following https://github.com/foreveryh/claude-agent-kit
        # Convert messages to CAS format
        cas_messages = []
        for msg in messages:
            content_blocks = []
            
            if msg['role'] == 'user':
                # Split into text and tool_use if needed
                # For simplicity, just add as text
                content_blocks.append({
                    'type': 'text',
                    'text': msg['content']
                })
            elif msg['role'] == 'assistant':
                # Handle tool responses if present
                content_blocks.append({
                    'type': 'text',
                    'text': msg['content']
                })

        # Prepare request payload
        payload = {
            'model': model or 'claude-3-5-sonnet-20241022',
            'messages': cas_messages,
            'max_tokens': max_tokens or 1024,
            'temperature': temperature
        }
        
        if system:
            payload['system'] = system
        
        if tools:
            payload['tools'] = tools

        # Send request
        # Implementation using aiohttp would go here
        # For now, just simulate a response
        return Message(
            id="msg_123",
            type="message",
            role="assistant",
            content=[
                ContentBlock(
                    type="text",
                    text="This is a simulated CAS response."
                )
            ],
            model="claude-3-5-sonnet-20241022",
            stop_reason="end_turn",
            stop_sequence=None,
            usage={
                "input_tokens": 100,
                "output_tokens": 50
            }
        )

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
        # Stream implementation following CAS protocol
        payload = {
            'model': model or 'claude-3-5-sonnet-20241022',
            'messages': messages,
            'max_tokens': max_tokens or 1024,
            'temperature': temperature,
            'stream': True
        }
        
        if system:
            payload['system'] = system
        
        if tools:
            payload['tools'] = tools

        # In a real implementation, this would use aiohttp
        # Here we're simulating the stream
        response_chunks = [
            '{"type":"message_start","message":{"id":"msg_123","type":"message","role":"assistant"}}',
            '{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
            '{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}',
            '{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" world"}}',
            '{"type":"content_block_stop","index":0}',
            '{"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null}}',
            '{"type":"message_stop"}'
        ]
        
        for chunk in response_chunks:
            yield chunk
            # In real implementation, would add delays to simulate streaming