import httpx
import logging
import json
from typing import Dict, Any, Optional
from .models import AgentMetadata, A2AMessage, A2AResponse

logger = logging.getLogger(__name__)

class NetworkClient:
    """Client for communicating with A2A agents."""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        
    async def send_message(self, agent: AgentMetadata, message: A2AMessage) -> A2AResponse:
        """Send a message to an agent and await response."""
        try:
            url = f"{agent.url.rstrip('/')}/agent/message"
            
            payload = message.model_dump(mode='json')
            
            logger.info(f"Adding task to queue for {agent.name} ({agent.url})")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                return A2AResponse(**data)
                
        except httpx.TimeoutException:
            logger.error(f"Timeout communicating with agent {agent.name}")
            return A2AResponse(
                agent_id=agent.id,
                content="Error: Agent timed out.",
                status="error",
                error="timeout"
            )
        except Exception as e:
            logger.error(f"Error communicating with agent {agent.name}: {e}")
            return A2AResponse(
                agent_id=agent.id,
                content=f"Error: Connection failed - {str(e)}",
                status="error",
                error=str(e)
            )
    
    async def check_health(self, agent: AgentMetadata) -> bool:
        """Check if agent is online."""
        try:
            url = f"{agent.url.rstrip('/')}/health"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                return resp.status_code == 200
        except:
            return False
