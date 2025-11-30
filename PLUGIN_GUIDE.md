# Plugin Development Guide

## Overview
The Personal Assistant Bot uses a plugin-based architecture. Each tool/feature is a self-contained plugin that can be easily added or removed.

## Creating a New Plugin

### 1. Create Plugin Directory
```bash
mkdir -p plugins/your_plugin_name
touch plugins/your_plugin_name/__init__.py
touch plugins/your_plugin_name/plugin.py
```

### 2. Implement Plugin Class
Create `plugins/your_plugin_name/plugin.py`:

```python
from bot.base_plugin import BasePlugin
from telegram import Update
from telegram.ext import ContextTypes

class YourPlugin(BasePlugin):
    """Your plugin description"""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        # Initialize your plugin
    
    @property
    def name(self) -> str:
        return "your_plugin_name"
    
    @property
    def description(self) -> str:
        return "What your plugin does"
    
    @property
    def commands(self):
        return [
            {
                'command': 'yourcommand',
                'description': 'Command description'
            }
        ]
    
    async def setup(self) -> bool:
        """Initialize plugin (optional)"""
        self.logger.info(f"{self.name} plugin initialized")
        return True
    
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle commands"""
        message_text = update.message.text
        
        if not message_text.startswith('/yourcommand'):
            return False
        
        # Process command
        await update.message.reply_text("Command processed!")
        return True
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle regular messages (optional)"""
        # Return True if handled, False otherwise
        return False
```

### 3. Restart Bot
The plugin will be auto-discovered and loaded on bot restart:
```bash
./run.sh bot
```

## Plugin Structure

### Required Methods
- `name`: Unique plugin identifier
- `description`: What the plugin does
- `commands`: List of commands (can be empty)
- `handle_command()`: Process commands
- `setup()`: Initialize plugin (return False to disable)

### Optional Methods
- `handle_message()`: Process non-command messages
- `shutdown()`: Cleanup on bot shutdown

## Accessing Configuration
```python
from utils.config import get_config_value

api_key = get_config_value(self.config, 'section', 'key', 'fallback')
```

## Using Shared Utilities
```python
from utils.api_client import ModelScopeClient

client = ModelScopeClient(api_key, base_url, self.logger)
```

## Example Plugins

### Simple Command Plugin
```python
async def handle_command(self, update, context):
    if update.message.text.startswith('/hello'):
        await update.message.reply_text("Hello!")
        return True
    return False
```

### Message Processing Plugin
```python
async def handle_message(self, update, context):
    text = update.message.text.lower()
    if 'help' in text:
        await update.message.reply_text("How can I help?")
        return True
    return False
```

## Best Practices
1. **Error Handling**: Always wrap API calls in try-except
2. **Logging**: Use `self.logger` for debugging
3. **Config**: Store sensitive data in `config.ini`
4. **Return Values**: Return `True` if handled, `False` otherwise
5. **User Feedback**: Provide clear status messages
