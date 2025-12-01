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
    # Telegram
    if os.environ.get('TELEGRAM_BOT_TOKEN'):
        if not config.has_section('telegram'):
            config.add_section('telegram')
        config.set('telegram', 'bot_token', os.environ.get('TELEGRAM_BOT_TOKEN'))

    # Auth
    if os.environ.get('ADMIN_ID'):
        if not config.has_section('auth'):
            config.add_section('auth')
        config.set('auth', 'admin_id', os.environ.get('ADMIN_ID'))

    # ModelScope
    if not config.has_section('modelscope'):
        config.add_section('modelscope')
        
    if os.environ.get('MODELSCOPE_API_KEY'):
        config.set('modelscope', 'api_key', os.environ.get('MODELSCOPE_API_KEY'))
    if os.environ.get('MODELSCOPE_BASE_URL'):
        config.set('modelscope', 'base_url', os.environ.get('MODELSCOPE_BASE_URL'))
    if os.environ.get('MODELSCOPE_MODEL_ID'):
        config.set('modelscope', 'model_id', os.environ.get('MODELSCOPE_MODEL_ID'))

    # Image Processing Defaults
    if not config.has_section('image_processing'):
        config.add_section('image_processing')

    if os.environ.get('DEFAULT_WIDTH'):
        config.set('image_processing', 'default_width', os.environ.get('DEFAULT_WIDTH'))
    if os.environ.get('DEFAULT_HEIGHT'):
        config.set('image_processing', 'default_height', os.environ.get('DEFAULT_HEIGHT'))
    if os.environ.get('DEFAULT_STEPS'):
        config.set('image_processing', 'default_steps', os.environ.get('DEFAULT_STEPS'))
    
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
