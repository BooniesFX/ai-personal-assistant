from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator

class AgentAdapter(ABC):
    """Abstract base class for agent adapters."""
    
    @abstractmethod
    async def process_message(self, content: str, context: Dict[str, Any] = None) -> str:
        """
        Process a message and return the response.
        """
        pass
    
    @abstractmethod
    async def shutdown(self):
        """Cleanup resources."""
        pass
