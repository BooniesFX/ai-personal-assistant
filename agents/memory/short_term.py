#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Short-Term Memory
Rolling window of recent conversation turns.
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional
from collections import deque
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Default number of turns to keep
DEFAULT_WINDOW_SIZE = 5


@dataclass
class ConversationTurn:
    """A single conversation turn."""
    role: str  # 'user', 'assistant', 'tool'
    content: str
    timestamp: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        d = asdict(self)
        # Remove None values to keep it clean
        return {k: v for k, v in d.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class ShortTermMemory:
    """
    Short-term memory for recent conversation context.
    
    Persists recent turns to disk to survive restarts.
    Tracks turn count for summarization triggers.
    """
    
    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE, save_path: str = "data/short_term_memory.json"):
        """
        Initialize short-term memory.
        
        Args:
            window_size: Number of turns to keep (default: 5)
            save_path: Path to JSON file for persistence
        """
        self.window_size = window_size
        self.save_path = save_path
        self._sessions: Dict[str, deque] = {}
        self._summary_counters: Dict[str, int] = {}  # Track turns since last summary
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Load from disk
        self._load()
    
    def _get_session_key(self, user_id: str, session_id: str) -> str:
        """Generate session key."""
        return f"{user_id}:{session_id}"
    
    def _ensure_session(self, session_key: str):
        """Ensure session exists."""
        if session_key not in self._sessions:
            self._sessions[session_key] = deque(maxlen=self.window_size * 2)  # 2 turns per exchange
        
        if session_key not in self._summary_counters:
            self._summary_counters[session_key] = 0
            
    def _load(self):
        """Load memory from disk."""
        if not os.path.exists(self.save_path):
            return
            
        try:
            with open(self.save_path, 'r') as f:
                data = json.load(f)
                
            for key, session_data in data.items():
                # Load turns
                turns_data = session_data.get('turns', [])
                self._sessions[key] = deque(
                    [ConversationTurn.from_dict(t) for t in turns_data],
                    maxlen=self.window_size * 2
                )
                
                # Load counter
                self._summary_counters[key] = session_data.get('turn_count_since_summary', 0)
                
            logger.info(f"Loaded short-term memory from {self.save_path}")
        except Exception as e:
            logger.error(f"Error loading short-term memory: {e}")
            
    def _save(self):
        """Save memory to disk."""
        try:
            data = {}
            for key, turns in self._sessions.items():
                data[key] = {
                    'turns': [t.to_dict() for t in turns],
                    'turn_count_since_summary': self._summary_counters.get(key, 0)
                }
                
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving short-term memory: {e}")
    
    def add_turn(
        self, 
        user_id: str, 
        session_id: str, 
        role: str, 
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a conversation turn.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            role: 'user', 'assistant', or 'tool'
            content: Message content
            tool_calls: List of tool calls (for assistant)
            tool_call_id: Tool call ID (for tool response)
            metadata: Optional metadata
        """
        session_key = self._get_session_key(user_id, session_id)
        self._ensure_session(session_key)
        
        turn = ConversationTurn(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            metadata=metadata or {}
        )
        
        self._sessions[session_key].append(turn)
        
        # Increment counter
        self._summary_counters[session_key] += 1
        
        logger.debug(f"Added {role} turn to short-term memory for {session_key}")
        
        # Persist to disk
        self._save()
    
    def get_recent_turns(
        self, 
        user_id: str, 
        session_id: str,
        count: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get recent conversation turns.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            count: Number of turns to return (default: all in window)
            
        Returns:
            List of message dicts with 'role' and 'content'
        """
        session_key = self._get_session_key(user_id, session_id)
        
        if session_key not in self._sessions:
            return []
        
        turns = list(self._sessions[session_key])
        
        if count is not None:
            turns = turns[-count:]
        
        result = []
        for t in turns:
            msg = {"role": t.role, "content": t.content}
            if t.tool_calls:
                msg["tool_calls"] = t.tool_calls
            if t.tool_call_id:
                msg["tool_call_id"] = t.tool_call_id
            result.append(msg)
        return result
    
    def get_full_context(
        self, 
        user_id: str, 
        session_id: str
    ) -> List[Dict[str, str]]:
        """
        Get full short-term context for LLM.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            List of message dicts ready for LLM
        """
        return self.get_recent_turns(user_id, session_id)
    
    def clear_session(self, user_id: str, session_id: str):
        """
        Clear a session's short-term memory.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        session_key = self._get_session_key(user_id, session_id)
        if session_key in self._sessions:
            self._sessions[session_key].clear()
            self._summary_counters[session_key] = 0
            self._save()
            logger.info(f"Cleared short-term memory for {session_key}")
    
    def get_turn_count(self, user_id: str, session_id: str) -> int:
        """
        Get number of turns in session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Number of turns
        """
        session_key = self._get_session_key(user_id, session_id)
        if session_key not in self._sessions:
            return 0
        return len(self._sessions[session_key])
    
    def should_summarize(self, user_id: str, session_id: str) -> bool:
        """
        Check if session should trigger summarization.
        
        Returns True when 10 or more turns have accumulated since last summary.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            True if summarization is recommended
        """
        session_key = self._get_session_key(user_id, session_id)
        if session_key not in self._sessions:
            return False
        
        # Trigger every 10 messages (user/assistant turns)
        return self._summary_counters.get(session_key, 0) >= 10
        
    def reset_summary_counter(self, user_id: str, session_id: str):
        """
        Reset the summarization counter after successful summarization.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        session_key = self._get_session_key(user_id, session_id)
        if session_key in self._summary_counters:
            self._summary_counters[session_key] = 0
            self._save()
            logger.info(f"Reset summary counter for {session_key}")
