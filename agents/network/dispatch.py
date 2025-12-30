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
            "description": (
                "Delegate a task to another specialized agent in the Butler network. "
                "Use this tool when the user asks to communicate with, ask, or delegate a task to a specific agent. "
                "For example: 'ask the Echo Agent to...', 'tell the Coding Agent to...', 'have the Local Agent do...'. "
                "The agent_id can be found from the agent's name - try the format 'agent_XXXXXXXX' or the exact ID. "
                "If unsure of the agent_id, you can try with a descriptive ID and the tool will list available agents if not found."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The ID of the agent to call. Common formats: 'agent_xxxxxxxx' or a descriptive name. If wrong, the error will list available agents."
                    },
                    "instruction": {
                        "type": "string",
                        "description": "The detailed instruction or message to send to the agent."
                    },
                    "context_summary": {
                         "type": "string", 
                         "description": "Optional summary of the current conversation context to help the agent."
                    }
                },
                "required": ["agent_id", "instruction"]
            }
        }

    async def execute(self, tool_input: Dict[str, Any], update: Any = None, context: Any = None) -> str:
        """
        Execute the dispatch logic.
        
        Args:
            tool_input: Dict with 'agent_id', 'instruction', and optional 'context_summary'
            update: Platform context (unused)
            context: Additional context (unused)
        """
        agent_id = tool_input.get('agent_id')
        instruction = tool_input.get('instruction')
        context_summary = tool_input.get('context_summary')
        
        if not agent_id or not instruction:
            return "Error: 'agent_id' and 'instruction' are required fields."
        
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


class ListAgentsTool:
    """
    Tool to list all currently registered agents in the Butler network.
    Allows the LLM to discover available agents before dispatching tasks.
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "list_agents",
            "description": (
                "List all currently registered and online agents in the Butler network. "
                "Use this tool when the user asks about available agents, what agents are online, "
                "or wants to know which agents they can communicate with. "
                "Returns a list of agents with their IDs, names, capabilities, and status."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    async def execute(self, tool_input: Dict[str, Any], update: Any = None, context: Any = None) -> str:
        """
        Execute the list agents logic.
        """
        agents = await self.registry.list_agents()
        
        if not agents:
            return "No agents are currently registered in the network."
        
        result_lines = [f"📋 **Currently Registered Agents ({len(agents)} online):**\n"]
        
        for agent in agents:
            result_lines.append(f"### {agent.name}")
            result_lines.append(f"- **ID**: `{agent.id}`")
            result_lines.append(f"- **URL**: {agent.url}")
            result_lines.append(f"- **Protocol**: {agent.protocol}")
            if agent.capabilities:
                result_lines.append(f"- **Capabilities**: {', '.join(agent.capabilities)}")
            result_lines.append("")
        
        result_lines.append("Use `dispatch_to_agent` with the agent's ID to send a task to any of these agents.")
        
        return "\n".join(result_lines)
