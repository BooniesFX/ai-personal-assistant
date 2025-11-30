#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Permission Manager
Handles user and group access control
"""

import json
import os
import logging

class PermissionManager:
    """Manages permissions for users and groups"""
    
    def __init__(self, data_file='data/permissions.json'):
        """
        Initialize permission manager
        
        Args:
            data_file: Path to JSON storage file
        """
        self.data_file = data_file
        self.logger = logging.getLogger(__name__)
        self.permissions = {
            "users": [],
            "groups": []
        }
        self.load()
    
    def load(self):
        """Load permissions from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.permissions = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading permissions: {e}")
        else:
            self.save()
    
    def save(self):
        """Save permissions to file"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.permissions, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving permissions: {e}")
    
    def is_allowed_user(self, user_id):
        """Check if user is allowed"""
        return user_id in self.permissions["users"]
    
    def is_allowed_group(self, chat_id):
        """Check if group is allowed"""
        return chat_id in self.permissions["groups"]
    
    def add_user(self, user_id, name=None):
        """Add user to whitelist"""
        if user_id not in self.permissions["users"]:
            self.permissions["users"].append(user_id)
            self.save()
            return True
        return False
    
    def remove_user(self, user_id):
        """Remove user from whitelist"""
        if user_id in self.permissions["users"]:
            self.permissions["users"].remove(user_id)
            self.save()
            return True
        return False
    
    def add_group(self, chat_id, title=None):
        """Add group to whitelist"""
        if chat_id not in self.permissions["groups"]:
            self.permissions["groups"].append(chat_id)
            self.save()
            return True
        return False
    
    def remove_group(self, chat_id):
        """Remove group from whitelist"""
        if chat_id in self.permissions["groups"]:
            self.permissions["groups"].remove(chat_id)
            self.save()
            return True
        return False
    
    def get_stats(self):
        """Get permission stats"""
        return {
            "users": len(self.permissions["users"]),
            "groups": len(self.permissions["groups"])
        }
