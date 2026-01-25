import logging
import asyncio
from typing import Dict, List, Optional, Union
from datetime import datetime
from .models import AgentMetadata, AgentProtocol, AgentCard
from .client import NetworkClient

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Manages the roster of known agents.
    
    Supports both legacy AgentMetadata and Google A2A AgentCard.
    Automatically converts between formats as needed.
    """
    
    def __init__(self, network_client: Optional[NetworkClient] = None):
        self._agents: Dict[str, AgentMetadata] = {}  # Legacy format for compatibility
        self._agent_cards: Dict[str, AgentCard] = {}  # Google A2A format
        self._lock = asyncio.Lock()
        self._network_client = network_client or NetworkClient()
    
    async def register_agent(self, agent: Union[AgentMetadata, AgentCard]):
        """
        Register or update an agent.
        
        Args:
            agent: Either legacy AgentMetadata or Google A2A AgentCard
        """
        async with self._lock:
            if isinstance(agent, AgentCard):
                # Handle Google A2A AgentCard
                agent_id = agent.name.lower().replace(" ", "-")
                self._agent_cards[agent_id] = agent
                
                # Also store as legacy metadata for compatibility
                metadata = AgentMetadata.from_agent_card(agent, status="online")
                self._agents[agent_id] = metadata
                
                logger.info(f"Registered Google A2A agent: {agent.name} ({agent_id})")
                
            else:
                # Handle legacy AgentMetadata
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
        """
        Get an agent by ID (legacy format).
        
        Args:
            agent_id: The agent ID
        
        Returns:
            AgentMetadata if found, None otherwise
        """
        return self._agents.get(agent_id)
    
    async def get_agent_card(self, agent_id: str) -> Optional[AgentCard]:
        """
        Get an AgentCard by ID (Google A2A format).
        
        Args:
            agent_id: The agent ID
        
        Returns:
            AgentCard if found, None otherwise
        """
        # Try direct lookup
        if agent_id in self._agent_cards:
            return self._agent_cards[agent_id]
        
        # Try to convert from legacy metadata
        if agent_id in self._agents:
            return self._agents[agent_id].to_agent_card()
        
        return None
    
    async def list_agents(self) -> List[AgentMetadata]:
        """
        List all agents (legacy format).
        
        Returns:
            List of AgentMetadata
        """
        return list(self._agents.values())
    
    async def list_agent_cards(self) -> List[AgentCard]:
        """
        List all agents (Google A2A format).
        
        Returns:
            List of AgentCard
        """
        return list(self._agent_cards.values())
    
    async def remove_agent(self, agent_id: str):
        """
        Remove an agent from the registry.
        
        Args:
            agent_id: The agent ID to remove
        """
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
            if agent_id in self._agent_cards:
                del self._agent_cards[agent_id]
            logger.info(f"Removed agent: {agent_id}")
    
    async def discover_agent(self, url: str) -> Optional[AgentCard]:
        """
        Discover an agent by fetching its AgentCard.
        
        Args:
            url: The base URL of the agent
        
        Returns:
            AgentCard if successful, None otherwise
        """
        try:
            agent_card = await self._network_client.fetch_agent_card(url)
            if agent_card:
                await self.register_agent(agent_card)
                return agent_card
        except Exception as e:
            logger.error(f"Failed to discover agent at {url}: {e}")
        
        return None
    
    def load_static_config(self, config_list: List[Dict]):
        """
        Load agents from a static config list (e.g. from yaml).
        
        Supports both legacy and Google A2A formats.
        
        Args:
            config_list: List of agent configurations
        """
        for item in config_list:
            try:
                # Check if it's a Google A2A format (has protocolVersion)
                if 'protocolVersion' in item:
                    agent_card = AgentCard(**item)
                    self._agent_cards[agent_card.name.lower().replace(" ", "-")] = agent_card
                    # Also create legacy metadata
                    metadata = AgentMetadata.from_agent_card(agent_card)
                    self._agents[metadata.id] = metadata
                    logger.info(f"Loaded Google A2A agent: {agent_card.name}")
                else:
                    # Legacy format
                    agent = AgentMetadata(
                        id=item['id'],
                        name=item['name'],
                        description=item.get('description', ''),
                        url=item['url'],
                        protocol=item.get('protocol', AgentProtocol.GOOGLE_A2A),
                        capabilities=item.get('capabilities', [])
                    )
                    self._agents[agent.id] = agent
                    logger.info(f"Loaded static agent: {agent.name}")
            except Exception as e:
                logger.error(f"Failed to load static agent config: {e}")
