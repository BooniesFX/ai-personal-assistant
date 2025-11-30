#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Image Generation Plugin
Z-Image-Turbo image generation via ModelScope API
"""

from bot.base_plugin import BasePlugin
from utils.api_client import ModelScopeClient
from utils.config import get_config_value
from telegram import Update
from telegram.ext import ContextTypes


class ImageGenerationPlugin(BasePlugin):
    """Plugin for AI image generation"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        
        # Get config
        api_key = get_config_value(config, 'modelscope', 'api_key')
        base_url = get_config_value(config, 'modelscope', 'base_url', 
                                    'https://api-inference.modelscope.cn/')
        model_id = get_config_value(config, 'modelscope', 'model_id',
                                    'Tongyi-MAI/Z-Image-Turbo')
        
        # Initialize API client
        self.api_client = ModelScopeClient(api_key, base_url, logger)
        self.model_id = model_id
    
    @property
    def name(self) -> str:
        return "image_generation"
    
    @property
    def description(self) -> str:
        return "🎨 AI Image Generation - Create images from text descriptions"
    
    @property
    def commands(self):
        return [
            {
                'command': 'img',
                'description': 'Generate an image from a text prompt (shortcut)'
            }
        ]
    
    async def setup(self) -> bool:
        """Setup plugin"""
        if not self.api_client.api_key:
            self.logger.error("ModelScope API Key not configured for Image Generation plugin")
            return False
        
        self.logger.info("Image Generation plugin initialized")
        return True
    
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle commands"""
        message_text = update.message.text
        
        # Check if this is our command
        if not message_text.startswith('/img'):
            return False
        
        # Extract prompt
        # /img command
        prompt = message_text[4:].strip()
        
        if not prompt:
            await update.message.reply_text(
                "Please provide a prompt!\n\n"
                "Example: /generate A golden cat playing in the garden"
            )
            return True
        
        await self._generate_and_send(update, prompt)
        return True
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle regular text messages as prompts"""
        prompt = update.message.text.strip()
        
        if not prompt:
            return False
        
        await self._generate_and_send(update, prompt)
        return True
    
    async def _generate_and_send(self, update: Update, prompt: str):
        """Generate image and send to user"""
        # Send status message
        status_message = await update.message.reply_text(
            f"🎨 Generating image...\n\n"
            f"Prompt: {prompt}\n\n"
            f"Please wait, this may take 10-30 seconds..."
        )
        
        try:
            # Generate image
            image_bio = self.api_client.generate_image(
                prompt=prompt,
                model_id=self.model_id
            )
            
            # Send image
            await update.message.reply_photo(
                photo=image_bio,
                caption=f"✨ Generated image for:\n{prompt}",
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60
            )
            
            # Delete status message
            await status_message.delete()
            
        except Exception as e:
            self.logger.error(f"Error generating image: {e}")
            await status_message.edit_text(
                f"❌ Error generating image:\n{str(e)}\n\n"
                f"Please try again or contact the administrator."
            )
