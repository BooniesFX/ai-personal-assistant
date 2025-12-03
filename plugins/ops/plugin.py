#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OPS Plugin
Daily Practice System for training observation, abstraction, structuring, and decision-making
"""

from bot.base_plugin import BasePlugin
from plugins.ops.ai_client import OPSAIClient
from plugins.ops.storage import OPSStorage
from plugins.ops.scheduler import ReminderScheduler
from utils.config import get_config_value
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from datetime import datetime, timedelta


class OPSPlugin(BasePlugin):
    """Plugin for OPS daily practice system"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        
        # Get config
        api_key = get_config_value(config, 'ops', 'llm_api_key')
        base_url = get_config_value(config, 'ops', 'llm_base_url', 'https://api.openai.com/v1')
        model = get_config_value(config, 'ops', 'llm_model', 'gpt-4o-mini')
        
        # Initialize components
        self.ai_client = OPSAIClient(api_key, base_url, model, logger)
        self.storage = OPSStorage()
        self.scheduler = None  # Will be initialized in setup
    
    @property
    def name(self) -> str:
        return "ops"
    
    @property
    def description(self) -> str:
        return "🎯 OPS - 每日能力训练系统"
    
    @property
    def commands(self):
        return [
            {
                'command': 'ops',
                'description': '记录问题并获得AI分析和决策建议'
            },
            {
                'command': 'ops_feedback',
                'description': '反馈决策执行结果'
            },
            {
                'command': 'ops_review',
                'description': '查看本周复盘'
            },
            {
                'command': 'ops_stats',
                'description': '查看个人进度统计'
            }
        ]
    
    async def setup(self) -> bool:
        """Setup plugin"""
        if not self.ai_client.api_key:
            self.logger.error("OPS LLM API Key not configured")
            return False
        
        self.logger.info("OPS plugin initialized")
        return True
    
    async def post_init(self, application):
        """Post-initialization hook to start scheduler"""
        # Initialize scheduler with bot instance
        self.scheduler = ReminderScheduler(
            storage=self.storage,
            bot=application.bot,
            logger=self.logger,
            check_interval=3600  # Check every hour
        )
        await self.scheduler.start()
        self.logger.info("OPS reminder scheduler started")
    
    async def shutdown(self):
        """Shutdown hook to stop scheduler"""
        if self.scheduler:
            await self.scheduler.stop()
            self.logger.info("OPS reminder scheduler stopped")
    
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle commands"""
        message_text = update.effective_message.text
        
        if message_text.startswith('/ops_feedback'):
            await self._handle_feedback(update, context)
            return True
        elif message_text.startswith('/ops_review'):
            await self._handle_review(update, context)
            return True
        elif message_text.startswith('/ops_stats'):
            await self._handle_stats(update, context)
            return True
        elif message_text.startswith('/ops'):
            await self._handle_ops(update, context)
            return True
        
        return False
    
    async def _handle_ops(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ops command"""
        user_id = update.effective_user.id
        message_text = update.effective_message.text
        
        # Extract problem description
        problem = message_text[4:].strip()
        
        if not problem:
            await update.effective_message.reply_text(
                "📝 请描述你遇到的问题或不爽的事情\n\n"
                "用法: /ops <问题描述>\n"
                "例如: /ops 又被会议拖走，今天任务做不完，心烦"
            )
            return
        
        # Send processing message
        status_msg = await update.effective_message.reply_text(
            "🤔 正在分析你的问题...\n请稍候..."
        )
        
        try:
            # Analyze problem with AI
            analysis = self.ai_client.analyze_problem(problem)
            
            # Create daily card
            card = {
                'user_id': user_id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'input': problem,
                'category': analysis['category'],
                'essence': analysis['essence'],
                'gaps': analysis['gaps'],
                'decisions': analysis['decisions']
            }
            
            card_id = self.storage.save_card(card)
            
            # Build response message
            response = self._format_analysis(analysis)
            
            # Build decision keyboard
            keyboard = []
            for decision in analysis['decisions']:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{decision['id']}: {decision['text'][:30]}...",
                        callback_data=f"ops_select:{card_id}:{decision['id']}"
                    )
                ])
            keyboard.append([
                InlineKeyboardButton("❌ 暂不执行", callback_data=f"ops_skip:{card_id}")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Delete status message
            await status_msg.delete()
            
            # Send analysis
            await update.effective_message.reply_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error(f"Error in OPS analysis: {e}")
            await status_msg.edit_text(
                f"❌ 分析失败: {str(e)}\n\n"
                "请稍后重试或联系管理员。"
            )
    
    async def _handle_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ops_review command"""
        user_id = update.effective_user.id
        
        # Get this week's cards
        cards = self.storage.get_week_cards(user_id, week_offset=0)
        
        if not cards:
            await update.effective_message.reply_text(
                "📊 本周还没有记录\n\n"
                "使用 /ops <问题> 开始记录你的问题和决策"
            )
            return
        
        # Generate review
        review = self._generate_weekly_review(cards)
        
        await update.effective_message.reply_text(
            review,
            parse_mode='Markdown'
        )
    
    async def _handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ops_stats command"""
        user_id = update.effective_user.id
        
        # Get recent cards
        cards = self.storage.get_user_cards(user_id, limit=30)
        
        if not cards:
            await update.effective_message.reply_text(
                "📊 还没有数据\n\n"
                "使用 /ops <问题> 开始你的能力训练"
            )
            return
        
        # Calculate stats
        stats = self._calculate_stats(cards)
        
        await update.effective_message.reply_text(
            stats,
            parse_mode='Markdown'
        )
    
    async def _handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ops_feedback command"""
        user_id = update.effective_user.id
        message_text = update.effective_message.text
        
        # Parse: /ops_feedback <card_id> <completed/未完成> <result>
        parts = message_text.split(maxsplit=3)
        
        if len(parts) < 4:
            await update.effective_message.reply_text(
                "📝 请提供反馈信息\n\n"
                "用法: /ops_feedback <卡片ID> <已完成/未完成> <结果描述>\n"
                "例如: /ops_feedback abc123 已完成 设置成功，今天专注了2小时"
            )
            return
        
        _, card_id, status, result = parts
        completed = status in ['已完成', '完成', 'done', 'yes']
        
        # Get card
        card = self.storage.get_card(card_id)
        if not card:
            await update.effective_message.reply_text("❌ 找不到该卡片")
            return
        
        if card.get('user_id') != user_id:
            await update.effective_message.reply_text("❌ 这不是你的卡片")
            return
        
        # Update feedback
        self.storage.update_card(card_id, {
            'feedback': {
                'completed': completed,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
        })
        
        # Send confirmation
        emoji = "✅" if completed else "📝"
        await update.effective_message.reply_text(
            f"{emoji} 反馈已记录！\n\n"
            f"状态: {'已完成' if completed else '未完成'}\n"
            f"结果: {result}\n\n"
            "继续加油！💪"
        )
    
    def _format_analysis(self, analysis: dict) -> str:
        """Format analysis result for display"""
        msg = "🎯 *问题分析*\n\n"
        
        # Category
        msg += f"📂 *分类*: {', '.join(analysis['category'])}\n\n"
        
        # Essence
        msg += f"💡 *本质*: {analysis['essence']}\n\n"
        
        # Gaps
        msg += "🔍 *差距*:\n"
        for i, gap in enumerate(analysis['gaps'], 1):
            msg += f"{i}. {gap}\n"
        msg += "\n"
        
        # Decisions
        msg += "✅ *建议决策* (选择一个执行):\n\n"
        for decision in analysis['decisions']:
            msg += f"*{decision['id']}*: {decision['text']}\n"
            msg += f"   ⏱ {decision['effort']}\n\n"
        
        return msg
    
    def _generate_weekly_review(self, cards: list) -> str:
        """Generate weekly review from cards"""
        msg = "📊 *本周复盘*\n\n"
        
        # Basic stats
        total_cards = len(cards)
        completed = sum(1 for c in cards if c.get('feedback', {}).get('completed'))
        
        msg += f"📝 记录问题: {total_cards} 个\n"
        msg += f"✅ 完成决策: {completed} 个\n"
        msg += f"📈 完成率: {completed/total_cards*100:.0f}%\n\n"
        
        # Most common categories
        categories = {}
        for card in cards:
            for cat in card.get('category', []):
                categories[cat] = categories.get(cat, 0) + 1
        
        if categories:
            msg += "🏷 *最常见问题类型*:\n"
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]:
                msg += f"• {cat}: {count} 次\n"
            msg += "\n"
        
        # Effective decisions
        effective = [c for c in cards if c.get('feedback', {}).get('completed')]
        if effective:
            msg += "💪 *有效决策示例*:\n"
            for card in effective[:2]:
                decision_id = card.get('selected_decision')
                if decision_id:
                    decision = next((d for d in card.get('decisions', []) if d['id'] == decision_id), None)
                    if decision:
                        msg += f"• {decision['text']}\n"
            msg += "\n"
        
        msg += "🎯 *下周建议*:\n"
        msg += "继续保持每日记录，关注高频问题类型，建立系统化解决方案。"
        
        return msg
    
    def _calculate_stats(self, cards: list) -> str:
        """Calculate and format statistics"""
        msg = "📊 *个人统计*\n\n"
        
        total = len(cards)
        completed = sum(1 for c in cards if c.get('feedback', {}).get('completed'))
        
        msg += f"📝 总记录: {total}\n"
        msg += f"✅ 完成: {completed}\n"
        msg += f"📈 完成率: {completed/total*100:.0f}%\n\n"
        
        # Category distribution
        categories = {}
        for card in cards:
            for cat in card.get('category', []):
                categories[cat] = categories.get(cat, 0) + 1
        
        if categories:
            msg += "🏷 *问题分布*:\n"
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                msg += f"• {cat}: {count} ({count/total*100:.0f}%)\n"
        
        return msg
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline buttons"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('ops_select:'):
            # User selected a decision
            _, card_id, decision_id = data.split(':')
            
            # Update card
            self.storage.update_card(card_id, {
                'selected_decision': decision_id
            })
            
            # Schedule reminder
            remind_at = (datetime.now() + timedelta(hours=24)).isoformat()
            self.storage.save_reminder(query.from_user.id, card_id, remind_at)
            
            await query.edit_message_text(
                f"✅ 已选择决策 {decision_id}\n\n"
                "明天此时会提醒你反馈执行结果。\n"
                "加油！💪"
            )
            return True
        
        elif data.startswith('ops_skip:'):
            # User skipped
            _, card_id = data.split(':')
            
            await query.edit_message_text(
                "⏭ 已跳过\n\n"
                "没关系，下次再试。保持记录本身就是进步！"
            )
            return True
        
        return False
