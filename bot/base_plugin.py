#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base Plugin Class
All plugins must inherit from this class
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from telegram import Update
from telegram.ext import ContextTypes


class BasePlugin(ABC):
    """Abstract base class for all bot plugins"""
    
    def __init__(self, config, logger):
        """
        Initialize plugin
        
        Args:
            config: ConfigParser instance
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.enabled = True
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name/identifier"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description"""
        pass
    
    @property
    @abstractmethod
    def commands(self) -> List[Dict[str, str]]:
        """
        List of commands this plugin handles
        
        Returns:
            List of dicts with 'command' and 'description' keys
            Example: [{'command': 'generate', 'description': 'Generate an image'}]
        """
        pass
    
    @abstractmethod
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Handle a command
        
        Args:
            update: Telegram update
            context: Telegram context
            
        Returns:
            True if command was handled, False otherwise
        """
        pass
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Handle a regular message (optional)
        
        Args:
            update: Telegram update
            context: Telegram context
            
        Returns:
            True if message was handled, False otherwise
        """
        return False
    
    async def setup(self) -> bool:
        """
        Setup/initialize the plugin (optional)
        
        Returns:
            True if setup successful, False otherwise
        """
        return True
    
    async def shutdown(self):
        """Cleanup when bot shuts down (optional)"""
        pass
    
    def get_help_text(self) -> str:
        """
        Get help text for this plugin
        
        Returns:
            Formatted help text
        """
        help_text = f"*{self.name}*\n{self.description}\n\n"
        if self.commands:
            help_text += "*Commands:*\n"
            for cmd in self.commands:
                help_text += f"/{cmd['command']} - {cmd['description']}\n"
        return help_text
