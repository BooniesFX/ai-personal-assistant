#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from typing import Dict, List, Any, Optional
from agents.skills.base import BaseSkill
from agents.skills.loader import MarkdownSkillLoader

logger = logging.getLogger(__name__)

class SkillManager:
    """Manages business SOP skills."""
    
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self.loader = MarkdownSkillLoader()
        self._load_markdown_skills()
        
    def _load_markdown_skills(self):
        """Load skills from SKILL.md files."""
        skills = self.loader.load_skills()
        for skill in skills:
            self.register_skill(skill)
        
    def register_skill(self, skill: BaseSkill):
        """Register a new business skill."""
        self._skills[skill.name] = skill
        logger.info(f"Registered skill: {skill.name}")
        
    def get_skill_definitions(self) -> List[Dict[str, Any]]:
        """Get definitions for all registered skills."""
        return [s.get_tool_definition() for s in self._skills.values()]
        
    async def execute_skill(self, name: str, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a registered skill."""
        if name not in self._skills:
            raise ValueError(f"Skill not found: {name}")
        return await self._skills[name].execute(params, context)

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """Get skill by name."""
        return self._skills.get(name)
