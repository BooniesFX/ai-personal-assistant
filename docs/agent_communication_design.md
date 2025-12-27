# design: External Agent Communication Protocols

This document outlines how `ai-personal-assistant` will communicate with external agents (like the `claude` CLI, Hapi servers, or other independent agent processes).

## 1. Subprocess / STDIO (The "Hapi" Way)
This method is used for local CLI agents (e.g., `claude`, `gh`, or custom python scripts).

### Mechanism
- **Spawn**: The main agent spawns the external agent as a subprocess using `asyncio.create_subprocess_exec`.
- **Input**: Send user prompts via `stdin`.
- **Output**: Stream output from `stdout`.
- **Termination**: Send SIGINT/SIGTERM or special exit command.

### Protocol Detail
```python
# Conceptual implementation
process = await asyncio.create_subprocess_exec(
    "claude", 
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE
)

# Send message
process.stdin.write(b"Review this code.\n")
await process.stdin.drain()

# Read response
while True:
    line = await process.stdout.readline()
    if not line: break
    yield line
```

## 2. Model Context Protocol (MCP) (The "Native" Way)
If the external agent implements the **MCP Server** spec, we can connect natively using the existing `MCPClientManager`.

### Mechanism
- **Transport**: Stdio or SSE (Server-Sent Events).
- **Structure**: The external agent exposes "Tools" or "Prompts".
- **Interaction**: The main agent "calls" the external agent as a tool.

## 3. HTTP / REST API (The "Service" Way)
For agents running on other servers (e.g., a Hapi server running on another machine).

### Mechanism
- **Request**: POST `/api/chat` with JSON payload `{"message": "..."}`.
- **Response**: JSON or Streaming Text.

---

## Proposed Implementation: `ExternalAgentTool`

We will create a universal `ExternalAgentTool` that can be configured to wrap any of these methods.

### Config Structure
```yaml
agents:
  - name: "coding_assistant"
    type: "subprocess"
    command: ["claude"]
    description: "Use this agent for complex coding tasks."
    
  - name: "research_agent"
    type: "http"
    url: "http://localhost:8080/chat"
    description: "Use this agent for web research."
```

### The Tool Interface
To the Main Agent (LLM), this looks like just another tool:
```json
{
  "name": "delegate_to_coding_assistant",
  "description": "Delegate a complex coding task to the dedicated coding assistant CLI.",
  "parameters": {
    "type": "object",
    "properties": {
      "instruction": { "type": "string", "description": "The full instruction to pass to the agent." }
    }
  }
}
```

## FAQ: How data flows?
1. **User** asks Main Agent: "Refactor this file."
2. **Main Agent** decides: "I should use the `coding_assistant` tool."
3. **Main Agent** calls tool: `delegate_to_coding_assistant(instruction="Refactor...")`.
4. **Tool Logic**:
   - Spawns `claude` process (if not running).
   - Writes "Refactor..." to `claude`'s stdin.
   - Captures `claude`'s stdout.
   - Returns the stdout text as the "Tool Result".
5. **Main Agent** sees the result and summarizes it for the user.
