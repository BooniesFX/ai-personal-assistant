#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Management
Centralized config loading with environment variable support
"""

import configparser
import os


def load_config(config_file='config.ini'):
    """
    Load configuration from file and environment
    
    Args:
        config_file: Path to config file
        
    Returns:
        ConfigParser instance
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    
    # Override with environment variables if present
    # ModelScope
    if os.environ.get('MODELSCOPE_API_KEY'):
        if not config.has_section('modelscope'):
            config.add_section('modelscope')
        config.set('modelscope', 'api_key', os.environ.get('MODELSCOPE_API_KEY'))
    
    # Telegram
    if os.environ.get('TELEGRAM_BOT_TOKEN'):
        if not config.has_section('telegram'):
            config.add_section('telegram')
        config.set('telegram', 'bot_token', os.environ.get('TELEGRAM_BOT_TOKEN'))
    
    return config


def get_config_value(config, section, key, fallback=''):
    """
    Get config value with fallback
    
    Args:
        config: ConfigParser instance
        section: Config section
        key: Config key
        fallback: Fallback value
        
    Returns:
        Config value or fallback
    """
    return config.get(section, key, fallback=fallback)
