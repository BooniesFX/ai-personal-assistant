#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Long-Term Memory
Persistent summarized conversation history.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MemorySummary:
    """A summarized memory entry."""
    summary: str
    key_facts: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    turn_count: int = 0


class LongTermMemory:
    """
    Long-term memory for persistent context.
    
    Stores summarized conversation history and extracted facts.
    This persists across sessions and provides background context.
    """
    
    def __init__(self, storage_path: str = "data/long_term_memory.json"):
        """
        Initialize long-term memory.
        
        Args:
            storage_path: Path to storage file
        """
        self.storage_path = Path(storage_path)
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load()
    
    def _load(self):
        """Load from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                logger.info(f"Loaded long-term memory from {self.storage_path}")
            else:
                self._data = {}
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Error loading long-term memory: {e}")
            self._data = {}
    
    def _save(self):
        """Save to storage."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving long-term memory: {e}")
    
    def _get_user_key(self, user_id: str) -> str:
        """Get user storage key."""
        return f"user_{user_id}"
    
    def get_summary(self, user_id: str) -> Optional[str]:
        """
        Get user's overall conversation summary.
        
        Args:
            user_id: User identifier
            
        Returns:
            Summary text or None
        """
        user_key = self._get_user_key(user_id)
        user_data = self._data.get(user_key, {})
        return user_data.get("summary")
    
    def get_key_facts(self, user_id: str) -> List[str]:
        """
        Get extracted key facts about user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of key facts
        """
        user_key = self._get_user_key(user_id)
        user_data = self._data.get(user_key, {})
        return user_data.get("key_facts", [])
    
    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences.
        
        Args:
            user_id: User identifier
            
        Returns:
            Preferences dict
        """
        user_key = self._get_user_key(user_id)
        user_data = self._data.get(user_key, {})
        return user_data.get("preferences", {})
    
    def update_summary(
        self, 
        user_id: str, 
        summary: str,
        key_facts: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ):
        """
        Update user's memory summary.
        
        Args:
            user_id: User identifier
            summary: New summary text
            key_facts: Optional new facts to add
            preferences: Optional preferences to update
        """
        user_key = self._get_user_key(user_id)
        
        if user_key not in self._data:
            self._data[user_key] = {}
        
        self._data[user_key]["summary"] = summary
        self._data[user_key]["updated_at"] = datetime.now().isoformat()
        
        # Merge key facts
        if key_facts:
            existing = self._data[user_key].get("key_facts", [])
            # Add new facts, avoid duplicates
            for fact in key_facts:
                if fact not in existing:
                    existing.append(fact)
            self._data[user_key]["key_facts"] = existing[-50:]  # Keep last 50
        
        # Merge preferences
        if preferences:
            existing = self._data[user_key].get("preferences", {})
            existing.update(preferences)
            self._data[user_key]["preferences"] = existing
        
        self._save()
        logger.info(f"Updated long-term memory for {user_id}")
    
    def add_fact(self, user_id: str, fact: str):
        """
        Add a single key fact.
        
        Args:
            user_id: User identifier
            fact: Fact to add
        """
        user_key = self._get_user_key(user_id)
        
        if user_key not in self._data:
            self._data[user_key] = {}
        
        facts = self._data[user_key].get("key_facts", [])
        if fact not in facts:
            facts.append(fact)
            self._data[user_key]["key_facts"] = facts[-50:]
            self._save()
    
    def set_preference(self, user_id: str, key: str, value: Any):
        """
        Set a user preference.
        
        Args:
            user_id: User identifier
            key: Preference key
            value: Preference value
        """
        user_key = self._get_user_key(user_id)
        
        if user_key not in self._data:
            self._data[user_key] = {}
        
        if "preferences" not in self._data[user_key]:
            self._data[user_key]["preferences"] = {}
        
        self._data[user_key]["preferences"][key] = value
        self._save()
    
    def get_context_for_llm(self, user_id: str) -> str:
        """
        Get formatted context for LLM system prompt.
        
        Args:
            user_id: User identifier
            
        Returns:
            Formatted context string
        """
        summary = self.get_summary(user_id)
        facts = self.get_key_facts(user_id)
        prefs = self.get_preferences(user_id)
        
        parts = []
        
        if summary:
            parts.append(f"Previous conversation summary:\n{summary}")
        
        if facts:
            facts_text = "\n".join([f"- {f}" for f in facts[-10:]])  # Last 10
            parts.append(f"Known facts about user:\n{facts_text}")
        
        if prefs:
            prefs_text = "\n".join([f"- {k}: {v}" for k, v in prefs.items()])
            parts.append(f"User preferences:\n{prefs_text}")
        
        return "\n\n".join(parts) if parts else ""
    
    def clear_user(self, user_id: str):
        """
        Clear all memory for a user.
        
        Args:
            user_id: User identifier
        """
        user_key = self._get_user_key(user_id)
        if user_key in self._data:
            del self._data[user_key]
            self._save()
            logger.info(f"Cleared long-term memory for {user_id}")
