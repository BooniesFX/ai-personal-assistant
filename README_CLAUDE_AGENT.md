# Claude Agent Implementation

This document describes the new Claude Agent architecture that enhances the existing Telegram bot with natural language understanding and AI capabilities.

## Overview

The Claude Agent extends the traditional command-based bot with:

1. **Natural Language Understanding** - Process user requests in plain English
2. **Persistent Memory** - Remember user preferences and conversation context
3. **Tool Integration** - Execute existing plugins as AI tools
4. **Hybrid Mode** - Seamlessly combine traditional commands with AI interactions

## Components

### Core Components

- `agents/core/client.py` - Claude API wrapper with streaming and error handling
- `agents/core/bot.py` - Main Claude Agent controller
- `telegram_claude_agent.py` - New entry point for hybrid bot

### Session Management

- `agents/session/manager.py` - User session lifecycle and context management
- Persistent sessions with automatic cleanup
- Context window management (last 20 messages)

### Memory System

- `agents/memory/store.py` - JSON-based memory storage
- User preferences and interaction history
- Automatic backup and recovery

### Tool Registry

- `agents/tools/registry.py` - Centralized tool management
- `agents/tools/adapters.py` - Plugin-to-tool adapters
- Dynamic tool loading and execution

## Getting Started

### Prerequisites

1. Anthropic API key for Claude access
2. Updated dependencies (see `pyproject.toml`)

### Configuration

Add to your `.env` file:
```env
ANTHROPIC_API_KEY=your_claude_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

### Running the Agent

```bash
python telegram_claude_agent.py
```

## Usage

Users can interact in two ways:

### Natural Language Mode
Just talk naturally:
> "Can you generate an image of a cat wearing a hat?"

### Command Mode
Traditional slash commands still work:
> `/img cat wearing hat`

## Development

### Adding New Tools

1. Create tool definition with input schema
2. Implement async handler function
3. Register with `ToolRegistry`

### Extending Plugins

Existing plugins are automatically adapted using `PluginAdapter`.

## Architecture Diagram

```
┌─────────────────────┐
│  Telegram Client    │
├─────────────────────┤
│  Hybrid Bot         │
├─────────────────────┤
│  Claude Agent       │
│  ├── Session Mgr    │
│  ├── Memory Store   │
│  ├── Tool Registry  │
│  └── Claude Client  │
├─────────────────────┤
│  Plugin System      │
└─────────────────────┘
```