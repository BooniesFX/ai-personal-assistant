#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from agents.skills.base import BaseSkill

logger = logging.getLogger(__name__)

class MarkdownSkill(BaseSkill):
    """
    A skill defined by a SKILL.md file (YAML frontmatter + Markdown content).
    """
    def __init__(self, name: str, description: str, instruction: str, input_schema: Dict[str, Any]):
        super().__init__(name, description)
        self.instruction = instruction
        self._input_schema = input_schema
        
    def get_input_schema(self) -> Dict[str, Any]:
        return self._input_schema
        
    async def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        # Markdown skills are primarily "instructional" skills.
        # They don't execute Python code directly (unless we add a code interpreter later).
        # Instead, they return their system prompt/instruction bound with the inputs.
        # The AgentCore loop will see this result and understands it needs to follow these instructions.
        
        # In a real "agentic" flow, the agent calls this tool, passes args.
        # The result of this tool execution IS the SOP instruction customized for those args.
        
        # Simple string formatting if placeholders exist
        formatted_instruction = self.instruction
        try:
            formatted_instruction = self.instruction.format(**params)
        except:
            pass
            
        return f"""
[SKILL EXECUTION: {self.name}]
SOP/INSTRUCTIONS:
{formatted_instruction}

INPUT PARAMETERS:
{params}

Please proceed by following the SOP above.
"""

class MarkdownSkillLoader:
    """Loads skills from SKILL.md files."""
    
    def __init__(self, library_path: str = "agents/skills/library"):
        self.library_path = Path(library_path)
        
    def load_skills(self) -> List[MarkdownSkill]:
        """Scan library and load all valid skills."""
        skills = []
        
        if not self.library_path.exists():
            self.library_path.mkdir(parents=True, exist_ok=True)
            return []
            
        for skill_dir in self.library_path.iterdir():
            if not skill_dir.is_dir():
                continue
                
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
                
            try:
                skill = self._parse_skill_file(skill_file)
                if skill:
                    skills.append(skill)
            except Exception as e:
                logger.error(f"Error loading skill from {skill_file}: {e}")
                
        return skills
        
    def _parse_skill_file(self, file_path: Path) -> Optional[MarkdownSkill]:
        """Parse a single SKILL.md file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split YAML frontmatter and content
        if not content.startswith('---'):
            logger.warning(f"Invalid skill format in {file_path}: Missing frontmatter")
            return None
            
        parts = content.split('---', 2)
        if len(parts) < 3:
            logger.warning(f"Invalid skill format in {file_path}: Malformed frontmatter")
            return None
            
        yaml_content = parts[1]
        markdown_content = parts[2].strip()
        
        try:
            metadata = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.error(f"YAML error in {file_path}: {e}")
            return None
            
        name = metadata.get('name')
        description = metadata.get('description')
        input_schema = metadata.get('input_schema', {
            "type": "object",
            "properties": {},
            "additionalProperties": True # Allow flexible inputs by default
        })
        
        if not name or not description:
            logger.warning(f"Missing name or description in {file_path}")
            return None
            
        return MarkdownSkill(
            name=name,
            description=description,
            instruction=markdown_content,
            input_schema=input_schema
        )
