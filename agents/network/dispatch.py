import logging
import json
import uuid
from typing import Dict, Any, List
from agents.network.registry import AgentRegistry
from agents.network.client import NetworkClient
from agents.network.models import A2AMessage

logger = logging.getLogger(__name__)

class DispatchTool:
    """
    The 'Universal Remote' tool for the Butler.
    Allows the generic LLM to dispatch tasks to specific agents in the network.
    """
    
    def __init__(self, registry: AgentRegistry, client: NetworkClient, bot_id: str = "butler_core"):
        self.registry = registry
        self.client = client
        self.bot_id = bot_id

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "dispatch_to_agent",
            "description": "Delegate a task to a specialized agent in the network.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The ID of the agent to call (e.g. 'coding_agent')."
                    },
                    "instruction": {
                        "type": "string",
                        "description": "The detailed instruction or message for the agent."
                    },
                    "context_summary": {
                         "type": "string", 
                         "description": "Optional summary of the current conversation context to help the agent."
                    }
                },
                "required": ["agent_id", "instruction"]
            }
        }

    async def execute(self, agent_id: str, instruction: str, context_summary: str = None) -> str:
        """
        Execute the dispatch logic.
        """
        # 1. Lookup Agent
        agent = await self.registry.get_agent(agent_id)
        if not agent:
            # Fallback: Try to find by partial name map if ID is wrong?
            # For now, strict ID.
            available = [f"{a.name} ({a.id})" for a in await self.registry.list_agents()]
            return f"Error: Agent '{agent_id}' not found. Available agents: {', '.join(available)}"
        
        # 2. Construct Message
        msg = A2AMessage(
            from_agent_id=self.bot_id,
            to_agent_id=agent.id,
            conversation_id=str(uuid.uuid4()), # New conversation for this task
            content=instruction,
            context={"summary": context_summary} if context_summary else {}
        )
        
        # 3. Send
        logger.info(f"Dispatching task to {agent.name}: {instruction[:50]}...")
        response = await self.client.send_message(agent, msg)
        
        # 4. Format Result
        if response.status == "success":
            return f"Agent {agent.name} responded:\n{response.content}"
        else:
            return f"Agent {agent.name} failed: {response.content} (Error: {response.error})"
