#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base Skill Class
Skills represent high-level business logic and SOPs (Standard Operating Procedures).
Unlike atomic tools, skills often orchestrate multiple tools or follow complex rules.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseSkill(ABC):
    """
    Abstract base class for all agent skills.
    
    A skill is a self-contained business logic unit that the agent can invoke.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
    @abstractmethod
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute the skill logic."""
        pass

    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Return the tool definition for this skill so the LLM can call it.
        By default, we treat skills as tools in the LLM's manifest.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_input_schema()
        }

    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for skill parameters."""
        pass
