## Why
Transform our command-based Telegram bot into an intelligent AI assistant using the Claude Code SDK, enabling natural language interactions, user-specific memory, and custom skill capabilities while maintaining backward compatibility.

## What Changes
- **Core Architecture**: Replace command parser with Claude Agent for natural language understanding
- **Session Management**: Add persistent user sessions with memory and context retention
- **Tool Registry**: Implement centralized tool/skill management system
- **Memory System**: Add JSON-based memory storage with future SQLite migration path
- **Skill System**: Enable secure execution of user-uploaded custom skills
- **Hybrid Mode**: Maintain backward compatibility with existing command system
- **BREAKING**: Major architectural transformation requiring new dependencies and entry point

## Impact
- **Affected specs**:
  - `agent-architecture` (NEW)
  - `session-management` (NEW)
  - `tool-registry` (NEW)
  - `memory-system` (NEW)
  - `skill-system` (NEW)
- **Affected code**:
  - Core bot architecture (`telegram_bot.py`)
  - Plugin system will be adapted to Tool Registry
  - New dependencies: anthropic, aiofiles, pydantic
  - New entry point: `telegram_claude_agent.py`