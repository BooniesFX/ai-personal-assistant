#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OPS Reminder Scheduler
Background task to check and send reminders
"""

import asyncio
from datetime import datetime
from typing import Optional
from telegram import Bot


class ReminderScheduler:
    """Background scheduler for OPS reminders"""
    
    def __init__(self, storage, bot: Bot, logger=None, check_interval: int = 3600):
        """
        Initialize scheduler
        
        Args:
            storage: OPSStorage instance
            bot: Telegram Bot instance
            logger: Logger instance
            check_interval: Check interval in seconds (default: 3600 = 1 hour)
        """
        self.storage = storage
        self.bot = bot
        self.logger = logger
        self.check_interval = check_interval
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            if self.logger:
                self.logger.warning("Reminder scheduler already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        
        if self.logger:
            self.logger.info(f"Reminder scheduler started (check every {self.check_interval}s)")
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        if self.logger:
            self.logger.info("Reminder scheduler stopped")
    
    async def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self._check_and_send_reminders()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in reminder scheduler: {e}")
            
            # Wait for next check
            await asyncio.sleep(self.check_interval)
    
    async def _check_and_send_reminders(self):
        """Check for pending reminders and send them"""
        pending = self.storage.get_pending_reminders()
        
        if not pending:
            return
        
        if self.logger:
            self.logger.info(f"Found {len(pending)} pending reminders")
        
        for reminder in pending:
            try:
                await self._send_reminder(reminder)
                
                # Mark as sent
                self.storage.mark_reminder_sent(
                    reminder['user_id'],
                    reminder['card_id']
                )
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to send reminder {reminder['card_id']}: {e}")
    
    async def _send_reminder(self, reminder: dict):
        """Send a reminder to user"""
        user_id = reminder['user_id']
        card_id = reminder['card_id']
        
        # Get card details
        card = self.storage.get_card(card_id)
        if not card:
            if self.logger:
                self.logger.warning(f"Card {card_id} not found for reminder")
            return
        
        # Get selected decision
        decision_id = card.get('selected_decision')
        if not decision_id:
            return
        
        decision = next(
            (d for d in card.get('decisions', []) if d['id'] == decision_id),
            None
        )
        
        if not decision:
            return
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Build reminder message
        message = (
            f"⏰ *每日复盘提醒*\n\n"
            f"昨天你选择了决策：\n"
            f"*{decision_id}*: {decision['text']}\n\n"
            f"请反馈执行结果："
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ 已完成", callback_data=f"ops_fb_done:{card_id}"),
                InlineKeyboardButton("❌ 未完成", callback_data=f"ops_fb_fail:{card_id}")
            ]
        ]
        
        # Send message
        await self.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        if self.logger:
            self.logger.info(f"Sent reminder to user {user_id} for card {card_id}")
