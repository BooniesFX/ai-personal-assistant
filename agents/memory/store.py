#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JSON Memory Store
Simple JSON-based memory storage for user data and preferences.
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class JSONMemoryStore:
    """JSON-based memory storage system."""

    def __init__(self, storage_path: str = "data/memory.json"):
        """
        Initialize memory store.

        Args:
            storage_path: Path to JSON file for storage
        """
        self.storage_path = Path(storage_path)
        self.data: Dict[str, Any] = {}

        # Create storage directory if it doesn't exist
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data
        self._load()

    def _load(self):
        """Load data from JSON file."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info(f"Loaded memory data from {self.storage_path}")
            else:
                # Create empty data structure
                self.data = {}
                self._save()
                logger.info(f"Created new memory store at {self.storage_path}")
        except Exception as e:
            logger.error(f"Error loading memory data: {e}")
            self.data = {}

    def _save(self):
        """Save data to JSON file."""
        try:
            # Create backup of existing file
            if self.storage_path.exists():
                backup_path = self.storage_path.with_suffix('.json.bak')
                self.storage_path.rename(backup_path)

            # Write new data
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

            # Remove backup if save was successful
            backup_path = self.storage_path.with_suffix('.json.bak')
            if backup_path.exists():
                backup_path.unlink()

            logger.debug(f"Saved memory data to {self.storage_path}")
        except Exception as e:
            logger.error(f"Error saving memory data: {e}")
            # Restore backup if it exists
            backup_path = self.storage_path.with_suffix('.json.bak')
            if backup_path.exists():
                backup_path.rename(self.storage_path)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value by key.

        Args:
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Value associated with key or default
        """
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """
        Set value for key.

        Args:
            key: Key to set
            value: Value to store
        """
        self.data[key] = value

    def delete(self, key: str):
        """
        Delete key from storage.

        Args:
            key: Key to delete
        """
        if key in self.data:
            del self.data[key]

    def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Key to check

        Returns:
            True if key exists, False otherwise
        """
        return key in self.data

    def keys(self) -> list:
        """
        Get all keys.

        Returns:
            List of all keys
        """
        return list(self.data.keys())

    def clear(self):
        """Clear all data."""
        self.data.clear()

    def save(self):
        """Save data to storage."""
        self._save()

    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Get user-specific data.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of user data
        """
        return self.data.get(f"user_{user_id}", {})

    def set_user_data(self, user_id: int, data: Dict[str, Any]):
        """
        Set user-specific data.

        Args:
            user_id: User identifier
            data: User data to store
        """
        self.data[f"user_{user_id}"] = data

    def get_user_preference(self, user_id: int, key: str, default: Any = None) -> Any:
        """
        Get user preference.

        Args:
            user_id: User identifier
            key: Preference key
            default: Default value

        Returns:
            Preference value or default
        """
        user_data = self.get_user_data(user_id)
        return user_data.get("preferences", {}).get(key, default)

    def set_user_preference(self, user_id: int, key: str, value: Any):
        """
        Set user preference.

        Args:
            user_id: User identifier
            key: Preference key
            value: Preference value
        """
        user_data = self.get_user_data(user_id)
        if "preferences" not in user_data:
            user_data["preferences"] = {}
        user_data["preferences"][key] = value
        self.set_user_data(user_id, user_data)