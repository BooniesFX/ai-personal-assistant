
import json
import os
import logging
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

class UserIdentityManager:
    """
    Manages user identities and platform bindings.
    Maps platform-specific IDs (Telegram ID, Web Session) to a unified Email identity.
    """
    
    def __init__(self, storage_path: str = "data/identities.json", access_code: str = None):
        """
        Initialize identity manager.
        
        Args:
            storage_path: Path to JSON storage
            access_code: Global password for web access (defaults to WEB_ACCESS_PASSWORD env var)
        """
        self.storage_path = storage_path
        self.access_code = access_code or os.environ.get('WEB_ACCESS_PASSWORD', '123456')
        self._identities: Dict[str, str] = {}  # Map: "platform:id" -> "email"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Load from disk
        self._load()
        
    def _load(self):
        """Load identities from disk."""
        if not os.path.exists(self.storage_path):
            return
            
        try:
            with open(self.storage_path, 'r') as f:
                self._identities = json.load(f)
            logger.info(f"Loaded {len(self._identities)} identity bindings")
        except Exception as e:
            logger.error(f"Error loading identities: {e}")
            
    def _save(self):
        """Save identities to disk."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self._identities, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving identities: {e}")
            
    def _get_key(self, platform_name: str, platform_id: str) -> str:
        """Generate lookup key."""
        return f"{platform_name}:{platform_id}"
        
    def bind_identity(self, platform_name: str, platform_id: str, email: str):
        """
        Bind a platform ID to an email.
        
        Args:
            platform_name: 'telegram', 'web', etc.
            platform_id: Platform specific user ID
            email: Unified email identity
        """
        key = self._get_key(platform_name, platform_id)
        self._identities[key] = email.strip().lower()
        self._save()
        logger.info(f"Bound {key} to {email}")
        
    def get_email(self, platform_name: str, platform_id: str) -> Optional[str]:
        """
        Get bound email for a platform ID.
        
        Returns:
            Email if bound, else None
        """
        key = self._get_key(platform_name, platform_id)
        return self._identities.get(key)
        
    def verify_access(self, code: str) -> bool:
        """Verify web access code."""
        # Simple string comparison
        # In production, use hash
        return code == self.access_code
