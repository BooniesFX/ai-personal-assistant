# Migration Guide: From Traditional Bot to Claude Agent

This guide explains how to migrate from the traditional command-based bot to the new Claude Agent system.

## What's New

The Claude Agent introduces several enhancements:

1. **Natural Language Processing** - Users can now communicate in plain English
2. **Context Awareness** - The bot remembers previous conversations
3. **Enhanced Tool System** - Existing plugins work as AI tools
4. **Hybrid Compatibility** - Both old and new interaction methods work

## Migration Steps

### 1. Update Dependencies

```bash
uv pip install -e .
```

### 2. Configure Claude API

Add to your `.env` file:
```env
ANTHROPIC_API_KEY=your_claude_api_key_here
```

### 3. Update Entry Point

Instead of running:
```bash
python telegram_bot.py
```

Run the new hybrid bot:
```bash
python telegram_claude_agent.py
```

## Backward Compatibility

The new system maintains full backward compatibility:

- All existing commands continue to work
- Plugin system remains unchanged
- Configuration files are compatible
- User data is preserved

## New Features

### Natural Language Interaction

Users can now say things like:
- "Generate an image of a sunset"
- "Help me analyze this problem" (for OPS plugin)
- "Show me the admin commands"

### Persistent Memory

The bot now remembers:
- User preferences
- Conversation context
- Interaction history

### Enhanced Help System

The `/help` command now shows both traditional commands and AI capabilities.

## For Developers

### Plugin Adaptation

Existing plugins automatically work as tools. No changes needed for basic functionality.

### Adding New Tools

To add new Claude-specific tools:
1. Create a tool definition with input schema
2. Implement an async handler function
3. Register with the `ToolRegistry`

### Customization

You can customize:
- Claude model selection
- Session timeout duration
- Memory storage location
- Tool behavior

## Testing

To verify everything works:

```bash
python test_agents.py
```

This runs tests for all new components.

## Troubleshooting

### Common Issues

1. **Missing API Key**
   - Solution: Add `ANTHROPIC_API_KEY` to `.env`

2. **Dependency Issues**
   - Solution: Run `uv pip install -e .` again

3. **Permission Errors**
   - Solution: Ensure `data/` directory is writable

### Rollback

To revert to the traditional bot:
1. Stop `telegram_claude_agent.py`
2. Start `telegram_bot.py` as before

## Support

For issues with the migration, check:
- Logs in the console output
- Error messages in Telegram responses
- This migration guide

The hybrid approach means you can gradually adopt new features while maintaining reliability.