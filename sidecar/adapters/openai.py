import logging
import os
from typing import Dict, Any, Optional
from .base import AgentAdapter
from openai import AsyncOpenAI

logger = logging.getLogger("sidecar.openai")

class OpenAIAdapter(AgentAdapter):
    """
    Adapter that proxies requests to an OpenAI-compatible API.
    Useful for wrapping other LLMs or Agents exposed via API as A2A agents.
    """
    
    def __init__(self, base_url: str, api_key: str, model: str, system_prompt: str = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.system_prompt = system_prompt
        # Simple memory: Map conversation_id -> List[Messages]
        self.memory: Dict[str, list] = {}
        
    async def process_message(self, content: str, context: Dict[str, Any] = None) -> str:
        conversation_id = context.get('conversation_id', 'default') if context else 'default'
        
        # Initialize history if needed
        if conversation_id not in self.memory:
            self.memory[conversation_id] = []
            if self.system_prompt:
                self.memory[conversation_id].append({"role": "system", "content": self.system_prompt})
        
        # Add User Message
        self.memory[conversation_id].append({"role": "user", "content": content})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.memory[conversation_id]
            )
            
            reply = response.choices[0].message.content
            
            # Add Assistant Message
            self.memory[conversation_id].append({"role": "assistant", "content": reply})
            
            return reply
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error calling upstream API: {e}"

    async def shutdown(self):
        await self.client.close()
