import httpx
import logging
import json
from typing import Dict, Any, Optional, AsyncIterator
from .models import (
    AgentMetadata,
    A2AMessage,
    A2AResponse,
    AgentCard,
    Message,
    Task,
    TaskState,
    JSONRPCRequest,
    JSONRPCResponse,
    create_jsonrpc_request,
    parse_jsonrpc_response,
    create_task_from_message,
)
from .google_a2a_models import (
    MessageSendParams,
    TaskQueryParams,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)

logger = logging.getLogger(__name__)


class NetworkClient:
    """
    Client for communicating with A2A agents.
    
    Supports both legacy A2A protocol and Google A2A (JSON-RPC 2.0).
    """
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        
    # ============================================================================
    # Legacy Methods (Backward Compatibility)
    # ============================================================================
        
    async def send_message(self, agent: AgentMetadata, message: A2AMessage) -> A2AResponse:
        """
        Legacy method: Send a message to an agent and await response.
        
        DEPRECATED: Use send_google_a2a_message for new implementations.
        This method is maintained for backward compatibility with sidecars.
        """
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

    # ============================================================================
    # Google A2A Methods (JSON-RPC 2.0)
    # ============================================================================
    
    async def fetch_agent_card(self, url: str) -> Optional[AgentCard]:
        """
        Fetch an AgentCard from a Google A2A compliant agent.
        
        Args:
            url: Base URL of the agent
        
        Returns:
            AgentCard if successful, None otherwise
        """
        try:
            # Try well-known URI first
            well_known_url = f"{url.rstrip('/')}/.well-known/agent.json"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(well_known_url)
                response.raise_for_status()
                
                data = response.json()
                return AgentCard(**data)
                
        except Exception as e:
            logger.error(f"Failed to fetch AgentCard from {url}: {e}")
            return None
    
    async def send_google_a2a_message(
        self,
        agent_card: AgentCard,
        message: Message,
        task_id: Optional[str] = None,
        push_notification_config: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Send a message using Google A2A protocol (message/send method).
        
        Args:
            agent_card: The AgentCard of the target agent
            message: The message to send
            task_id: Optional task ID to continue an existing task
            push_notification_config: Optional push notification configuration
        
        Returns:
            Task: The created or updated task
        """
        try:
            url = agent_card.url.rstrip('/')
            
            # Create JSON-RPC request
            params = MessageSendParams(
                task_id=task_id,
                message=message,
                push_notification_config=push_notification_config
            )
            
            request = create_jsonrpc_request(
                method="message/send",
                params=params.model_dump(mode='json', by_alias=True)
            )
            
            logger.info(f"Sending Google A2A message to {agent_card.name} at {url}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=request.model_dump(mode='json', by_alias=True, exclude_none=True),
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                data = response.json()
                rpc_response = parse_jsonrpc_response(data)
                
                if rpc_response.error:
                    raise Exception(f"JSON-RPC error: {rpc_response.error}")
                
                return Task(**rpc_response.result)
                
        except Exception as e:
            logger.error(f"Failed to send Google A2A message: {e}")
            # Return a failed task
            from .google_a2a_models import TaskStatus
            return Task(
                id=task_id or "unknown",
                context_id="unknown",
                status=TaskStatus(
                    state=TaskState.FAILED,
                    message=Message(role=MessageRole.AGENT, parts=[{"text": f"Error: {str(e)}"}])
                )
            )
    
    async def stream_google_a2a_message(
        self,
        agent_card: AgentCard,
        message: Message,
        task_id: Optional[str] = None
    ) -> AsyncIterator[Union[Task, TaskStatusUpdateEvent, TaskArtifactUpdateEvent]]:
        """
        Stream a message using Google A2A protocol (message/stream method).
        
        Args:
            agent_card: The AgentCard of the target agent
            message: The message to send
            task_id: Optional task ID to continue an existing task
        
        Yields:
            TaskStatusUpdateEvent or TaskArtifactUpdateEvent
        """
        try:
            url = agent_card.url.rstrip('/')
            
            # Create JSON-RPC request
            params = MessageSendParams(
                task_id=task_id,
                message=message
            )
            
            request = create_jsonrpc_request(
                method="message/stream",
                params=params.model_dump(mode='json', by_alias=True)
            )
            
            logger.info(f"Streaming Google A2A message to {agent_card.name} at {url}")
            
            async with httpx.AsyncClient(timeout=None) as client:  # No timeout for streaming
                async with client.stream(
                    "POST",
                    url,
                    json=request.model_dump(mode='json', by_alias=True, exclude_none=True),
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response.raise_for_status()
                    
                    # Parse SSE events
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            try:
                                event_data = json.loads(data_str)
                                
                                # Check if it's a task status update
                                if "task" in event_data:
                                    yield Task(**event_data["task"])
                                # Check if it's an artifact update
                                elif "artifact" in event_data:
                                    yield TaskArtifactUpdateEvent(**event_data)
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse SSE event: {e}")
                                
        except Exception as e:
            logger.error(f"Failed to stream Google A2A message: {e}")
            raise
    
    async def get_task(self, agent_card: AgentCard, task_id: str) -> Optional[Task]:
        """
        Get a task using Google A2A protocol (tasks/get method).
        
        Args:
            agent_card: The AgentCard of the target agent
            task_id: The task ID to query
        
        Returns:
            Task if found, None otherwise
        """
        try:
            url = agent_card.url.rstrip('/')
            
            params = TaskQueryParams(task_id=task_id)
            
            request = create_jsonrpc_request(
                method="tasks/get",
                params=params.model_dump(mode='json', by_alias=True)
            )
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=request.model_dump(mode='json', by_alias=True, exclude_none=True),
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                data = response.json()
                rpc_response = parse_jsonrpc_response(data)
                
                if rpc_response.error:
                    logger.error(f"JSON-RPC error: {rpc_response.error}")
                    return None
                
                return Task(**rpc_response.result)
                
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    async def cancel_task(self, agent_card: AgentCard, task_id: str) -> bool:
        """
        Cancel a task using Google A2A protocol (tasks/cancel method).
        
        Args:
            agent_card: The AgentCard of the target agent
            task_id: The task ID to cancel
        
        Returns:
            True if successful, False otherwise
        """
        try:
            url = agent_card.url.rstrip('/')
            
            params = TaskQueryParams(task_id=task_id)
            
            request = create_jsonrpc_request(
                method="tasks/cancel",
                params=params.model_dump(mode='json', by_alias=True)
            )
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=request.model_dump(mode='json', by_alias=True, exclude_none=True),
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                data = response.json()
                rpc_response = parse_jsonrpc_response(data)
                
                if rpc_response.error:
                    logger.error(f"JSON-RPC error: {rpc_response.error}")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
