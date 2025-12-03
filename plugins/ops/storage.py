#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OPS Storage
Data persistence for daily cards and feedback
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid


class OPSStorage:
    """Storage manager for OPS data"""
    
    def __init__(self, data_dir: str = "data/ops"):
        """
        Initialize storage
        
        Args:
            data_dir: Base directory for OPS data
        """
        self.data_dir = data_dir
        self.cards_dir = os.path.join(data_dir, "cards")
        self.reminders_file = os.path.join(data_dir, "reminders.json")
        
        # Ensure directories exist
        os.makedirs(self.cards_dir, exist_ok=True)
    
    def save_card(self, card: Dict) -> str:
        """
        Save a daily card
        
        Args:
            card: Card data
            
        Returns:
            Card ID
        """
        # Generate ID if not present
        if 'id' not in card:
            card['id'] = str(uuid.uuid4())
        
        # Add timestamp if not present
        if 'created_at' not in card:
            card['created_at'] = datetime.now().isoformat()
        
        # Generate filename: YYYY-MM-DD_<id>.json
        date = card.get('date', datetime.now().strftime('%Y-%m-%d'))
        filename = f"{date}_{card['id']}.json"
        filepath = os.path.join(self.cards_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        
        return card['id']
    
    def get_card(self, card_id: str) -> Optional[Dict]:
        """
        Get a card by ID
        
        Args:
            card_id: Card ID
            
        Returns:
            Card data or None
        """
        # Search for file with this ID
        for filename in os.listdir(self.cards_dir):
            if filename.endswith(f"_{card_id}.json"):
                filepath = os.path.join(self.cards_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return None
    
    def update_card(self, card_id: str, updates: Dict) -> bool:
        """
        Update a card
        
        Args:
            card_id: Card ID
            updates: Fields to update
            
        Returns:
            Success status
        """
        card = self.get_card(card_id)
        if not card:
            return False
        
        card.update(updates)
        self.save_card(card)
        return True
    
    def get_user_cards(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get recent cards for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of cards
            
        Returns:
            List of cards (newest first)
        """
        cards = []
        for filename in sorted(os.listdir(self.cards_dir), reverse=True):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.cards_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                card = json.load(f)
                if card.get('user_id') == user_id:
                    cards.append(card)
                    if len(cards) >= limit:
                        break
        
        return cards
    
    def get_week_cards(self, user_id: int, week_offset: int = 0) -> List[Dict]:
        """
        Get cards for a specific week
        
        Args:
            user_id: User ID
            week_offset: 0 for current week, -1 for last week, etc.
            
        Returns:
            List of cards for that week
        """
        from datetime import timedelta
        
        # Calculate week start/end
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday() + 7 * abs(week_offset))
        week_end = week_start + timedelta(days=6)
        
        cards = []
        for filename in os.listdir(self.cards_dir):
            if not filename.endswith('.json'):
                continue
            
            # Parse date from filename
            try:
                date_str = filename.split('_')[0]
                card_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                if week_start <= card_date <= week_end:
                    filepath = os.path.join(self.cards_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        card = json.load(f)
                        if card.get('user_id') == user_id:
                            cards.append(card)
            except (ValueError, IndexError):
                continue
        
        return sorted(cards, key=lambda x: x.get('date', ''))
    
    def save_reminder(self, user_id: int, card_id: str, remind_at: str):
        """
        Save a reminder
        
        Args:
            user_id: User ID
            card_id: Card ID
            remind_at: ISO timestamp
        """
        reminders = self._load_reminders()
        
        if str(user_id) not in reminders:
            reminders[str(user_id)] = []
        
        reminders[str(user_id)].append({
            'card_id': card_id,
            'remind_at': remind_at,
            'sent': False
        })
        
        self._save_reminders(reminders)
    
    def get_pending_reminders(self) -> List[Dict]:
        """
        Get all pending reminders
        
        Returns:
            List of pending reminders
        """
        reminders = self._load_reminders()
        now = datetime.now().isoformat()
        
        pending = []
        for user_id, user_reminders in reminders.items():
            for reminder in user_reminders:
                if not reminder.get('sent') and reminder['remind_at'] <= now:
                    pending.append({
                        'user_id': int(user_id),
                        **reminder
                    })
        
        return pending
    
    def mark_reminder_sent(self, user_id: int, card_id: str):
        """Mark a reminder as sent"""
        reminders = self._load_reminders()
        
        if str(user_id) in reminders:
            for reminder in reminders[str(user_id)]:
                if reminder['card_id'] == card_id:
                    reminder['sent'] = True
        
        self._save_reminders(reminders)
    
    def _load_reminders(self) -> Dict:
        """Load reminders from file"""
        if os.path.exists(self.reminders_file):
            with open(self.reminders_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_reminders(self, reminders: Dict):
        """Save reminders to file"""
        with open(self.reminders_file, 'w', encoding='utf-8') as f:
            json.dump(reminders, f, ensure_ascii=False, indent=2)
