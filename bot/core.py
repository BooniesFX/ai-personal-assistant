#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot Core
Main bot application with plugin system
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bot.plugin_manager import PluginManager
from utils.config import load_config, get_config_value
from utils.permissions import PermissionManager


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class PersonalAssistantBot:
    """Personal Assistant Bot with Plugin System"""
    
    def __init__(self, config_file='config.ini'):
        """
        Initialize bot
        
        Args:
            config_file: Path to config file
        """
        self.config = load_config(config_file)
        self.logger = logger
        
        # Get bot token
        self.bot_token = get_config_value(self.config, 'telegram', 'bot_token')
        
        if not self.bot_token:
            raise ValueError("Telegram Bot Token not configured!")
        
        # Initialize permission manager
        self.permission_manager = PermissionManager()
        
        # Initialize plugin manager
        self.plugin_manager = PluginManager(self.config, self.logger)
        
        # Create application
        self.application = Application.builder().token(self.bot_token).build()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        await update.message.reply_html(
            f"Hi {user.mention_html()}! 👋\n\n"
            f"I'm your Personal Assistant Bot with multiple tools!\n\n"
            f"Use /help to see all available commands."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = self.plugin_manager.get_help_text()
        help_text += "\n*General Commands:*\n"
        help_text += "/start - Start the bot\n"
        help_text += "/help - Show this help message"
        
        await update.message.reply_text(help_text)
    
    async def check_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user/chat is allowed"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get admin ID
        admin_id = get_config_value(self.config, 'auth', 'admin_id')
        try:
            admin_id = int(admin_id) if admin_id else None
        except:
            admin_id = None
            
        # Admin is always allowed
        if admin_id and user_id == admin_id:
            return True
            
        # Check whitelist
        if chat_id == user_id: # Private chat
            if self.permission_manager.is_allowed_user(user_id):
                return True
            # Notify user and admin
            await update.effective_message.reply_text("⛔️ You are not authorized to use this bot.\nRequest sent to admin.")
            if admin_id:
                try:
                    await context.bot.send_message(
                        admin_id, 
                        f"🔔 **Access Request**\nUser: {update.effective_user.mention_html()} (`{user_id}`)\n"
                        f"Use `/allow {user_id}` to approve.",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    self.logger.error(f"Failed to notify admin: {e}")
            return False
        else: # Group chat
            if self.permission_manager.is_allowed_group(chat_id):
                return True
            # Only notify once per group session (optional, for now just ignore or reply once)
            # To avoid spam, we might just ignore, or reply only to commands
            # Let's reply to commands only
            if update.effective_message.text and update.effective_message.text.startswith('/'):
                 await update.effective_message.reply_text("⛔️ This group is not authorized.\nAdmin must approve this group.")
                 if admin_id:
                    try:
                        await context.bot.send_message(
                            admin_id,
                            f"🔔 **Group Access Request**\nGroup: {update.effective_chat.title} (`{chat_id}`)\n"
                            f"Invited by: {update.effective_user.mention_html()}\n"
                            f"Use `/allow {chat_id}` to approve.",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
            return False

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route commands to appropriate plugins"""
        # Check permissions first
        if not await self.check_permissions(update, context):
            return

        command = update.effective_message.text.split()[0][1:]  # Remove leading /
        
        # Get command map
        command_map = self.plugin_manager.get_all_commands()
        
        if command in command_map:
            plugin = command_map[command]
            try:
                handled = await plugin.handle_command(update, context)
                if not handled:
                    await update.effective_message.reply_text(
                        f"Command /{command} could not be processed. Try /help for usage."
                    )
            except Exception as e:
                self.logger.error(f"Error handling command /{command}: {e}")
                await update.effective_message.reply_text(
                    f"❌ Error processing command: {str(e)}"
                )
        else:
            await update.effective_message.reply_text(
                f"Unknown command: /{command}\n"
                f"Use /help to see available commands."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route messages to plugins"""
        # Check permissions first
        if not await self.check_permissions(update, context):
            return

        # Try each plugin until one handles it
        for plugin in self.plugin_manager.plugins:
            if plugin.enabled:
                try:
                    handled = await plugin.handle_message(update, context)
                    if handled:
                        return
                except Exception as e:
                    self.logger.error(f"Error in plugin {plugin.name}: {e}")
        
        # If no plugin handled it, send default message
        await update.effective_message.reply_text(
            "I'm not sure how to help with that. Try /help to see what I can do!"
        )
    
    async def post_init(self, application):
        """Post-initialization hook"""
        # Store permission manager in bot_data for plugins to access
        application.bot_data['permission_manager'] = self.permission_manager
        
        # Load plugins
        await self.plugin_manager.load_plugins()
        self.logger.info(f"Loaded {len(self.plugin_manager.plugins)} plugins")
        
        # Call post_init on plugins that have it
        for plugin in self.plugin_manager.plugins:
            if hasattr(plugin, 'post_init'):
                try:
                    await plugin.post_init(application)
                except Exception as e:
                    self.logger.error(f"Error in {plugin.name} post_init: {e}")
    
    async def post_shutdown(self, application):
        """Post-shutdown hook"""
        await self.plugin_manager.shutdown_plugins()
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        # Core commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Plugin commands (catch-all for any command)
        self.application.add_handler(
            MessageHandler(filters.COMMAND, self.handle_command)
        )
        
        # Regular messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Callback queries (for inline buttons)
        from telegram.ext import CallbackQueryHandler
        self.application.add_handler(
            CallbackQueryHandler(self.handle_callback)
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route callback queries to plugins"""
        query = update.callback_query
        
        # Try each plugin until one handles it
        for plugin in self.plugin_manager.plugins:
            if plugin.enabled and hasattr(plugin, 'handle_callback'):
                try:
                    handled = await plugin.handle_callback(update, context)
                    if handled:
                        return
                except Exception as e:
                    self.logger.error(f"Error in plugin {plugin.name} callback: {e}")
        
        # If no plugin handled it, answer the query
        await query.answer("未知操作")
    
    def run(self):
        """Start the bot"""
        self.logger.info("Starting Personal Assistant Bot...")
        
        # Setup handlers
        self.setup_handlers()
        
        # Add initialization and shutdown hooks
        self.application.post_init = self.post_init
        self.application.post_shutdown = self.post_shutdown
        
        # Run bot
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
