# A2A (Agent-to-Agent) 网络配置指南

## 概述

A2A 网络允许多个 Agent 互相通信和协作。通过标准的 MCP 协议，**任何支持 MCP 的 Agent 都可以直接使用 A2A 功能**，无需修改代码。

## 🌍 通用配置（任何设备）

只需知道 Butler 的 IP 地址，就可以让任何设备上的 Agent 接入 A2A 网络。

### Claude Code 配置

编辑 `~/.claude.json`，添加：

```json
{
  "mcpServers": {
    "butler-a2a": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://BUTLER_IP:8080/mcp"]
    }
  }
}
```

**示例**（Butler 运行在 192.168.1.100）：

```json
{
  "mcpServers": {
    "butler-a2a": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://192.168.1.100:8080/mcp"]
    }
  }
}
```

### Gemini CLI / 其他 MCP 客户端

同样使用 `mcp-remote`：

```bash
# 连接到 Butler
npx -y mcp-remote http://BUTLER_IP:8080/mcp
```

---

## 本地配置（运行 Butler 的设备）

如果你在 Butler 所在的设备上使用 Claude Code：

```bash
# 作为 stdio 服务器 (用于本地 MCP 客户端)
python -m agents.network.a2a_mcp_server

# 设置 Butler URL (如果不是默认的 localhost:8080)
BUTLER_URL=http://192.168.1.100:8080 python -m agents.network.a2a_mcp_server
```

---

## 方法 3: 注册 Sidecar Agent

Sidecar Agent 是专门用途的 Agent（如代码分析、文档生成等）。

### 启动 Sidecar

```bash
cd sidecar
python app.py --name "code-analyzer" --port 8091 --butler http://localhost:8080
```

### Sidecar 自动注册流程

1. Sidecar 启动时向 Butler 发送 `POST /network/register`
2. Butler 将其添加到 Agent Registry
3. 其他 Agent 可以通过 `list_agents` 看到它
4. 可以通过 `dispatch_to_agent` 向它发送任务

### 注册请求示例

```bash
curl -X POST http://localhost:8080/network/register \
  -H "Content-Type: application/json" \
  -d '{
    "id": "code-analyzer",
    "name": "Code Analyzer Agent",
    "url": "http://localhost:8091",
    "capabilities": ["code_analysis", "review"]
  }'
```

---

## 架构图

```
┌─────────────────┐                    ┌─────────────────────┐
│  Claude Code    │  ◀── MCP ───────▶ │                     │
├─────────────────┤                    │                     │
│  Gemini CLI     │  ◀── MCP ───────▶ │   Butler (8080)     │
├─────────────────┤                    │   - Agent Registry  │
│  Codex          │  ◀── MCP ───────▶ │   - A2A Tools       │
├─────────────────┤                    │                     │
│  Web UI         │  ◀── WebSocket ──▶│                     │
└─────────────────┘                    └──────────┬──────────┘
                                                  │
                                                  │ HTTP
                          ┌───────────────────────┼───────────────────────┐
                          ▼                       ▼                       ▼
                   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
                   │ Sidecar A   │         │ Sidecar B   │         │ Sidecar C   │
                   │ :8091       │         │ :8092       │         │ :8093       │
                   └─────────────┘         └─────────────┘         └─────────────┘
```

---

## 使用示例

### 在 Claude Code 中

```
> 列出当前网络中的所有 Agent
< [使用 list_agents 工具]
< 
< ## Registered Agents
< 
< - **Code Analyzer** (ID: `code-analyzer`)
<   - URL: http://localhost:8091
<   - Capabilities: code_analysis, review

> 让 code-analyzer 分析一下我的代码
< [使用 dispatch_to_agent 工具]
< agent_id: code-analyzer
< message: 分析 /path/to/my/code
<
< ## Response from Code Analyzer
< 代码分析结果...
```

### 在 Web UI 中

Web 界面的侧边栏会显示 "Active Agents" 列表，点击可以查看详情或直接与其对话。
