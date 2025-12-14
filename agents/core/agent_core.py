#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Agent Core
Central agent that handles all platforms through transport adapters.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List, Callable
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
        
        from agents.session.manager import SessionManager
        from agents.memory.store import JSONMemoryStore
        from agents.memory.short_term import ShortTermMemory
        from agents.memory.long_term import LongTermMemory
        from agents.memory.summarizer import MemorySummarizer
        from agents.tools.registry import ToolRegistry
        from agents.core.client import ClaudeClient
        from bot.plugin_manager import PluginManager
        from utils.config import load_config
        from agents.identity.manager import UserIdentityManager
        
        # Load config if not provided
        if self.config is None:
            self.config = load_config()
        
        # Initialize core components
        self.memory_store = JSONMemoryStore("data/claude_memory.json")
        self.session_manager = SessionManager(self.memory_store)
        self.llm_client = ClaudeClient(self.config)
        self.tool_registry = ToolRegistry()
        self.identity_manager = UserIdentityManager()
        
        # Initialize dual memory system
        self.short_term_memory = ShortTermMemory(window_size=5)
        self.long_term_memory = LongTermMemory("data/long_term_memory.json")
        self.summarizer = MemorySummarizer(self.llm_client)
        
        logger.info("Dual memory system initialized (short-term: 5 turns, long-term: persistent)")
        
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
        platform_context: Any = None
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
        tools = self.tool_registry.get_tool_definitions()
        
        # System prompt with long-term context
        system_prompt = self._get_system_prompt(message.platform, user_id)
        
        logger.info(f"Processing message from {message.platform.value}:{user_id}")
        
        try:
            if tools:
                # With tool support
                result = await self.llm_client.create_tool_message(
                    messages=context,
                    tools=tools,
                    system=system_prompt
                )
                
                response_obj = result.get('response')
                tool_calls = result.get('tool_calls', [])
                tool_results = []
                
                # Execute tool calls
                if tool_calls:
                    for tc in tool_calls:
                        try:
                            tool_result = await self.tool_registry.execute_tool(
                                tc['name'],
                                tc['input'],
                                platform_context,
                                None
                            )
                            tool_results.append({
                                'tool_name': tc['name'],
                                'result': str(tool_result)
                            })
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            tool_results.append({
                                'tool_name': tc['name'],
                                'error': str(e)
                            })
                
                # Extract text response
                response_text = self._extract_text(response_obj)
                
            else:
                # Without tools
                response_obj = await self.llm_client.create_message(
                    messages=context,
                    system=system_prompt
                )
                response_text = self._extract_text(response_obj)
                tool_calls = []
                tool_results = []
            
            # Add assistant response to short-term memory
            self.short_term_memory.add_turn(
                user_id, session_id,
                role="assistant",
                content=response_text
            )
            
            return Response(
                content=response_text,
                tool_calls=tool_calls,
                tool_results=tool_results
            )
            
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
        base = (
            "You are a helpful AI assistant. "
            "You have access to tools and should use them when appropriate. "
            "Respond naturally and concisely."
        )
        
        platform_hints = {
            Platform.TELEGRAM: " You are connected via Telegram.",
            Platform.WEB: " You are connected via web browser.",
            Platform.SLACK: " You are connected via Slack.",
            Platform.WECHAT: " You are connected via WeChat.",
        }
        
        prompt = base + platform_hints.get(platform, "")
        
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
