# 开发上下文 (Agent Context)

## 当前任务: A2A Network (Butler + Sidecar) - [已完成]
集成 A2A 协议网络，实现 Assistant (Butler) 调度外部 Agent (Sidecar) 的能力。

## 已完成 (Completed)
- [x] **Phase A: 核心网络**
    - 实现 `AgentRegistry` (注册表与自运行接口)
    - 实现 `NetworkClient` (HTTP 客户端)
    - 实现 `DispatchTool` (LLM 调用工具)
- [x] **Phase B: Sidecar 服务**
    - 实现 FastAPI `sidecar/app.py`
    - 实现 CLI 适配器 (`cli.py`)
    - 实现 OpenAI 适配器 (`openai.py`)
    - 实现 自动注册流程 (Auto-Registration / Heartbeat)
- [x] **Phase C: 部署与验证**
    - 实现 `start_sidecar_with_tunnel.sh` (Cloudflared 自动化)
    - 编写 `docs/A2A_TESTING.md` (测试指南)
    - 集成测试验证通过 (tests/verify_a2a.py)

## 关键文件 (Key Files)
| 文件 | 说明 |
|------|------|
| `agents/network/registry.py` | Agent 注册与管理逻辑 |
| `agents/network/dispatch.py` | LLM 用来调度任务的 Tool |
| `sidecar/app.py` | Sidecar 主服务入口 |
| `scripts/start_sidecar_with_tunnel.sh` | Cloudflared 极速部署脚本 |
| `docs/A2A_TESTING.md` | 开发与云端联调指南 |

## 待完成 (Backlog)
- [ ] PTY Support for CLI Adapter (对交互要求高的 CLI 优化)
- [ ] Sidecar API Key 鉴权 (生产环境增强)
