# Project Context

## Purpose
This is a Telegram-based AI personal assistant bot designed to provide intelligent automation and assistance through natural language interactions. The bot features a modular plugin architecture that enables easy extension of capabilities including AI image generation, personal development training (OPS system), and administrative functions. The project aims to evolve from traditional command-based interactions to an intelligent Agent-based system using Claude Code SDK, allowing users to communicate naturally without memorizing specific commands.

Key goals:
- Provide seamless AI assistance through Telegram
- Support multiple AI capabilities (image generation, problem analysis, decision tracking)
- Enable natural language interactions without command memorization
- Maintain extensible plugin architecture for easy feature additions
- Implement user-specific memory and personalization
- Support custom skill uploads for advanced users

## Tech Stack
- **Python 3.12+**: Modern Python with full async/await support
- **python-telegram-bot (v22.5)**: Official Telegram Bot API Python wrapper
- **asyncio**: Asynchronous programming for high concurrency
- **uv**: Modern Python package manager (faster alternative to pip)
- **Pydantic**: Data validation and settings management
- **Anthropic Claude SDK**: Core AI agent engine (planned integration)
- **ModelScope API**: AI image generation service (Z-Image-Turbo model)
- **OpenAI API**: LLM services for OPS module (GPT-4o-mini)
- **Docker**: Containerization for easy deployment
- **python-dotenv**: Environment variable management

## Project Conventions

### Code Style
- **Naming Conventions**:
  - Classes: PascalCase (e.g., `PersonalAssistantBot`, `BasePlugin`)
  - Functions/Methods: snake_case (e.g., `handle_command`, `get_user_memory`)
  - Constants: UPPER_SNAKE_CASE (e.g., `MAX_SESSIONS`, `DEFAULT_TIMEOUT`)
  - Files: lowercase_with_underscores (e.g., `plugin_manager.py`)
  - Private methods: prefix with underscore (e.g., `_validate_input`)

- **Type Annotations**: Comprehensive type hints throughout codebase
- **Documentation**: Google-style docstrings with Args, Returns, Raises sections
- **Async Patterns**: Use async/await for all I/O operations
- **Error Handling**: Specific exception types with meaningful error messages
- **Logging**: Structured logging with appropriate log levels

### Architecture Patterns
- **Plugin Architecture**: Modular design with BasePlugin abstract class
- **Manager Pattern**: Centralized managers for plugins, sessions, permissions
- **Factory Pattern**: For creating different types of skills and tools
- **Adapter Pattern**: Converting legacy plugins to Claude SDK tools
- **Repository Pattern**: For data access and storage operations
- **Strategy Pattern**: Different execution strategies for various skill types

Key architectural decisions:
- Separation of core bot logic from plugin implementations
- Async-first design for high concurrency
- Configuration-driven behavior with environment variable overrides
- File-based storage with JSON/JSONL formats (migrating to SQLite in future)
- Permission-based access control with admin overrides

### Testing Strategy
**Current State**: No automated tests present - manual testing only

**Planned Testing Approach**:
- **Unit Tests**: Individual component testing with pytest
- **Integration Tests**: Plugin-Bot API interaction testing
- **End-to-End Tests**: Full user workflow testing
- **Load Tests**: Concurrent user session testing
- **Security Tests**: Input validation and permission testing

**Test Structure**:
```
tests/
├── unit/           # Component-level tests
├── integration/    # API and service integration tests
├── e2e/           # End-to-end workflow tests
├── fixtures/      # Test data and mocks
└── conftest.py    # Pytest configuration
```

### Git Workflow
- **Branch Strategy**: Feature-based branching with descriptive names
- **Commit Convention**: Conventional Commits format
  - `feat:` New features
  - `fix:` Bug fixes
  - `docs:` Documentation updates
  - `refactor:` Code refactoring
  - `test:` Test additions/updates
  - `chore:` Maintenance tasks

- **Example Commits**:
  ```
  feat: add natural language processing for image generation
  fix: resolve session timeout handling in OPS module
  docs: update API documentation for skill upload endpoint
  refactor: simplify plugin discovery logic in PluginManager
  ```

- **Pull Request Process**: Feature branches → main branch
- **Code Review**: Required before merging to main
- **Release Tagging**: Semantic versioning (v1.2.3)

