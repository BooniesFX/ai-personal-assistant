#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Admin Plugin
Manage bot permissions and approvals
"""

from bot.base_plugin import BasePlugin
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ChatMemberHandler
from utils.config import get_config_value
import logging

class AdminPlugin(BasePlugin):
    """Plugin for admin management"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.admin_id = get_config_value(config, 'auth', 'admin_id')
        try:
            self.admin_id = int(self.admin_id) if self.admin_id else None
        except ValueError:
            self.logger.error("Invalid Admin ID in config")
            self.admin_id = None
            
    @property
    def name(self) -> str:
        return "admin"
    
    @property
    def description(self) -> str:
        return "🛡️ Admin Management - Manage users and groups"
    
    @property
    def commands(self):
        return [
            {
                'command': 'allow',
                'description': 'Allow a user or group ID'
            },
            {
                'command': 'block',
                'description': 'Block a user or group ID'
            },
            {
                'command': 'users',
                'description': 'List authorized users/groups'
            },
            {
                'command': 'id',
                'description': 'Get current chat/user ID'
            }
        ]
    
    async def setup(self) -> bool:
        if not self.admin_id:
            self.logger.warning("Admin Plugin: No admin_id configured!")
        return True

    def is_admin(self, user_id):
        return self.admin_id and user_id == self.admin_id

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        user_id = update.effective_user.id
        command = update.message.text.split()[0][1:]
        
        # /id command is public
        if command == 'id':
            chat_id = update.effective_chat.id
            msg = f"👤 User ID: `{user_id}`\n"
            if chat_id != user_id:
                msg += f"📢 Chat ID: `{chat_id}`"
            await update.message.reply_text(msg, parse_mode='Markdown')
            return True
            
        # Other commands are admin only
        if not self.is_admin(user_id):
            return False # Let core handle "unknown command" or ignore
            
        permission_manager = context.bot_data.get('permission_manager')
        if not permission_manager:
            await update.message.reply_text("❌ Permission Manager not loaded")
            return True
            
        args = update.message.text.split()[1:]
        
        if command == 'users':
            stats = permission_manager.get_stats()
            msg = f"📊 **Stats**\nUsers: {stats['users']}\nGroups: {stats['groups']}\n\n"
            msg += "**Users:**\n" + "\n".join(map(str, permission_manager.permissions['users']))
            msg += "\n\n**Groups:**\n" + "\n".join(map(str, permission_manager.permissions['groups']))
            await update.message.reply_text(msg, parse_mode='Markdown')
            return True
            
        if not args:
            await update.message.reply_text(f"Usage: /{command} <id>")
            return True
            
        try:
            target_id = int(args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid ID format")
            return True
            
        if command == 'allow':
            # Simple heuristic: negative is group, positive is user
            if target_id < 0:
                if permission_manager.add_group(target_id):
                    await update.message.reply_text(f"✅ Group {target_id} allowed")
                    # Try to notify group
                    try:
                        await context.bot.send_message(target_id, "✅ This group has been approved by admin!")
                    except:
                        pass
                else:
                    await update.message.reply_text(f"⚠️ Group {target_id} already allowed")
            else:
                if permission_manager.add_user(target_id):
                    await update.message.reply_text(f"✅ User {target_id} allowed")
                    try:
                        await context.bot.send_message(target_id, "✅ You have been approved by admin!")
                    except:
                        pass
                else:
                    await update.message.reply_text(f"⚠️ User {target_id} already allowed")
                    
        elif command == 'block':
            if target_id < 0:
                if permission_manager.remove_group(target_id):
                    await update.message.reply_text(f"🚫 Group {target_id} blocked")
                else:
                    await update.message.reply_text(f"⚠️ Group {target_id} not found")
            else:
                if permission_manager.remove_user(target_id):
                    await update.message.reply_text(f"🚫 User {target_id} blocked")
                else:
                    await update.message.reply_text(f"⚠️ User {target_id} not found")
                    
        return True

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        return False
