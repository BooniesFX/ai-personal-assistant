#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Personal Assistant Bot Entry Point
"""

from bot.core import PersonalAssistantBot


def main():
    """Start the bot"""
    try:
        bot = PersonalAssistantBot()
        bot.run()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please check your config.ini or environment variables")
    except Exception as e:
        print(f"Error starting bot: {e}")


if __name__ == "__main__":
    main()
