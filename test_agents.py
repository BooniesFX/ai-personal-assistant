#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Claude Agent components
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.core.client import ClaudeClient
from agents.memory.store import JSONMemoryStore
from agents.session.manager import SessionManager


def test_claude_client():
    """Test ClaudeClient functionality."""
    print("Testing ClaudeClient...")

    try:
        # This will fail if no API key is configured, which is expected in testing
        client = ClaudeClient()
        print("✓ ClaudeClient instantiated successfully")
        return True
    except ValueError as e:
        if "Anthropic API key not configured" in str(e):
            print("✓ ClaudeClient correctly requires API key")
            return True
        else:
            print(f"✗ Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"✗ Error instantiating ClaudeClient: {e}")
        return False


def test_memory_store():
    """Test JSONMemoryStore functionality."""
    print("Testing JSONMemoryStore...")

    try:
        # Create a test memory store
        memory = JSONMemoryStore("data/test_memory.json")

        # Test set/get
        memory.set("test_key", "test_value")
        assert memory.get("test_key") == "test_value"

        # Test user data
        memory.set_user_preference(12345, "theme", "dark")
        assert memory.get_user_preference(12345, "theme") == "dark"

        # Clean up
        if os.path.exists("data/test_memory.json"):
            os.remove("data/test_memory.json")

        print("✓ JSONMemoryStore working correctly")
        return True
    except Exception as e:
        print(f"✗ Error testing JSONMemoryStore: {e}")
        return False


async def test_session_manager():
    """Test SessionManager functionality."""
    print("Testing SessionManager...")

    try:
        # Create memory store and session manager
        memory = JSONMemoryStore("data/test_session_memory.json")
        session_manager = SessionManager(memory)

        # Test session creation
        session = await session_manager.get_or_create_session(12345, 67890)
        assert session.user_id == 12345
        assert session.chat_id == 67890

        # Test context update
        await session_manager.update_session_context(
            12345, 67890,
            {"role": "user", "content": "Hello"}
        )

        context = await session_manager.get_session_context(12345, 67890)
        assert len(context) == 1
        assert context[0]["content"] == "Hello"

        # Test preferences
        await session_manager.set_preference(12345, 67890, "language", "en")
        lang = await session_manager.get_preference(12345, 67890, "language")
        assert lang == "en"

        # Clean up
        if os.path.exists("data/test_session_memory.json"):
            os.remove("data/test_session_memory.json")

        print("✓ SessionManager working correctly")
        return True
    except Exception as e:
        print(f"✗ Error testing SessionManager: {e}")
        return False


async def main():
    """Run all tests."""
    print("Running Claude Agent component tests...\n")

    results = []

    # Test ClaudeClient
    result1 = test_claude_client()
    results.append(result1)

    # Test MemoryStore
    result2 = test_memory_store()
    results.append(result2)

    # Test SessionManager
    result3 = await test_session_manager()
    results.append(result3)

    # Summary
    passed = sum(results)
    total = len(results)

    print(f"\nTest Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)