## Domain Context

### Telegram Bot Ecosystem
- **Bot Father**: Telegram's official bot management interface
- **Update Objects**: Messages, callbacks, inline queries
- **Chat Types**: Private, groups, channels, supergroups
- **User IDs vs Chat IDs**: Important distinction for permissions
- **Rate Limiting**: Telegram's flood control mechanisms

### AI/ML Service Integration
- **ModelScope**: Chinese AI model platform with image generation APIs
- **OpenAI Compatibility**: Multiple LLM providers support OpenAI API format
- **Token-based Authentication**: API keys and usage quotas
- **Async API Calls**: Non-blocking requests for better performance

### Plugin System Domain
- **Dynamic Loading**: Runtime plugin discovery and instantiation
- **Command Routing**: Mapping text commands to plugin handlers
- **Lifecycle Management**: Setup, execution, cleanup phases
- **Error Isolation**: Plugin failures shouldn't crash the bot

### OPS (Daily Practice System) Domain
- **Structured Thinking**: Observe → Abstract → Structure → Decide methodology
- **Decision Tracking**: 24-hour feedback loops for decision execution
- **Progress Analytics**: Weekly reviews and personal statistics
- **AI-powered Analysis**: Problem categorization and gap identification

## Important Constraints

### Technical Constraints
- **Telegram API Limits**: 30 messages/second to same chat, 20 messages/minute globally
- **File Size Limits**: 50MB max for downloads, photos up to 10MB
- **Memory Constraints**: Running on limited-resource platforms (Zeabur free tier)
- **Storage Limits**: File-based storage with size considerations
- **Network Reliability**: Must handle intermittent connectivity

### Business Constraints
- **Privacy Compliance**: User data protection and GDPR considerations
- **Cost Control**: Free tier limitations on cloud platforms
- **Multi-language Support**: Chinese and English mixed processing
- **Backward Compatibility**: Existing user base must not be disrupted

### Security Constraints
- **Input Validation**: All user inputs must be sanitized
- **API Key Protection**: Secrets management through environment variables
- **Permission System**: Strict access control for sensitive operations
- **Rate Limiting**: Prevent abuse and API quota exhaustion

### Operational Constraints
- **Zero-downtime Updates**: Bot must remain available during updates
- **Graceful Degradation**: Continue operating when services are down
- **Log Management**: Structured logging without exposing sensitive data
- **Error Recovery**: Automatic recovery from transient failures

## External Dependencies

### AI Services
- **ModelScope API**:
  - Endpoint: `https://api-inference.modelscope.cn/`
  - Model: `Tongyi-MAI/Z-Image-Turbo`
  - Authentication: API key header
  - Rate limits: Varies by subscription tier

- **OpenAI Compatible API**:
  - Primary: `https://api.openai.com/v1` (or custom base URL)
  - Model: `gpt-4o-mini` (configurable)
  - Authentication: Bearer token
  - Usage: OPS problem analysis and decision generation

### Infrastructure Services
- **Telegram Bot API**:
  - Webhook or polling mode
  - File storage for photos/documents
  - Inline keyboard support
  - Callback query handling

- **Docker Registry**:
  - Container image storage
  - Multi-platform builds (AMD64, ARM64)
  - Automated deployments

### Configuration Management
- **Environment Variables**:
  ```bash
  TELEGRAM_BOT_TOKEN      # Required: Bot authentication
  ADMIN_ID               # Required: Admin user ID for permissions
  MODELSCOPE_API_KEY     # Required: Image generation service
  OPS_LLM_API_KEY        # Required: LLM service for OPS module
  CLAUDE_API_KEY         # Future: Claude SDK integration

  # Optional configurations
  DEFAULT_WIDTH          # Image generation default width
  DEFAULT_HEIGHT         # Image generation default height
  DEFAULT_STEPS          # Image generation default steps
  OPS_LLM_BASE_URL       # Custom LLM endpoint
  OPS_LLM_MODEL          # LLM model selection
  ```

### Development Tools
- **uv Package Manager**: Modern Python dependency management
- **Git**: Version control with GitHub integration
- **Docker**: Local development and production deployment
- **Claude Code**: AI-assisted development environment
