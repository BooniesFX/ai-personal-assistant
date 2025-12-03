#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OPS AI Client
LLM client for analyzing problems and generating decisions
"""

import json
import requests
from typing import Dict, List, Optional


class OPSAIClient:
    """AI client for OPS module"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", 
                 model: str = "gpt-4o-mini", logger=None):
        """
        Initialize OPS AI client
        
        Args:
            api_key: LLM API key
            base_url: API base URL
            model: Model name
            logger: Logger instance
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.logger = logger
    
    def analyze_problem(self, user_input: str) -> Dict:
        """
        Analyze user's problem and generate structured response
        
        Args:
            user_input: User's problem description
            
        Returns:
            Dict with category, essence, gaps, and decisions
        """
        prompt = self._build_analysis_prompt(user_input)
        
        try:
            response = self._call_llm(prompt)
            result = self._parse_response(response)
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error analyzing problem: {e}")
            raise
    
    def _build_analysis_prompt(self, user_input: str) -> str:
        """Build prompt for problem analysis"""
        return f"""你是一个帮助用户训练"观察→抽象→结构化→决断"能力的教练。

用户输入的问题：{user_input}

请按以下JSON格式返回分析结果：
{{
  "category": ["类别1", "类别2"],  // 从以下选择：信息、沟通、效率、决策、情绪、时间管理、优先级
  "essence": "一句话本质描述",
  "gaps": ["差距1", "差距2", "差距3"],  // 3个具体差距
  "decisions": [
    {{"id": "A", "text": "决策描述（具体可执行）", "effort": "预估时间"}},
    {{"id": "B", "text": "决策描述（具体可执行）", "effort": "预估时间"}},
    {{"id": "C", "text": "决策描述（具体可执行）", "effort": "预估时间"}}
  ]
}}

要求：
1. 决策必须具体、可执行、小步骤
2. 每个决策effort控制在5分钟内
3. 决策要针对差距，能立即行动
4. 用中文回复

只返回JSON，不要其他内容。"""
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _parse_response(self, response: str) -> Dict:
        """Parse LLM response to structured data"""
        # Try to extract JSON from response
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith('```'):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1])
        
        try:
            data = json.loads(response)
            
            # Validate structure
            required_keys = ['category', 'essence', 'gaps', 'decisions']
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Missing required key: {key}")
            
            return data
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.error(f"Failed to parse JSON response: {response}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
