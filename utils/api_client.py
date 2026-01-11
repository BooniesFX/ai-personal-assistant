#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ModelScope API Client
Shared client for ModelScope image generation API
"""

import httpx
import asyncio
import json
from io import BytesIO
from PIL import Image

class ModelScopeClient:
    """Async Client for ModelScope API"""
    
    def __init__(self, api_key, base_url=None, logger=None, provider='modelscope'):
        self.provider = provider
        self.logger = logger
        self.api_key = api_key
        self.base_url = base_url.rstrip('/') + '/' if base_url else "https://api-inference.modelscope.cn/api/v1/"

    async def generate_image(self, prompt, model_id='Tongyi-MAI/Z-Image-Turbo',
                      negative_prompt='', width=1024, height=1024,
                      steps=15, seed=42, timeout=120, status_callback=None):
        """
        Async generate image from text prompt
        """
        if not self.api_key:
            raise ValueError("ModelScope API Key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        request_data = {
            "model": model_id,
            "prompt": prompt,
            "size": f"{width}x{height}",
            "steps": steps,
            "n_steps": steps,
            "seed": seed
        }
        
        if negative_prompt:
            request_data["negative_prompt"] = negative_prompt

        async with httpx.AsyncClient(timeout=30.0) as client:
            if self.logger:
                self.logger.info(f"Submitting image task: {prompt[:50]}...")
            
            # Submit task
            response = await client.post(
                f"{self.base_url}v1/images/generations",
                headers={**headers, "X-ModelScope-Async-Mode": "true"},
                json=request_data
            )
            response.raise_for_status()
            task_id = response.json().get("task_id")
            
            if not task_id:
                raise Exception(f"Failed to get task_id: {response.text}")

            # Poll for result
            max_attempts = timeout // 2
            for attempt in range(1, max_attempts + 1):
                await asyncio.sleep(2)
                
                try:
                    result_resp = await client.get(
                        f"{self.base_url}v1/tasks/{task_id}",
                        headers={**headers, "X-ModelScope-Task-Type": "image_generation"},
                    )
                    result_resp.raise_for_status()
                    data = result_resp.json()
                    status = data.get("task_status")
                    
                    msg = f"Task Status: {status} (Attempt {attempt}/{max_attempts})"
                    if self.logger:
                        self.logger.info(msg)
                    if status_callback:
                        await status_callback(f"🎨 {msg}")

                    if status == "SUCCEED":
                        image_url = data["output_images"][0]
                        img_resp = await client.get(image_url)
                        img_resp.raise_for_status()
                        
                        image = Image.open(BytesIO(img_resp.content))
                        bio = BytesIO()
                        image.save(bio, format='JPEG', quality=95)
                        bio.seek(0)
                        return bio
                    
                    elif status == "FAILED":
                        raise Exception(f"Image generation failed: {data.get('message', 'Unknown error')}")
                        
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Polling error: {e}")
                    continue

        raise TimeoutError(f"Image generation timed out after {timeout} seconds")

