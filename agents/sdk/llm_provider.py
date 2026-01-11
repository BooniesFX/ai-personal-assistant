#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging

logger = logging.getLogger(__name__)

def get_llm_env_config(config):
    """
    Returns environment variable overrides for the Claude SDK to support third-party LLMs.
    """
    llm_provider = config.get('llm', {}).get('provider', 'anthropic')
    api_key = config.get('llm', {}).get('api_key')
    base_url = config.get('llm', {}).get('base_url')
    
    env_overrides = {}
    
    if llm_provider == 'openai' or 'deepseek' in base_url.lower() if base_url else False:
        # If using a DeepSeek or OpenAI-compatible provider
        if api_key:
            env_overrides["ANTHROPIC_API_KEY"] = api_key
        if base_url:
            env_overrides["ANTHROPIC_BASE_URL"] = base_url
            
        logger.info(f"Configuring SDK for provider {llm_provider} with base_url {base_url}")
    else:
        # Default Anthropic
        if api_key:
            env_overrides["ANTHROPIC_API_KEY"] = api_key
            
    return env_overrides
