# Claude Agent SDK 迁移实施计划

## 📋 项目背景

将现有手写的 Agent 框架迁移到 `anthropic-ai/claude-agent-sdk-python`，获得以下好处：
- 官方维护的 Agent 循环和工具管理
- 内置 MCP 服务器支持（无需子进程）
- Hooks 机制实现细粒度控制
- 更好的错误处理和类型安全
- 支持第三方 LLM（通过自定义 Client）

---

## 🎯 优先级排序

- **P0 (必须)**: 核心 AgentCore 迁移到 ClaudeSDKClient
- **P0 (必须)**: 现有工具/插件适配为 SDK MCP Tools
- **P1 (高)**: Memory 系统集成（通过 Hooks）
- **P1 (高)**: 第三方 LLM 支持（DeepSeek 等）
- **P2 (中)**: Transport 层保持不变（Telegram/Web）
- **P2 (中)**: Identity 系统集成
- **P3 (低)**: 完善错误处理和日志

---

## 🔄 阶段划分

### Phase A: 环境准备与基础理解
**状态**: 待开始

1. 安装 SDK
   ```bash
   uv add claude-agent-sdk
   ```

2. 创建 SDK 适配层目录结构
   ```
   agents/
   ├── sdk/                    # 新增：SDK 适配层
   │   ├── __init__.py
   │   ├── agent.py           # ClaudeSDKClient 封装
   │   ├── tools.py           # 工具定义 (@tool 装饰器)
   │   ├── hooks.py           # Hooks 定义 (Memory, Identity)
   │   └── llm_provider.py    # 第三方 LLM 适配器
   ```

3. 验证 SDK 基础功能可用

---

### Phase B: 核心工具迁移
**状态**: 待开始

将现有插件迁移为 SDK MCP Tools：

| 现有组件 | SDK 迁移方案 |
|----------|-------------|
| `ImageGenerationPlugin` | `@tool("generate_image")` |
| `DispatchTool` | `@tool("dispatch_to_agent")` |
| `ListAgentsTool` | `@tool("list_agents")` |
| `AdminPlugin` | `@tool("admin_manage")` |
| `SkillManager` | 保持为 `@tool` 集合 |

示例代码：
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("generate_image", "Generate an AI image. ONLY use when user explicitly requests.", {
    "prompt": str,
    "width": int,
    "height": int
})
async def generate_image(args):
    # 调用现有 ModelScopeClient
    result = await api_client.generate_image(args["prompt"], ...)
    return {"content": [{"type": "text", "text": f"Image generated: {url}"}]}

# 创建 MCP 服务器
tools_server = create_sdk_mcp_server(
    name="butler-tools",
    version="1.0.0",
    tools=[generate_image, ...]
)
```

---

### Phase C: Memory 系统集成
**状态**: 待开始

通过 Hooks 机制将 Memory 注入到对话流程：

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

async def inject_memory_hook(input_data, tool_use_id, context):
    """在每次对话前注入长期记忆"""
    user_id = context.get("user_id")
    memory_context = long_term_memory.get_context_for_llm(user_id)
    
    # 通过修改 system_prompt 注入
    return {
        "hookSpecificOutput": {
            "additionalSystemPrompt": memory_context
        }
    }

async def save_conversation_hook(input_data, tool_use_id, context):
    """对话结束后保存到短期记忆"""
    short_term_memory.add_turn(...)
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreConversation": [HookMatcher(matcher="*", hooks=[inject_memory_hook])],
        "PostConversation": [HookMatcher(matcher="*", hooks=[save_conversation_hook])],
    }
)
```

---

### Phase D: 第三方 LLM 支持
**状态**: 待开始

SDK 默认使用 Claude，但需要支持 DeepSeek 等第三方模型。

**方案**: 通过自定义 `cli_path` 或 Hook 拦截实现：

```python
# 方案1: 使用环境变量配置模型
options = ClaudeAgentOptions(
    model="deepseek-ai/DeepSeek-V3.2",  # 需要确认 SDK 是否支持
)

# 方案2: 创建 LLM 适配器（如果 SDK 不直接支持）
# 这需要研究 SDK 源码确定最佳方案
```

**注意**: 这部分需要深入研究 SDK 源码，确认其对第三方 LLM 的支持程度。

---

### Phase E: Transport 层集成
**状态**: 待开始

现有 Transport 层（Telegram/Web）保持不变，只需修改调用方式：

```python
# 修改前 (agents/core/agent_core.py)
response = await self.llm_client.create_tool_message(...)

# 修改后 (agents/sdk/agent.py)
async with ClaudeSDKClient(options=options) as client:
    await client.query(user_message)
    async for msg in client.receive_response():
        yield msg  # 流式返回给 Transport
```

---

### Phase F: 清理与文档更新
**状态**: 待开始

1. 删除废弃的代码：
   - `agents/core/agent_core.py` → 用 `agents/sdk/agent.py` 替代
   - `agents/core/client.py` → 不再需要
   - `agents/tools/registry.py` → SDK 内置管理

2. 更新文档：
   - `.agent/context.md`
   - `README.md`
   - `docs/CHANGELOG.md`

---

## 📁 目标目录结构

```
agents/
├── sdk/                    # 新增：Claude Agent SDK 适配层
│   ├── __init__.py
│   ├── agent.py           # ButlerAgent (封装 ClaudeSDKClient)
│   ├── tools.py           # 所有 @tool 定义
│   ├── hooks.py           # Memory/Identity Hooks
│   └── config.py          # SDK 配置
│
├── memory/                 # 保留：Memory 系统
│   ├── short_term.py
│   ├── long_term.py
│   └── summarizer.py
│
├── identity/               # 保留：Identity 系统
│   └── manager.py
│
├── network/                # 保留：A2A 网络
│   ├── registry.py
│   ├── client.py
│   └── dispatch.py
│
├── transport/              # 保留：传输层
│   ├── telegram_adapter.py
│   ├── websocket_handler.py
│   └── web_server.py
│
└── [废弃] core/            # 将被 sdk/ 替代
    ├── agent_core.py      # → sdk/agent.py
    ├── client.py          # → 不再需要
    └── ...
```

---

## ✅ 完成检查清单

- [ ] Phase A: SDK 安装与目录结构
- [ ] Phase B: 核心工具迁移 (generate_image, dispatch, list_agents)
- [ ] Phase C: Memory Hooks 集成
- [ ] Phase D: 第三方 LLM 支持验证
- [ ] Phase E: Transport 层集成测试
- [ ] Phase F: 清理与文档更新
- [ ] 编译/运行测试通过
- [ ] Telegram 端测试通过
- [ ] Web 端测试通过

---

## ⚠️ 风险与待确认事项

1. **第三方 LLM 支持**: SDK 是否原生支持 DeepSeek 等 OpenAI 兼容 API？需要研究源码。
2. **Hooks 时机**: 确认 SDK 支持的 Hook 点是否满足 Memory 注入需求。
3. **流式响应**: 确认 SDK 的流式输出是否可以无缝对接现有 WebSocket。
4. **MCP 外部服务器**: Tavily MCP 是否需要保持为外部服务器，或可迁移为 SDK MCP。

---

## 📝 下一步行动

1. **立即**: 安装 SDK，创建 `agents/sdk/` 目录
2. **然后**: 先迁移一个简单工具 (`list_agents`) 验证流程
3. **逐步**: 按 Phase 顺序推进
