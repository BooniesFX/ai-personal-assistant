#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Memory Summarizer
Uses LLM to summarize conversations for long-term memory.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Summarization prompts
SUMMARY_SYSTEM_PROMPT = """You are a memory summarizer. Your task is to:
1. Create a concise summary of the conversation
2. Extract key facts about the user
3. Identify user preferences

Respond in JSON format:
{
  "summary": "Brief summary of the conversation (2-3 sentences)",
  "key_facts": ["fact1", "fact2", ...],
  "preferences": {"key": "value", ...}
}

Keep it concise. Focus on information useful for future conversations."""

SUMMARY_USER_PROMPT = """Please summarize this conversation:

{conversation}

Previous context (if any):
{previous_context}
"""


class MemorySummarizer:
    """
    LLM-based conversation summarizer.
    
    Extracts summaries, facts, and preferences from conversations
    for storage in long-term memory.
    """
    
    def __init__(self, llm_client):
        """
        Initialize summarizer.
        
        Args:
            llm_client: LLM client for summarization
        """
        self.llm_client = llm_client
    
    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        previous_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summarize a conversation.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            previous_summary: Optional previous summary to incorporate
            
        Returns:
            Dict with 'summary', 'key_facts', and 'preferences'
        """
        if not messages:
            return {
                "summary": "",
                "key_facts": [],
                "preferences": {}
            }
        
        # Format conversation
        conversation_text = self._format_conversation(messages)
        
        # Format previous context
        previous_context = previous_summary or "None"
        
        # Create prompt
        user_message = SUMMARY_USER_PROMPT.format(
            conversation=conversation_text,
            previous_context=previous_context
        )
        
        try:
            response = await self.llm_client.create_message(
                messages=[{"role": "user", "content": user_message}],
                system=SUMMARY_SYSTEM_PROMPT,
                max_tokens=500
            )
            
            # Extract text from response
            response_text = ""
            if hasattr(response, 'content'):
                for block in response.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
            
            # Parse JSON response
            result = self._parse_summary_response(response_text)
            logger.info(f"Generated summary with {len(result.get('key_facts', []))} facts")
            return result
            
        except Exception as e:
            logger.error(f"Error summarizing conversation: {e}")
            # Return basic fallback
            return {
                "summary": f"Conversation with {len(messages)} messages.",
                "key_facts": [],
                "preferences": {}
            }
    
    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into text for summarization."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n\n".join(lines)
    
    def _parse_summary_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured summary."""
        import json
        
        # Try to extract JSON
        try:
            # Find JSON block
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)
                
                return {
                    "summary": result.get("summary", ""),
                    "key_facts": result.get("key_facts", []),
                    "preferences": result.get("preferences", {})
                }
        except json.JSONDecodeError:
            pass
        
        # Fallback: use response as summary
        return {
            "summary": response_text[:500],
            "key_facts": [],
            "preferences": {}
        }
    
    async def extract_facts(
        self,
        message: str
    ) -> List[str]:
        """
        Extract facts from a single message.
        
        Lightweight extraction without full summarization.
        
        Args:
            message: User message to analyze
            
        Returns:
            List of extracted facts
        """
        # Simple heuristic extraction (no LLM call for efficiency)
        facts = []
        
        # Look for "I am/I'm" statements
        lower_msg = message.lower()
        
        patterns = [
            ("i am ", "User said they are"),
            ("i'm ", "User said they are"),
            ("my name is ", "User's name is"),
            ("i work ", "User works"),
            ("i live ", "User lives"),
            ("i like ", "User likes"),
            ("i prefer ", "User prefers"),
        ]
        
        for pattern, prefix in patterns:
            if pattern in lower_msg:
                idx = lower_msg.find(pattern)
                end_idx = lower_msg.find('.', idx)
                if end_idx == -1:
                    end_idx = min(idx + 50, len(message))
                
                fact_text = message[idx:end_idx].strip()
                if len(fact_text) > 10:
                    facts.append(fact_text)
        
        return facts[:3]  # Max 3 facts per message
