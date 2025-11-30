#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plugin Manager
Handles plugin discovery, loading, and lifecycle
"""

import os
import importlib
import inspect
from typing import List, Dict
from bot.base_plugin import BasePlugin


class PluginManager:
    """Manages bot plugins"""
    
    def __init__(self, config, logger):
        """
        Initialize plugin manager
        
        Args:
            config: ConfigParser instance
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.plugins: List[BasePlugin] = []
        self.plugin_dir = "plugins"
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins
        
        Returns:
            List of plugin module names
        """
        plugin_modules = []
        
        if not os.path.exists(self.plugin_dir):
            self.logger.warning(f"Plugin directory '{self.plugin_dir}' not found")
            return plugin_modules
        
        for item in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(self.plugin_dir, item)
            
            # Check if it's a directory and has a plugin.py file
            if os.path.isdir(plugin_path):
                plugin_file = os.path.join(plugin_path, "plugin.py")
                if os.path.exists(plugin_file):
                    plugin_modules.append(f"{self.plugin_dir}.{item}.plugin")
                    self.logger.info(f"Discovered plugin: {item}")
        
        return plugin_modules
    
    async def load_plugins(self):
        """Load all discovered plugins"""
        plugin_modules = self.discover_plugins()
        
        for module_name in plugin_modules:
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Find plugin class (should inherit from BasePlugin)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BasePlugin) and 
                        obj != BasePlugin):
                        
                        # Instantiate plugin
                        plugin = obj(self.config, self.logger)
                        
                        # Setup plugin
                        if await plugin.setup():
                            self.plugins.append(plugin)
                            self.logger.info(f"Loaded plugin: {plugin.name}")
                        else:
                            self.logger.error(f"Failed to setup plugin: {plugin.name}")
                        
                        break
                
            except Exception as e:
                self.logger.error(f"Error loading plugin {module_name}: {e}")
    
    async def shutdown_plugins(self):
        """Shutdown all plugins"""
        for plugin in self.plugins:
            try:
                await plugin.shutdown()
                self.logger.info(f"Shutdown plugin: {plugin.name}")
            except Exception as e:
                self.logger.error(f"Error shutting down plugin {plugin.name}: {e}")
    
    def get_plugin(self, name: str) -> BasePlugin:
        """
        Get plugin by name
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None
        """
        for plugin in self.plugins:
            if plugin.name == name:
                return plugin
        return None
    
    def get_all_commands(self) -> Dict[str, BasePlugin]:
        """
        Get all commands from all plugins
        
        Returns:
            Dict mapping command names to plugins
        """
        command_map = {}
        for plugin in self.plugins:
            if plugin.enabled:
                for cmd in plugin.commands:
                    command_map[cmd['command']] = plugin
        return command_map
    
    def get_help_text(self) -> str:
        """
        Get help text for all plugins
        
        Returns:
            Formatted help text
        """
        help_text = "🤖 *Available Tools*\n\n"
        
        for plugin in self.plugins:
            if plugin.enabled:
                help_text += plugin.get_help_text() + "\n"
        
        return help_text
