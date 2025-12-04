#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Personal Assistant Bot Entry Point
"""

from bot.core import PersonalAssistantBot


def main():
    """Start the bot"""
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        bot = PersonalAssistantBot()
        bot.run()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease ensure you have set the required environment variables:")
        print("  - TELEGRAM_BOT_TOKEN (required)")
        print("  - MODELSCOPE_API_KEY (required)")
        print("  - ADMIN_ID (required)")
        print("\nYou can set them in a .env file or export them directly.")
        print("See .env.example for reference.")
    except Exception as e:
        print(f"Error starting bot: {e}")


if __name__ == "__main__":
    main()
