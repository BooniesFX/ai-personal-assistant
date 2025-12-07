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


    

    # Image Processing Defaults
    if not config.has_section('image'):
        config.add_section('image')

    if os.environ.get('IMAGE_API_KEY'):
        config.set('image', 'api_key', os.environ.get('IMAGE_API_KEY'))
    if os.environ.get('IMAGE_BASE_URL'):
        config.set('image', 'base_url', os.environ.get('IMAGE_BASE_URL'))
    if os.environ.get('IMAGE_MODEL_ID'):
        config.set('image', 'model_id', os.environ.get('IMAGE_MODEL_ID'))
    if os.environ.get('IMAGE_PROVIDER'):
        config.set('image', 'provider', os.environ.get('IMAGE_PROVIDER'))
    if os.environ.get('DEFAULT_WIDTH'):
        config.set('image', 'default_width', os.environ.get('DEFAULT_WIDTH'))
    if os.environ.get('DEFAULT_HEIGHT'):
        config.set('image', 'default_height', os.environ.get('DEFAULT_HEIGHT'))
    if os.environ.get('DEFAULT_STEPS'):
        config.set('image', 'default_steps', os.environ.get('DEFAULT_STEPS'))

    # OPS Module
    if not config.has_section('ops'):
        config.add_section('ops')

    if os.environ.get('OPS_LLM_API_KEY'):
        config.set('ops', 'llm_api_key', os.environ.get('OPS_LLM_API_KEY'))
    if os.environ.get('OPS_LLM_BASE_URL'):
        config.set('ops', 'llm_base_url', os.environ.get('OPS_LLM_BASE_URL'))
    if os.environ.get('OPS_LLM_MODEL'):
        config.set('ops', 'llm_model', os.environ.get('OPS_LLM_MODEL'))
    if os.environ.get('OPS_REMINDER_TIME'):
        config.set('ops', 'reminder_time', os.environ.get('OPS_REMINDER_TIME'))

    # Claude Agent
    if not config.has_section('claude'):
        config.add_section('claude')

    if os.environ.get('ANTHROPIC_API_KEY'):
        config.set('claude', 'api_key', os.environ.get('ANTHROPIC_API_KEY'))
    if os.environ.get('CLAUDE_MODEL'):
        config.set('claude', 'model', os.environ.get('CLAUDE_MODEL'))
    if os.environ.get('CLAUDE_MAX_TOKENS'):
        config.set('claude', 'max_tokens', os.environ.get('CLAUDE_MAX_TOKENS'))
    if os.environ.get('SESSION_TIMEOUT_HOURS'):
        config.set('claude', 'session_timeout_hours', os.environ.get('SESSION_TIMEOUT_HOURS'))

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
