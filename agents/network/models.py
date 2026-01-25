from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime
import logging

# Import Google A2A models
from .google_a2a_models import (
    AgentCard,
    AgentSkill,
    AgentProvider,
    AgentCapabilities,
    Message,
    MessageRole,
    TextPart,
    DataPart,
    Task,
    TaskState,
    TaskStatus,
    JSONRPCRequest,
    JSONRPCResponse,
    generate_agent_id,
    generate_task_id,
    generate_context_id,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Legacy Models (Backward Compatibility)
# ============================================================================

class AgentProtocol(str, Enum):
    """Legacy protocol enum for backward compatibility."""
    A2A_REST = "a2a_rest"  # Our standard sidecar protocol (deprecated, use Google A2A)
    OPENAI = "openai"      # Direct OpenAI-compatible API
    GOOGLE_A2A = "google_a2a"  # Google A2A Protocol (new default)


class AgentMetadata(BaseModel):
    """
    Legacy registry entry for an agent.
    
    DEPRECATED: Use AgentCard for new implementations.
    This class is maintained for backward compatibility.
    """
    id: str = Field(..., description="Unique persistent ID of the agent")
    name: str = Field(..., description="Human-readable name")
    description: str = Field("An external agent", description="Capabilities description")
    url: str = Field(..., description="Base URL of the agent/sidecar")
    protocol: AgentProtocol = Field(AgentProtocol.GOOGLE_A2A)
    capabilities: List[str] = Field(default_factory=list)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    status: str = "offline"

    def to_agent_card(self) -> AgentCard:
        """
        Convert legacy AgentMetadata to Google A2A AgentCard.
        
        Returns:
            AgentCard: A Google A2A compliant AgentCard
        """
        # Convert capabilities list to skills
        skills = [
            AgentSkill(
                id=cap.lower().replace(" ", "-"),
                name=cap.title(),
                description=f"Capability: {cap}",
                tags=[cap.lower()]
            )
            for cap in self.capabilities
        ]
        
        # If no capabilities, add a generic skill
        if not skills:
            skills.append(
                AgentSkill(
                    id="generic",
                    name="Generic Capability",
                    description="General agent capabilities",
                    tags=["general"]
                )
            )
        
        return AgentCard(
            protocol_version="0.2.5",
            name=self.name,
            description=self.description,
            url=self.url,
            version="1.0.0",
            capabilities=AgentCapabilities(
                streaming=True,
                push_notifications=True
            ),
            default_input_modes=["application/json", "text/plain"],
            default_output_modes=["application/json", "text/plain"],
            skills=skills,
            supports_authenticated_extended_card=True
        )

    @classmethod
    def from_agent_card(cls, card: AgentCard, status: str = "online") -> "AgentMetadata":
        """
        Create AgentMetadata from Google A2A AgentCard.
        
        Args:
            card: Google A2A AgentCard
            status: Agent status (default: "online")
        
        Returns:
            AgentMetadata: Legacy AgentMetadata instance
        """
        # Extract capabilities from skills
        capabilities = []
        for skill in card.skills:
            capabilities.extend(skill.tags)
            capabilities.append(skill.name)
        
        return cls(
            id=generate_agent_id(card.name.lower().replace(" ", "-")),
            name=card.name,
            description=card.description,
            url=card.url,
            protocol=AgentProtocol.GOOGLE_A2A,
            capabilities=list(set(capabilities)),  # Remove duplicates
            status=status
        )


class A2AMessage(BaseModel):
    """
    Legacy A2A Message payload.
    
    DEPRECATED: Use Google A2A Message with JSON-RPC for new implementations.
    This class is maintained for backward compatibility.
    """
    from_agent_id: str
    to_agent_id: str
    conversation_id: str
    content: str
    context: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def to_google_a2a_message(self) -> Message:
        """
        Convert legacy A2AMessage to Google A2A Message.
        
        Returns:
            Message: A Google A2A compliant Message
        """
        parts = [TextPart(text=self.content)]
        
        # Add context as DataPart if present
        if self.context:
            parts.append(DataPart(data=self.context))
        
        return Message(
            role=MessageRole.USER,
            parts=parts,
            message_id=f"msg_{self.conversation_id}"
        )

    @classmethod
    def from_google_a2a_message(cls, msg: Message, from_agent_id: str, to_agent_id: str, conversation_id: str) -> "A2AMessage":
        """
        Create legacy A2AMessage from Google A2A Message.
        
        Args:
            msg: Google A2A Message
            from_agent_id: Sender agent ID
            to_agent_id: Receiver agent ID
            conversation_id: Conversation ID
        
        Returns:
            A2AMessage: Legacy A2AMessage instance
        """
        # Extract content from parts
        content = ""
        context = {}
        
        for part in msg.parts:
            if isinstance(part, TextPart):
                content += part.text
            elif isinstance(part, DataPart):
                context.update(part.data)
        
        return cls(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            conversation_id=conversation_id,
            content=content,
            context=context if context else None
        )


class A2AResponse(BaseModel):
    """
    Legacy A2A response from an agent.
    
    DEPRECATED: Use Google A2A Task and JSON-RPC Response for new implementations.
    This class is maintained for backward compatibility.
    """
    agent_id: str
    content: str
    status: str = "success"
    artifacts: List[Dict[str, Any]] = []
    error: Optional[str] = None

    @classmethod
    def from_google_a2a_task(cls, task: Task, agent_id: str) -> "A2AResponse":
        """
        Create legacy A2AResponse from Google A2A Task.
        
        Args:
            task: Google A2A Task
            agent_id: Agent ID
        
        Returns:
            A2AResponse: Legacy A2AResponse instance
        """
        # Extract content from task status message
        content = ""
        if task.status.message:
            for part in task.status.message.parts:
                if isinstance(part, TextPart):
                    content += part.text
        
        # Determine status
        status = "success"
        if task.status.state == TaskState.FAILED:
            status = "error"
        elif task.status.state == TaskState.CANCELED:
            status = "canceled"
        elif task.status.state == TaskState.REJECTED:
            status = "rejected"
        
        # Extract error message if failed
        error = None
        if task.status.state == TaskState.FAILED and task.status.message:
            error = content
            content = "Task failed"
        
        return cls(
            agent_id=agent_id,
            content=content,
            status=status,
            artifacts=task.artifacts,
            error=error
        )


# ============================================================================
# Google A2A Convenience Functions
# ============================================================================

def create_jsonrpc_request(method: str, params: Optional[Dict[str, Any]] = None, request_id: Optional[Union[str, int]] = None) -> JSONRPCRequest:
    """
    Create a JSON-RPC 2.0 request.
    
    Args:
        method: Method name to invoke
        params: Method parameters
        request_id: Request identifier (auto-generated if not provided)
    
    Returns:
        JSONRPCRequest: A JSON-RPC 2.0 request
    """
    if request_id is None:
        request_id = f"req_{generate_task_id()}"
    
    return JSONRPCRequest(
        method=method,
        params=params or {},
        id=request_id
    )


def parse_jsonrpc_response(data: Dict[str, Any]) -> JSONRPCResponse:
    """
    Parse a JSON-RPC 2.0 response.
    
    Args:
        data: Raw JSON-RPC response data
    
    Returns:
        JSONRPCResponse: Parsed JSON-RPC response
    """
    return JSONRPCResponse(**data)


def create_task_from_message(message: Message) -> Task:
    """
    Create a new Task from a Message.
    
    Args:
        message: The initial message for the task
    
    Returns:
        Task: A new Task in 'submitted' state
    """
    from .google_a2a_models import TaskStatus
    
    return Task(
        id=generate_task_id(),
        context_id=generate_context_id(),
        status=TaskStatus(
            state=TaskState.SUBMITTED,
            message=message
        )
    )
