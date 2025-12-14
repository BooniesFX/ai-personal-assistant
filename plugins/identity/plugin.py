
from telegram import Update
from telegram.ext import ContextTypes
from bot.base_plugin import BasePlugin
from agents.identity.manager import UserIdentityManager

class IdentityPlugin(BasePlugin):
    """
    Plugin for managing user identity (email binding).
    """
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.identity_manager = None
        
    @property
    def name(self) -> str:
        return "identity"
        
    @property
    def description(self) -> str:
        return "Manage unified identity (email binding)"
        
    @property
    def commands(self) -> dict:
        return {
            "email": "Bind account: /email <your@email.com> <password>",
            "whoami": "Show current bound identity"
        }
        
    async def handle_command(self, command: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        
        if command == "email":
            if not context.args or len(context.args) < 2:
                await update.message.reply_text("Usage: /email <your@email.com> <password>")
                return
                
            email = context.args[0].lower().strip()
            password = context.args[1].strip()
            
            # Basic validation
            if "@" not in email:
                await update.message.reply_text("❌ Invalid email format.")
                return
            
            # Verify password
            if not self.identity_manager.verify_access(password):
                await update.message.reply_text("❌ Incorrect password.")
                return
                
            # Bind
            self.identity_manager.bind_identity("telegram", user_id, email)
            await update.message.reply_text(f"✅ Bound successfully!\nCurrent identity: {email}")
            
        elif command == "whoami":
            email = self.identity_manager.get_email("telegram", user_id)
            if email:
                await update.message.reply_text(f"🆔 You are identified as: {email}")
            else:
                await update.message.reply_text("❓ You are currently anonymous (Telegram ID only). Use /email to bind.")
