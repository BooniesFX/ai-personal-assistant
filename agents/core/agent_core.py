#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Agent Core
Central agent that handles all platforms through transport adapters.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    """Supported platforms."""
    TELEGRAM = "telegram"
    WEB = "web"
    SLACK = "slack"
    WECHAT = "wechat"


@dataclass
class Message:
    """Unified message format across all platforms."""
    user_id: str
    platform: Platform
    content: str
    attachments: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    """Unified response format."""
    content: str
    tool_calls: List[Dict] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentCore:
    """
    Unified Agent Core.
    
    Manages all shared components and provides a unified interface
    for all transport adapters (Telegram, Web, Slack, etc.)
    """
    
    def __init__(self, config=None):
        """
        Initialize Agent Core.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self._initialized = False
        self._transports: Dict[Platform, Any] = {}
        
        # Will be initialized in async init
        self.session_manager = None
        self.memory_store = None
        self.tool_registry = None
        self.llm_client = None
        self.plugin_manager = None
    
    async def initialize(self):
        """Initialize all components (async)."""
        if self._initialized:
            return
        
        from agents.memory.short_term import ShortTermMemory
        from agents.memory.long_term import LongTermMemory
        from agents.memory.summarizer import MemorySummarizer
        from agents.tools.registry import ToolRegistry
        from agents.core.client import ClaudeClient
        from bot.plugin_manager import PluginManager
        from utils.config import load_config
        from agents.identity.manager import UserIdentityManager
        from agents.tools.mcp_client import MCPClientManager, MCPServerConfig
        from agents.skills.manager import SkillManager
        
        # Load config if not provided
        if self.config is None:
            self.config = load_config()
        
        # Initialize core components
        self.llm_client = ClaudeClient(self.config)
        self.mcp_client_manager = MCPClientManager()
        self.skill_manager = SkillManager()
        
        # Identity Manager
        self.identity_manager = UserIdentityManager()
        
        # Tools
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_skill_manager(self.skill_manager)
        
        # Register Tavily MCP (Search)
        # TODO: Move to config file
        # Check if Tavily API Key is present in env or config, otherwise use default for demo if needed, 
        # but here we hardcode as per previous step for now.
        
        # Connect to Tavily MCP via mcp-remote bridge
        # This allows connecting to the remote SSE server via stdio
        tavily_url = os.getenv("TAVILY_MCP_URL", "")
        if tavily_url:
            await self.mcp_client_manager.connect_server("tavily", MCPServerConfig(
                name="tavily",
                transport="stdio",
                command="npx",
                args=["-y", "mcp-remote", tavily_url]
            ))
            logger.info("Tavily MCP configured via mcp-remote bridge")
        
        await self.tool_registry.register_mcp_source(self.mcp_client_manager)
        
        self.identity_manager = UserIdentityManager()
        
        # Initialize dual memory system
        self.short_term_memory = ShortTermMemory(window_size=5)
        self.long_term_memory = LongTermMemory("data/long_term_memory.json")
        self.summarizer = MemorySummarizer(self.llm_client)
        
        logger.info("Dual memory system initialized (short-term: 5 turns, long-term: persistent)")
        
        # --- Butler / Network Initialization ---
        from agents.network.registry import AgentRegistry
        from agents.network.client import NetworkClient
        from agents.network.dispatch import DispatchTool, ListAgentsTool
        
        self.agent_registry = AgentRegistry()
        self.network_client = NetworkClient()
        self.dispatch_tool = DispatchTool(self.agent_registry, self.network_client)
        self.list_agents_tool = ListAgentsTool(self.agent_registry)
        
        # Register Network Tools
        dispatch_def = self.dispatch_tool.get_tool_definition()
        self.tool_registry.register_tool(dispatch_def, self.dispatch_tool.execute)
        
        list_agents_def = self.list_agents_tool.get_tool_definition()
        self.tool_registry.register_tool(list_agents_def, self.list_agents_tool.execute)
        
        logger.info("Butler Network initialized: DispatchTool and ListAgentsTool registered")
        # ---------------------------------------

        # Load plugins as tools
        self.plugin_manager = PluginManager(self.config, logger)
        await self.plugin_manager.load_plugins()
        
        # Inject identity manager into identity plugin
        identity_plugin = self.plugin_manager.get_plugin("identity")
        if identity_plugin:
            identity_plugin.identity_manager = self.identity_manager
            logger.info("Injected identity manager into identity plugin")
        
        for plugin in self.plugin_manager.plugins:
            if plugin.enabled and hasattr(plugin, 'get_tool_definition'):
                try:
                    tool_def = plugin.get_tool_definition()
                    if tool_def:
                        self.tool_registry.register_tool(tool_def, plugin.handle_tool_call)
                        logger.info(f"Registered tool: {tool_def.get('name')}")
                except Exception as e:
                    logger.error(f"Error registering tool from {plugin.name}: {e}")
        
        logger.info(f"AgentCore initialized with {len(self.tool_registry.list_tools())} tools")
        self._initialized = True

    async def shutdown(self):
        """Shutdown all components and clean up resources."""
        if not self._initialized:
            return
            
        logger.info("Shutting down AgentCore...")
        
        # Shutdown MCP sessions
        if hasattr(self, 'mcp_client_manager') and self.mcp_client_manager:
            await self.mcp_client_manager.shutdown()
            
        # Shutdown plugins
        if self.plugin_manager:
            await self.plugin_manager.shutdown()
            
        self._initialized = False
        logger.info("AgentCore shutdown complete")

    
    def register_transport(self, platform: Platform, adapter):
        """
        Register a transport adapter.
        
        Args:
            platform: Platform identifier
            adapter: Transport adapter instance
        """
        self._transports[platform] = adapter
        logger.info(f"Registered transport: {platform.value}")
    
    async def process_message(
        self, 
        message: Message,
        platform_context: Any = None,
        status_callback: Callable[[str], Any] = None
    ) -> Response:
        """
        Process a message from any platform.
        
        Args:
            message: Unified message object
            platform_context: Platform-specific context (e.g., TG Update)
            
        Returns:
            Response object
        """
        if not self._initialized:
            await self.initialize()
        
        user_id = message.user_id
        
        # Unified Identity Resolution
        # Check if user_id is already an email (from web login)
        if '@' in user_id:
            # Already using email as identity
            email = user_id
            logger.info(f"Using email identity directly: {email}")
        else:
            # Check if this platform ID is bound to an email
            email = self.identity_manager.get_email(message.platform.value, user_id)
            if email:
                logger.info(f"Resolved identity {message.platform.value}:{user_id} -> {email}")
                user_id = email
            
        # Use unified session for email-identified users
        session_id = "unified_session" if email else f"{message.platform.value}_{message.user_id}"
        
        # Add to short-term memory
        self.short_term_memory.add_turn(
            user_id, session_id,
            role="user",
            content=message.content
        )
        
        # Check if we should trigger summarization
        if self.short_term_memory.should_summarize(user_id, session_id):
            await self._trigger_summarization(user_id, session_id)
        
        # Build context: long-term summary + short-term turns
        context = self._build_context(user_id, session_id)
        
        # Get tools
        tools = await self.tool_registry.get_tool_definitions()
        
        # System prompt with long-term context
        system_prompt = self._get_system_prompt(message.platform, user_id)
        
        logger.info(f"Processing message from {message.platform.value}:{user_id}")
        
        try:
            # Initialize loop variables
            max_turns = 15
            current_turn = 0
            final_response = None
            
            # Helper to append to local context and persistent memory
            async def add_context(role, content, tool_calls=None, tool_call_id=None, save_to_memory=False):
                if save_to_memory:
                    self.short_term_memory.add_turn(
                        user_id, session_id, role, content, 
                        tool_calls=tool_calls, tool_call_id=tool_call_id
                    )
                
                # Update context for next iteration
                context.append({
                    "role": role, 
                    "content": content,
                    "tool_calls": tool_calls,
                    "tool_call_id": tool_call_id
                })
                # Filter None values
                if context[-1]["tool_calls"] is None: del context[-1]["tool_calls"]
                if context[-1]["tool_call_id"] is None: del context[-1]["tool_call_id"]

            while current_turn < max_turns:
                current_turn += 1
                
                # Get tools (await async fetching)
                tools = await self.tool_registry.get_tool_definitions()
                
                if status_callback and current_turn == 1:
                     await status_callback("💭 Thinking...")
                elif status_callback:
                     await status_callback("🤔 Analyzing tool results...")
                
                # Debug OpenAI Context
                try:
                    logger.debug(f"Context sent to LLM (Turn {current_turn}): {json.dumps(context, default=str)}")
                except:
                    pass

                result = await self.llm_client.create_tool_message(
                    messages=context,
                    tools=tools,
                    system=system_prompt
                )
                
                response_obj = result.get('response')
                tool_calls = result.get('tool_calls', [])
                response_text = self._extract_text(response_obj)
                if not response_text:
                    response_text = None
                
                # Format tool calls if present
                formatted_tool_calls = None
                if tool_calls:
                    formatted_tool_calls = []
                    for tc in tool_calls:
                        formatted_tool_calls.append({
                            "id": tc['id'],
                            "type": "function",
                            "function": {
                                "name": tc['name'],
                                "arguments": json.dumps(tc['input'])
                            }
                        })
                
                # If no tool calls, this is the final final response - SAVE IT
                is_final = not tool_calls
                await add_context("assistant", response_text, tool_calls=formatted_tool_calls, save_to_memory=is_final)
                
                if is_final:
                    final_response = Response(
                        content=response_text,
                        tool_calls=[],
                        tool_results=[]
                    )
                    break
                    
                # Execute tools
                logger.info(f"Executing {len(tool_calls)} tools in turn {current_turn}")
                
                if status_callback:
                    # Notify user about tools being executed
                    # Distinguish between technical tools and business skills
                    tool_names = []
                    has_skill = False
                    for tc in tool_calls:
                        name = tc['name']
                        if self.tool_registry.is_skill(name):
                             tool_names.append(f"Skill: {name}")
                             has_skill = True
                        else:
                             tool_names.append(name)
                    
                    display_names = ", ".join(tool_names)
                    emoji = "🧠" if has_skill else "🔧"
                    type_label = "skill" if (has_skill and len(tool_calls) == 1) else "tool"
                    
                    if len(tool_calls) == 1:
                        await status_callback(f"{emoji} Executing {type_label}: {display_names}...")
                    else:
                        await status_callback(f"{emoji} Executing {len(tool_calls)} actions: {display_names}...")
                
                for tc in tool_calls:
                    tool_name = tc['name']
                    tool_id = tc['id']
                    tool_input = tc['input']
                    
                    try:
                        tool_result = await self.tool_registry.execute_tool(
                            tool_name,
                            tool_input,
                            platform_context,
                            None
                        )
                        result_content = str(tool_result)
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        result_content = f"Error: {str(e)}"
                        
                    # Save Tool Result to LOCAL context only
                    await add_context("tool", result_content, tool_call_id=tool_id, save_to_memory=False)
                    
                    # Also notify status_callback about the tool result (useful for web UI to render images)
                    if status_callback:
                        await status_callback({
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "tool_id": tool_id,
                            "content": result_content
                        })
            
            if not final_response:
                final_response = Response(
                    content=response_text if response_text else "Task completed (max turns reached).",
                    tool_calls=[], # We don't return intermediate calls in final response structure for now
                    tool_results=[]
                )
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                content=f"Sorry, I encountered an error: {str(e)}",
                metadata={"error": True}
            )
    
    def _get_system_prompt(self, platform: Platform, user_id: str = None) -> str:
        """Get system prompt with long-term memory context."""
        import datetime
        now = datetime.datetime.now()
        current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        weekday = now.strftime("%A")

        base_prompt = (
            "You are Butler, an advanced agentic coding assistant and personal life manager.\n"
            f"Current Local Time: {current_time_str} ({weekday})\n"
            "You have access to a variety of tools and skills to help the user with coding, "
            "task management, and information retrieval. "
            "Always be proactive, helpful, and concise.\n\n"
            "CRITICAL: When using tools, follow the schema exactly. If a tool fails, "
            "analyze the error and try a different approach.\n\n"
            "NOTE: The conversation history might contain outdated time information. "
            "ALWAYS prioritize the 'Current Local Time' provided in this system prompt.\n\n"
            "IMPORTANT: If a tool returns a result (like an image markdown link or a data summary), "
            "make sure to incorporate or mention it in your final response to the user so they can see it."
        )
        
        platform_hints = {
            Platform.TELEGRAM: " You are connected via Telegram.",
            Platform.WEB: " You are connected via web browser.",
            Platform.SLACK: " You are connected via Slack.",
            Platform.WECHAT: " You are connected via WeChat.",
        }
        
        prompt = base_prompt + platform_hints.get(platform, "")
        
        # Add long-term memory context if available
        if user_id and self.long_term_memory:
            long_term_context = self.long_term_memory.get_context_for_llm(user_id)
            if long_term_context:
                prompt += f"\n\n[Memory Context]\n{long_term_context}"
        
        return prompt
    
    def _build_context(self, user_id: str, session_id: str) -> List[Dict]:
        """Build conversation context from short-term memory."""
        return self.short_term_memory.get_full_context(user_id, session_id)
    
    async def _trigger_summarization(self, user_id: str, session_id: str):
        """Trigger summarization of conversation to long-term memory."""
        try:
            # Get current short-term turns
            turns = self.short_term_memory.get_recent_turns(user_id, session_id)
            if not turns:
                return
            
            # Get existing summary
            existing_summary = self.long_term_memory.get_summary(user_id)
            
            # Generate new summary
            result = await self.summarizer.summarize_conversation(
                turns,
                previous_summary=existing_summary
            )
            
            # Update long-term memory
            self.long_term_memory.update_summary(
                user_id,
                summary=result.get('summary', ''),
                key_facts=result.get('key_facts', []),
                preferences=result.get('preferences', {})
            )
            
            logger.info(f"Summarized conversation for {user_id}")
            
            # Reset summary counter in short-term memory
            self.short_term_memory.reset_summary_counter(user_id, session_id)
            
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
    
    def _extract_text(self, response) -> str:
        """Extract text from LLM response."""
        if hasattr(response, 'content'):
            parts = []
            for block in response.content:
                if hasattr(block, 'text'):
                    parts.append(block.text)
            return '\n'.join(parts)
        return str(response)
    
    async def get_session_history(
        self, 
        user_id: str, 
        platform: Platform
    ) -> List[Dict]:
        """
        Get session history for a user on a platform.
        
        Args:
            user_id: User identifier
            platform: Platform
            
        Returns:
            List of messages
        """
        session_id = f"{platform.value}_{user_id}"
        return await self.session_manager.get_session_context(user_id, session_id)
    
    async def merge_session(
        self, 
        source_user_id: str, 
        source_platform: Platform,
        target_user_id: str,
        target_platform: Platform
    ) -> bool:
        """
        Merge sessions across platforms (e.g., view TG history from Web).
        
        For now, this just allows viewing - not actual merging.
        """
        # Get source session
        source_history = await self.get_session_history(source_user_id, source_platform)
        
        if not source_history:
            return False
        
        logger.info(f"Session merge: {source_platform.value}:{source_user_id} -> {target_platform.value}:{target_user_id}")
        return True
    
    async def shutdown(self):
        """Cleanup on shutdown."""
        if self.plugin_manager:
            await self.plugin_manager.shutdown_plugins()
        logger.info("AgentCore shutdown complete")


# Global agent instance
_agent_core: Optional[AgentCore] = None


def get_agent_core(config=None) -> AgentCore:
    """Get or create the global AgentCore instance."""
    global _agent_core
    if _agent_core is None:
        _agent_core = AgentCore(config)
    return _agent_core
