import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from .models import AgentMetadata, AgentProtocol

logger = logging.getLogger(__name__)

class AgentRegistry:
    """
    Manages the roster of known agents.
    Supports both static configuration and dynamic registration.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentMetadata] = {}
        self._lock = asyncio.Lock()
    
    async def register_agent(self, agent: AgentMetadata):
        """Register or update an agent."""
        async with self._lock:
            agent.last_seen = datetime.utcnow()
            agent.status = "online"
            
            if agent.id in self._agents:
                # Update existing
                current = self._agents[agent.id]
                current.url = agent.url
                current.name = agent.name
                current.last_seen = agent.last_seen
                current.status = "online"
                logger.info(f"Updated agent registration: {agent.name} ({agent.id})")
            else:
                # Add new
                self._agents[agent.id] = agent
                logger.info(f"Registered new agent: {agent.name} ({agent.id})")
    
    async def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        return self._agents.get(agent_id)
        
    async def list_agents(self) -> List[AgentMetadata]:
        return list(self._agents.values())
    
    async def remove_agent(self, agent_id: str):
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.info(f"Removed agent: {agent_id}")

    def load_static_config(self, config_list: List[Dict]):
        """Load agents from a static config list (e.g. from yaml)."""
        for item in config_list:
            try:
                agent = AgentMetadata(
                    id=item['id'],
                    name=item['name'],
                    description=item.get('description', ''),
                    url=item['url'],
                    protocol=item.get('protocol', AgentProtocol.A2A_REST),
                    capabilities=item.get('capabilities', [])
                )
                # We do this synchronously as it's usually at startup
                self._agents[agent.id] = agent
                logger.info(f"Loaded static agent: {agent.name}")
            except Exception as e:
                logger.error(f"Failed to load static agent config: {e}")
