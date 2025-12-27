from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class AgentProtocol(str, Enum):
    A2A_REST = "a2a_rest"  # Our standard sidecar protocol
    OPENAI = "openai"      # Direct OpenAI-compatible API

class AgentMetadata(BaseModel):
    """Registry entry for an agent."""
    id: str = Field(..., description="Unique persistent ID of the agent")
    name: str = Field(..., description="Human-readable name")
    description: str = Field("An external agent", description="Capabilities description")
    url: str = Field(..., description="Base URL of the agent/sidecar")
    protocol: AgentProtocol = Field(AgentProtocol.A2A_REST)
    capabilities: List[str] = Field(default_factory=list)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    status: str = "offline"

class A2AMessage(BaseModel):
    """Standard A2A Message payload."""
    from_agent_id: str
    to_agent_id: str
    conversation_id: str
    content: str
    context: Optional[Dict[str, Any]] = None  # Context passed by Butler
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class A2AResponse(BaseModel):
    """Standard response from an agent."""
    agent_id: str
    content: str
    status: str = "success"
    artifacts: List[Dict[str, Any]] = []
    error: Optional[str] = None
