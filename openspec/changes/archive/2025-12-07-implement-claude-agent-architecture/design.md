## Context
Transforming a command-based Telegram bot into an intelligent AI assistant using Claude Code SDK. The system must maintain backward compatibility while introducing natural language understanding, persistent memory, and extensible skill execution.

### Constraints
- Must maintain existing plugin functionality during transition
- Async-first architecture to match existing codebase
- Security-first approach for skill execution
- Response time must remain under 2 seconds
- Memory system must scale from JSON to SQLite without breaking changes

### Stakeholders
- Current users expecting existing commands to work
- Development team maintaining the system
- Future contributors extending the skill ecosystem

## Goals / Non-Goals
- Goals:
  - Natural language interaction for all current functionality
  - Persistent user memory and preferences
  - Secure custom skill execution environment
  - Seamless hybrid mode for gradual migration
  - Extensible architecture for future AI capabilities
- Non-Goals:
  - Real-time multi-user collaboration
  - Voice/audio processing capabilities
  - External API integrations beyond Claude SDK
  - Complex AI reasoning chains (single-turn focused)

## Decisions
- Decision: Use Claude Code SDK as the core intelligence engine
  - Reason: Provides robust tool calling, streaming, and error handling
  - Alternative: Build custom NLP pipeline (rejected - too complex)
  - Alternative: Use Dialogflow/Lex (rejected - vendor lock-in)

- Decision: JSON memory store with SQLite migration path
  - Reason: Simple to implement, easy to debug, clear upgrade path
  - Alternative: Direct SQLite implementation (rejected - adds complexity to phase 1)
  - Alternative: External database (rejected - overkill for initial implementation)

- Decision: Plugin-to-skill adapter pattern
  - Reason: Maintains existing code investment while enabling new capabilities
  - Alternative: Rewrite all plugins (rejected - high risk, no benefit)

- Decision: Hybrid command/agent mode
  - Reason: Ensures zero disruption to existing users
  - Alternative: Fork and replace (rejected - breaking change)

## Risks / Trade-offs
- Claude SDK API stability → Mitigation: Version pinning, abstraction layer
- Performance degradation → Mitigation: Caching, streaming, performance testing
- Security vulnerabilities in skill execution → Mitigation: Sandboxing, input validation
- User adoption resistance → Mitigation: Gradual rollout, tutorials, fallback mode
- Memory system scalability → Mitigation: Clear migration path to SQLite

## Migration Plan
1. **Phase 1**: Deploy alongside existing system (no user impact)
2. **Phase 2**: Enable agent mode for power users (opt-in)
3. **Phase 3**: Default to agent mode with command fallback
4. **Phase 4**: Full migration with legacy support
5. **Rollback**: Maintain original `telegram_bot.py` as fallback

## Open Questions
- How to handle file uploads in agent mode vs command mode?
- Should memory be opt-in or opt-in with smart defaults?
- What skill validation policies are needed for security?
- How to measure success of natural language vs commands?
- Should we cache Claude responses for common queries?