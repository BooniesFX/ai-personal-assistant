#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SDK Hooks for Memory and Identity Integration
"""

from claude_agent_sdk import HookMatcher
import logging

logger = logging.getLogger(__name__)

# Global instances (initialized by agent)
_long_term_memory = None
_identity_manager = None

def init_hooks(config):
    """Initialize hook dependencies."""
    global _long_term_memory, _identity_manager
    
    from agents.memory.long_term import LongTermMemory
    from agents.identity.manager import UserIdentityManager
    
    _long_term_memory = LongTermMemory()
    _identity_manager = UserIdentityManager()
    
    logger.info("Hooks initialized with Memory and Identity managers")

def get_identity_manager():
    """Get the identity manager instance."""
    return _identity_manager

async def memory_injection_hook(input_data, tool_use_id, context):
    """
    Inject long-term memory into system prompt before each conversation.
    This hook runs at PreConversation phase.
    """
    if not _long_term_memory:
        return {}
    
    # Get user_id from context (set by agent)
    user_id = context.get("user_id") if isinstance(context, dict) else None
    
    if not user_id:
        return {}
    
    # Get memory context
    memory_context = _long_term_memory.get_context_for_llm(user_id)
    
    if memory_context:
        logger.info(f"Injecting memory for user {user_id}")
        return {
            "hookSpecificOutput": {
                "additionalSystemPrompt": f"\n\n## User Context (from memory)\n{memory_context}"
            }
        }
    
    return {}

async def save_conversation_hook(input_data, tool_use_id, context):
    """
    Save conversation summary after completion.
    This hook runs at PostConversation phase.
    """
    # This is a placeholder - actual implementation would analyze the conversation
    # and update long-term memory with new facts
    return {}

def get_butler_hooks(user_id: str, config: dict):
    """
    Get configured hooks with user context.
    
    Args:
        user_id: Current user identifier
        config: Application config
    
    Returns:
        Hooks dictionary for ClaudeAgentOptions
    """
    # Note: SDK hooks receive context differently
    # We'll pass user_id through a different mechanism
    
    return {
        "PreConversation": [
            HookMatcher(matcher="*", hooks=[memory_injection_hook])
        ],
        "PostConversation": [
            HookMatcher(matcher="*", hooks=[save_conversation_hook])
        ]
    }
