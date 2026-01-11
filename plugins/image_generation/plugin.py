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
from typing import Dict, Any, List


class ImageGenerationPlugin(BasePlugin):
    """Plugin for AI image generation"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        
        # Get config
        # Get config with safe fallbacks
        api_key = get_config_value(config, 'image', 'api_key', fallback=None)
        base_url = get_config_value(config, 'image', 'base_url',
                                    fallback='https://api.modelscope.cn/api/v1')
        model_id = get_config_value(config, 'image', 'model_id',
                                    fallback='Tongyi-MAI/Z-Image-Turbo')
        provider = get_config_value(config, 'image', 'provider',
                                    fallback='modelscope')
        base_url = get_config_value(config, 'image', 'base_url',
                                    fallback='https://api-inference.modelscope.cn/api/v1')
        model_id = get_config_value(config, 'image', 'model_id',
                                    fallback='Tongyi-MAI/Z-Image-Turbo')
        
        # Default settings
        # Get default settings with safe conversion
        self.default_width = int(get_config_value(config, 'image', 'default_width', fallback='1024'))
        self.default_height = int(get_config_value(config, 'image', 'default_height', fallback='1024'))
        self.default_steps = int(get_config_value(config, 'image', 'default_steps', fallback='25'))
        self.default_height = int(get_config_value(config, 'image', 'default_height', fallback='1024'))
        self.default_steps = int(get_config_value(config, 'image', 'default_steps', fallback='25'))
        
        # Initialize API client
        # Get provider with safe fallback
        provider = get_config_value(config, 'image', 'provider', fallback='modelscope')

        self.api_client = ModelScopeClient(
            api_key=api_key,
            base_url=base_url,
            logger=logger,
            provider=provider
        )
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
                'description': 'Generate image. Usage: /img [--ar 16:9] [--steps 50] prompt'
            }
        ]
    
    async def setup(self) -> bool:
        """Setup plugin"""
        if not self.api_client.api_key:
            self.logger.error("ModelScope API Key not configured for Image Generation plugin")
            return False
        
        self.logger.info("Image Generation plugin initialized")
        return True
    
    def _parse_args(self, text: str):
        """Parse arguments from text"""
        args = {
            'width': self.default_width,
            'height': self.default_height,
            'steps': self.default_steps,
            'prompt': ''
        }
        
        # Normalize dashes (handle Telegram smart punctuation)
        # Replace em-dash (—) and en-dash (–) with double hyphen (--)
        text = text.replace('—', '--').replace('–', '--')
        
        parts = text.split()
        i = 0
        prompt_parts = []
        
        while i < len(parts):
            part = parts[i]
            if part.startswith('--'):
                if i + 1 < len(parts):
                    val = parts[i+1]
                    if part == '--width':
                        args['width'] = int(val)
                        i += 2
                        continue
                    elif part == '--height':
                        args['height'] = int(val)
                        i += 2
                        continue
                    elif part == '--steps':
                        args['steps'] = int(val)
                        i += 2
                        continue
                    elif part == '--ar':
                        try:
                            w, h = map(int, val.split(':'))
                            # Calculate dimensions based on aspect ratio, keeping max dimension <= 1024
                            # or just use a base size. Let's aim for ~1MP total pixels or max 1280 side
                            base = 1024
                            if w > h:
                                args['width'] = 1280
                                args['height'] = int(1280 * (h/w))
                            else:
                                args['height'] = 1280
                                args['width'] = int(1280 * (w/h))
                            
                            # Align to 8
                            args['width'] = (args['width'] // 8) * 8
                            args['height'] = (args['height'] // 8) * 8
                            
                            i += 2
                            continue
                        except:
                            pass
            
            prompt_parts.append(part)
            i += 1
            
        args['prompt'] = ' '.join(prompt_parts)
        return args

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle commands"""
        message_text = update.message.text
        
        # Check if this is our command
        if not message_text.startswith('/img'):
            return False
        
        # Extract raw text after command
        raw_text = message_text[4:].strip()
        
        if not raw_text:
            await update.message.reply_text(
                "Please provide a prompt!\n\n"
                "Usage: /img [--ar 16:9] [--steps 50] <prompt>\n"
                "Example: /img --ar 16:9 A golden cat playing in the garden"
            )
            return True
        
        # Parse args
        try:
            parsed = self._parse_args(raw_text)
        except Exception as e:
             await update.message.reply_text(f"❌ Error parsing arguments: {e}")
             return True

        if not parsed['prompt']:
             await update.message.reply_text("Please provide a prompt!")
             return True
        
        await self._generate_and_send(update, parsed)
        return True
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle regular text messages as prompts (uses defaults)"""
        prompt = update.message.text.strip()
        
        if not prompt:
            return False
        
        # Use defaults
        args = {
            'width': self.default_width,
            'height': self.default_height,
            'steps': self.default_steps,
            'prompt': prompt
        }
        
        await self._generate_and_send(update, args)
        return True
    
    async def _generate_and_send(self, update: Update, args: dict):
        """Generate image and send to user"""
        prompt = args['prompt']
        width = args['width']
        height = args['height']
        steps = args['steps']
        
        # Send status message
        status_message = await update.message.reply_text(
            f"🎨 Generating image...\n"
            f"📝 Prompt: {prompt}\n"
            f"📐 Size: {width}x{height}\n"
            f"Please wait..."
        )
        
        async def tg_callback(msg: str):
            try:
                await status_message.edit_text(f"🎨 Generating...\n{msg}")
            except:
                pass

        try:
            # Generate image (awaiting async call)
            image_bio = await self.api_client.generate_image(
                prompt=prompt,
                model_id=self.model_id,
                width=width,
                height=height,
                steps=steps,
                status_callback=tg_callback
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
            )

    def get_tool_definition(self) -> Dict[str, Any]:
        """Get tool definition for Claude agent"""
        return {
            "name": "generate_image",
            "description": "Generate an AI image based on a text prompt. ONLY use this tool when the user EXPLICITLY requests to generate, draw, paint, or create an image. Keywords to look for: '画', '生成图', '生成一张', 'draw', 'generate image', 'create picture'. Do NOT use this tool when user is just chatting, sharing observations, or describing something beautiful - respond conversationally instead.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the image to generate"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Width of the image (default 1024)",
                        "enum": [512, 768, 1024, 1280]
                    },
                    "height": {
                        "type": "integer",
                        "description": "Height of the image (default 1024)",
                        "enum": [512, 768, 1024, 1280]
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of inference steps (default 30, max 50)"
                    }
                },
                "required": ["prompt"]
            }
        }

    async def handle_tool_call(self, args: Dict[str, Any], update: Update, context: Any = None) -> str:
        """Handle execution of the tool - works for both Telegram and Web"""
        width = args.get('width', self.default_width)
        height = args.get('height', self.default_height)
        steps = args.get('steps', self.default_steps)
        
        plugin_args = {
            'width': int(width) if width else self.default_width,
            'height': int(height) if height else self.default_height,
            'steps': int(steps) if steps else self.default_steps,
            'prompt': args['prompt']
        }
        
        # Detect if we have a callback in context (passed by AgentCore)
        status_callback = None
        if isinstance(context, dict) and 'status_callback' in context:
            status_callback = context['status_callback']

        # Check if we have a Telegram update
        if update is not None and hasattr(update, 'message') and update.message:
            await self._generate_and_send(update, plugin_args)
            return f"Image successfully displayed in chat."
        else:
            # Web or other context
            try:
                self.logger.info(f"Generating image for web context: {plugin_args['prompt']}")
                
                # Generate image
                image_bio = await self.api_client.generate_image(
                    prompt=plugin_args['prompt'],
                    model_id=self.model_id,
                    width=plugin_args['width'],
                    height=plugin_args['height'],
                    steps=plugin_args['steps'],
                    status_callback=status_callback
                )
                
                if image_bio:
                    import os, uuid, datetime
                    images_dir = "static/images" # Public static dir
                    os.makedirs(images_dir, exist_ok=True)
                    
                    filename = f"img_{uuid.uuid4().hex[:8]}.jpg"
                    filepath = os.path.join(images_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(image_bio.read())
                    
                    image_url = f"/images/{filename}"
                    return f"✨ Image Generated!\n![Result]({image_url})"
                else:
                    return "Failed: Image data is empty."
                    
            except Exception as e:
                self.logger.error(f"Error in web image generation: {e}")
                return f"Error: {str(e)}"


