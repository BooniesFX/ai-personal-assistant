#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ModelScope API Client
Shared client for ModelScope image generation API
"""

import requests
import time
import json
from io import BytesIO
from PIL import Image


class ModelScopeClient:
    """Client for ModelScope API"""
    
    def __init__(self, api_key, base_url=None, logger=None, provider='modelscope'):
        """
        Initialize client
        
        Args:
            api_key: ModelScope API key
            base_url: API base URL
            logger: Logger instance (optional)
        """
        self.provider = provider
        self.logger = logger


        self.api_key = api_key
        self.base_url = base_url

    def generate_image(self, prompt, model_id='Tongyi-MAI/Z-Image-Turbo',
                      negative_prompt='', width=1024, height=1024,
                      steps=15, seed=42, timeout=120):
        """
        Generate image from text prompt
        
        Args:
            prompt: Text prompt
            model_id: Model identifier
            negative_prompt: Negative prompt (optional)
            width: Image width
            height: Image height
            steps: Number of inference steps
            seed: Random seed (optional)
            timeout: Max wait time in seconds
            
        Returns:
            BytesIO: Generated image
            
        Raises:
            ValueError: If API key not set
            TimeoutError: If generation times out
            Exception: For other errors
        """
        if not self.api_key:
            raise ValueError("ModelScope API Key not configured")
        
        common_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        request_data = {
            "model": model_id,
            "prompt": prompt,
        }
        
        if negative_prompt:
            request_data["negative_prompt"] = negative_prompt
            
        # Add optional parameters
        # OpenAI compatible API expects 'size' as string "WxH"
        if width and height:
            request_data["size"] = f"{width}x{height}"
            
        if steps:
            request_data["steps"] = steps
            request_data["n_steps"] = steps # Send both just in case
            
        if seed is not None:
            request_data["seed"] = seed
        
        if self.logger:
            self.logger.info(f"Generating image for prompt: {prompt}")
        
        # Send generation request
        response = requests.post(
            f"{self.base_url}v1/images/generations",
            headers={**common_headers, "X-ModelScope-Async-Mode": "true"},
            data=json.dumps(request_data, ensure_ascii=False).encode('utf-8')
        )
        response.raise_for_status()
        task_id = response.json()["task_id"]
        
        if self.logger:
            self.logger.info(f"Task ID: {task_id}")
        
        # Poll for result
        max_attempts = timeout // 2
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(2)
            attempt += 1
            
            result = requests.get(
                f"{self.base_url}v1/tasks/{task_id}",
                headers={**common_headers, "X-ModelScope-Task-Type": "image_generation"},
            )
            result.raise_for_status()
            data = result.json()
            
            status = data.get("task_status")
            
            if self.logger:
                self.logger.info(f"Task Status: {status} (Attempt {attempt}/{max_attempts})")
            
            if status == "SUCCEED":
                image_url = data["output_images"][0]
                if self.logger:
                    self.logger.info(f"Image URL: {image_url}")
                
                image_response = requests.get(image_url)
                image = Image.open(BytesIO(image_response.content))
                
                if self.logger:
                    self.logger.info(f"Received image size: {image.size}")
                
                # Convert to BytesIO for returning
                bio = BytesIO()
                image.save(bio, format='JPEG', quality=99)
                bio.seek(0)
                return bio
            elif status == "FAILED":
                raise Exception(f"Image generation failed: {data.get('message', 'Unknown error')}")
        
        raise TimeoutError(f"Image generation timed out after {timeout} seconds")
