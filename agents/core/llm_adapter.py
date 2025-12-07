from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator
from anthropic.types import Message


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
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
        Create a message with the LLM.
        """
        pass

    @abstractmethod
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
        """
        pass