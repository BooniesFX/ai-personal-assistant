# Design: The "Butler" Agent Network

## Concept
Instead of integrating every capability into one codebase, we treat the Assistant as a **Butler (Central Node)**.
- The Butler **knows** available agents (via Registry).
- The Butler **routes** user requests to the right agent.
- The Butler **aggregates** results and reports back to the user.

## 1. Network Topology
- **Center**: `AssistantCore` (The Butler)
- **Nodes**: External Agents (e.g., "Coder", "Searcher", "Scheduler")
- **Protocol**: HTTP/JSON (REST)

## 2. Registry (`agents/network/registry.yaml`)
A simple file listing the "Contacts" in the Butler's address book.
```yaml
agents:
  - id: "writer_agent"
    name: "Article Writer"
    description: "Specialized in writing long-form articles and summaries."
    endpoint: "http://localhost:8001/v1/chat/completions"
    protocol: "openai_compatible"
    
  - id: "research_agent"
    name: "Deep Researcher"
    description: "Performs deep web research and fact checking."
    endpoint: "http://192.168.1.50:3000/agent/task"
    protocol: "simple_json"
```

## 3. Communication Protocols
The Butler supports a few standard idioms to talk to external agents without modifying them.

### A. Simple JSON (Generic)
For custom lightweight agents.
- **Request**: `POST { "prompt": "..." }`
- **Response**: `{ "response": "..." }`

### B. OpenAI Compatible (Standard)
For generic LLM agents or frameworks (like LangChain/Autogen served via API).
- **Request**: `POST /v1/chat/completions { "messages": [...] }`

### C. Webhook / Async (The "Email" Style)
For long-running tasks.
- **Request**: `POST { "task": "...", "callback_url": "http://butler/webhook" }`
- **Response**: `202 Accepted`
- **Callback**: Butler receives `POST /webhook { "result": "..." }` later.

## 4. The "Dispatch" Tool
The Butler has a universal tool:
`dispatch_to_agent(agent_id: str, message: str)`

**Flow:**
1. **User**: "Research the history of AGI."
2. **Butler**: "I should ask the Researcher." -> Calls `dispatch_to_agent("research_agent", "Research history of AGI")`.
3. **System**: Sends HTTP request to `http://.../agent/task`.
4. **System**: Receives response "Here is the report...".
5. **Butler**: "Here is what the Researcher found: [Summary]" -> Sends to User.

## 5. Daily Aggregation (The "Morning Briefing")
The Butler can periodically query agents or check the "Inbox" (collected webhooks) to generate a summary.
- Cron Job -> `Butler.generate_briefing()`
- Reads `Inbox` database.
- Summarizes "Writer Agent finished the draft", "Scheduler confirmed meeting".
- Sends Telegram Message.
