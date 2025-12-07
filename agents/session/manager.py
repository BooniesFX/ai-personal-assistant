#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Session Manager
Manages user sessions with context and state persistence.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from ..memory.store import JSONMemoryStore

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """User session data structure."""
    user_id: int
    chat_id: int
    created_at: datetime
    last_active: datetime
    context: List[Dict[str, str]]
    preferences: Dict[str, Any]
    metadata: Dict[str, Any]


class SessionManager:
    """Manages user sessions with persistence."""

    def __init__(self, memory_store: JSONMemoryStore, session_timeout_hours: int = 24):
        """
        Initialize session manager.

        Args:
            memory_store: Memory store for session persistence
            session_timeout_hours: Hours after which inactive sessions expire
        """
        self.memory_store = memory_store
        self.session_timeout_hours = session_timeout_hours
        self.active_sessions: Dict[str, SessionData] = {}

        # Load existing sessions from memory store
        self._load_sessions()

    def _get_session_key(self, user_id: int, chat_id: int) -> str:
        """Generate session key from user and chat IDs."""
        return f"session_{user_id}_{chat_id}"

    def _is_session_expired(self, session: SessionData) -> bool:
        """Check if session has expired."""
        if not session.last_active:
            return True

        expiration_time = session.last_active + timedelta(hours=self.session_timeout_hours)
        return datetime.now() > expiration_time

    def _load_sessions(self):
        """Load sessions from memory store."""
        try:
            sessions_data = self.memory_store.get("sessions", {})
            for key, data in sessions_data.items():
                # Convert datetime strings back to datetime objects
                if 'created_at' in data:
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                if 'last_active' in data:
                    data['last_active'] = datetime.fromisoformat(data['last_active'])

                # Create SessionData object
                session = SessionData(**data)

                # Only load non-expired sessions
                if not self._is_session_expired(session):
                    self.active_sessions[key] = session

            logger.info(f"Loaded {len(self.active_sessions)} active sessions")
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")

    def _save_sessions(self):
        """Save sessions to memory store."""
        try:
            sessions_data = {}
            for key, session in self.active_sessions.items():
                # Convert datetime objects to strings for JSON serialization
                session_dict = asdict(session)
                if session_dict.get('created_at'):
                    session_dict['created_at'] = session_dict['created_at'].isoformat()
                if session_dict.get('last_active'):
                    session_dict['last_active'] = session_dict['last_active'].isoformat()

                sessions_data[key] = session_dict

            self.memory_store.set("sessions", sessions_data)
            self.memory_store.save()
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")

    async def get_or_create_session(
        self,
        user_id: int,
        chat_id: int,
        initial_context: Optional[List[Dict[str, str]]] = None
    ) -> SessionData:
        """
        Get existing session or create a new one.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            initial_context: Initial conversation context

        Returns:
            SessionData object
        """
        session_key = self._get_session_key(user_id, chat_id)

        # Check if we have an active session
        if session_key in self.active_sessions:
            session = self.active_sessions[session_key]

            # Check if session expired
            if self._is_session_expired(session):
                # Remove expired session
                del self.active_sessions[session_key]
            else:
                # Update last active time
                session.last_active = datetime.now()
                self._save_sessions()
                return session

        # Create new session
        now = datetime.now()
        session = SessionData(
            user_id=user_id,
            chat_id=chat_id,
            created_at=now,
            last_active=now,
            context=initial_context or [],
            preferences={},
            metadata={}
        )

        self.active_sessions[session_key] = session
        self._save_sessions()

        return session

    async def update_session_context(
        self,
        user_id: int,
        chat_id: int,
        message: Dict[str, str]
    ) -> SessionData:
        """
        Update session context with a new message.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            message: Message dictionary with role and content

        Returns:
            Updated SessionData object
        """
        session = await self.get_or_create_session(user_id, chat_id)

        # Add message to context
        session.context.append(message)

        # Keep context to reasonable size (last 20 messages)
        if len(session.context) > 20:
            session.context = session.context[-20:]

        # Update last active time
        session.last_active = datetime.now()

        # Save sessions
        self._save_sessions()

        return session

    async def get_session_context(
        self,
        user_id: int,
        chat_id: int
    ) -> List[Dict[str, str]]:
        """
        Get session context.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID

        Returns:
            List of message dictionaries
        """
        session = await self.get_or_create_session(user_id, chat_id)
        return session.context

    async def set_preference(
        self,
        user_id: int,
        chat_id: int,
        key: str,
        value: Any
    ):
        """
        Set a user preference.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            key: Preference key
            value: Preference value
        """
        session = await self.get_or_create_session(user_id, chat_id)
        session.preferences[key] = value
        session.last_active = datetime.now()
        self._save_sessions()

    async def get_preference(
        self,
        user_id: int,
        chat_id: int,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get a user preference.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            key: Preference key
            default: Default value if key not found

        Returns:
            Preference value or default
        """
        session = await self.get_or_create_session(user_id, chat_id)
        return session.preferences.get(key, default)

    async def clear_session(self, user_id: int, chat_id: int):
        """
        Clear a user session.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
        """
        session_key = self._get_session_key(user_id, chat_id)
        if session_key in self.active_sessions:
            del self.active_sessions[session_key]
            self._save_sessions()

    def cleanup_expired_sessions(self):
        """Remove expired sessions from memory."""
        expired_keys = []
        for key, session in self.active_sessions.items():
            if self._is_session_expired(session):
                expired_keys.append(key)

        for key in expired_keys:
            del self.active_sessions[key]

        if expired_keys:
            self._save_sessions()
            logger.info(f"Cleaned up {len(expired_keys)} expired sessions")