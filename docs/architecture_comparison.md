# Architecture Comparison: `ai-personal-assistant` vs `tiann/hapi`

## Executive Summary
**Recommendation: DO NOT Refactor.** 

The two projects solve fundamentally different problems with different architectures.
- **Current Repo (`ai-personal-assistant`)**: A **Framework** for building a highly customizable, integrated personal assistant with granular control over state, tools, and identity.
- **`tiann/hapi`**: A **Platform/Interface** for *remotely accessing* and *running* existing third-party CLI agents (like `claude` CLI).

Redirecting the current repo to mimic `hapi` would mean abandoning the custom logic (identity, dual memory, specific plugins) in favor of running external "black box" CLI agents.

---

## Detailed Analysis

### 1. `tiann/hapi`
**Nature:** Remote Access & Orchestration Layer.
**Core Mechanism:** Wraps CLI tools (`claude`, `codex`) in a server and exposes them via Web/Telegram.
**Agent "Native Call":** It runs agents as **subprocess** commands (e.g., `pkill -f claude`, `subprocess.run(['claude'])`).
**Pros:**
- **Zero Maintenance on Logic:** Uses official CLI agents (like Anthropic's Claude Code) which are maintained by vendors.
- **Mobility:** Great for "coding from phone".
- **Isolation:** Each agent session is a process.
**Cons:**
- **Opaque State:** You cannot easily inspect the agent's internal thought process, modify its system prompt dynamically based on user state, or inject custom memory *inside* the turn loop. You are just sending text to stdin and reading stdout.
- **Limited Customization:** You are limited to what the CLI tools support.

### 2. `ai-personal-assistant` (Current)
**Nature:** Custom Agent Framework.
**Core Mechanism:** Direct API calls (Anthropic/OpenAI SDKs) with a custom "Game Loop" (`AgentCore.process_message`).
**Agent "Native Call":** Direct Python method execution or HTTP API usage.
**Pros:**
- **Deep Integration:** Can inject `UserIdentity`, `LongTermMemory`, and custom `Plugins` directly into the prompt/context.
- **Granular Control:** Full control over `tool_calls`, retry logic, output parsing, and middleware.
- **Extensible:** Easy to add internal Python tools that share memory space.
**Cons:**
- **Maintenance:** You must build/maintain the loop, tool definitions, and context management.

---

## Feature Contrast

| Feature | `ai-personal-assistant` | `tiann/hapi` |
| :--- | :--- | :--- |
| **Agent Implementation** | Python Code using LLM APIs | Wraps external CLI Binaries (via PTY/Subprocess) |
| **State Management** | Custom (`LongTermMemory` classes) | Managed by the CLI tool itself (sqlite/files) |
| **Interoperability** | High (Internal Python Objects) | Low (Text Streams / Stdin/Stdout) |
| **New Tools** | Add a Python Class/Function | Must config CLI tool or add MCP server |
| **Multi-Agent** | Can programmatically loop agents | Runs distinct processes (switch agents via command) |
| **Use Case** | Integrated Personal Assistant | Remote Coding Environment / Terminal Wrapper |

## The "Native Call" Question

To support "native calling of various agents" (like Hapi does):
- **If you mean "Run different models":** You already have `ClaudeClient` which supports OpenAI/Anthropic. You can easily extend this to swap models per request.
- **If you mean "Run independent Agent Processes":** You *could* implement a `SubProcessAgent` tool in your `ToolRegistry`. This tool would act like Hapi—spawning a `claude` CLI process and piping input/output.

**Proposal:**
Instead of refactoring the entire repo, **add an `AgentTool` adapter**.
- This adapter allows your `AgentCore` to "call" an external agent (like `claude` CLI or another local agent) just like a tool.
- This gives you the best of both worlds: The main "Manager" agent (your current code) can delegate tasks to specialized "Worker" agents (external CLIs) when needed.
