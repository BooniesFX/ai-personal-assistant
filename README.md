# AI Personal Assistant

基于 Claude Agent SDK 的智能个人助手系统，支持多平台、多 Agent 协作和 MCP 协议。

## 🌟 核心特性

- 🤖 **多平台支持**: Telegram、Web、Slack、WeChat 统一接入
- 🌐 **A2A 网络**: Agent-to-Agent 通信与任务分发
- 🔌 **MCP 协议**: 完整支持 Model Context Protocol
- 🧠 **记忆系统**: 长期记忆与短期对话上下文
- 🎨 **Web UI**: 现代化玻璃拟态设计，支持 Markdown 和代码高亮
- 🔧 **插件/技能系统**: 模块化架构，易于扩展
- 🚀 **Sidecar 支持**: 专用 Agent 注册与协作
- 🎯 **多 LLM 支持**: Claude、DeepSeek、OpenAI 等

## 📁 项目结构

```
ai-personal-assistant/
├── agents/                    # 核心 Agent 系统
│   ├── core/                  # [已废弃] 旧版核心代码
│   ├── sdk/                   # Claude Agent SDK 适配层
│   │   ├── agent.py          # ButlerAgent 封装
│   │   ├── tools.py          # MCP 工具定义
│   │   ├── hooks.py          # Memory/Identity Hooks
│   │   └── llm_provider.py   # 第三方 LLM 适配器
│   ├── memory/               # 记忆系统
│   │   ├── long_term.py      # 长期记忆
│   │   ├── short_term.py     # 短期对话
│   │   └── summarizer.py     # 对话摘要
│   ├── identity/             # 身份管理
│   ├── network/              # A2A 网络通信
│   │   ├── a2a_mcp_server.py # MCP 服务器
│   │   ├── registry.py       # Agent 注册表
│   │   ├── dispatch.py       # 任务分发
│   │   └── anthropic_proxy.py # Anthropic 代理
│   ├── skills/               # 技能系统
│   └── transport/            # 传输层
│       ├── telegram_adapter.py
│       ├── websocket_handler.py
│       └── web_server.py
├── bot/                      # 旧版 Bot 逻辑（保留兼容）
├── plugins/                  # 插件目录
│   ├── admin/                # 管理插件
│   └── ops/                  # 运维插件
├── sidecar/                  # Sidecar Agent
│   ├── app.py               # Sidecar 主应用
│   └── adapters/            # CLI/OpenAI 适配器
├── static/                   # Web UI 静态资源
│   └── index.html           # 主界面
├── docs/                     # 文档
├── tests/                    # 测试
├── run_sdk.py               # SDK 版本入口
├── run_unified.py           # 统一入口
├── pyproject.toml           # 项目配置
└── docker-compose.yml       # Docker 部署
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.12+
- `uv` 包管理器

### 2. 安装依赖

```bash
# 使用 uv 安装依赖
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env`:

```env
# LLM 配置
LLM_PROVIDER=anthropic
LLM_API_KEY=your_anthropic_api_key
LLM_BASE_URL=https://api.anthropic.com
LLM_MODEL=claude-sonnet-4-20250514

# 图像生成
IMAGE_API_KEY=your_modelscope_api_key
IMAGE_BASE_URL=https://api.modelscope.cn/api/v1
IMAGE_MODEL_ID=Tongyi-MAI/Z-Image-Turbo

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Web 服务器
WEB_HOST=0.0.0.0
WEB_PORT=8080
```

### 4. 启动服务

```bash
# 使用 SDK 版本（推荐）
python run_sdk.py

# 或使用统一入口
python run_unified.py

# 或使用启动脚本
./run.sh
```

### 5. 访问界面

- **Web UI**: http://localhost:8080
- **Telegram**: 与你的 Bot 对话
- **MCP 端点**: http://localhost:8080/mcp

## 🌐 A2A 网络配置

### 连接 Claude Code

编辑 `~/.claude.json`:

```json
{
  "mcpServers": {
    "butler-a2a": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8080/mcp"]
    }
  }
}
```

### 启动 Sidecar Agent

```bash
cd sidecar
python app.py --name "code-analyzer" --port 8091 --butler http://localhost:8080
```

详细配置请参考 [docs/a2a_configuration.md](docs/a2a_configuration.md)

## 🛠️ 开发指南

### 添加新技能

在 `agents/skills/library/` 创建新技能目录：

```bash
mkdir -p agents/skills/library/my_skill
touch agents/skills/library/my_skill/SKILL.md
```

### 添加新工具

在 `agents/sdk/tools.py` 中使用 `@tool` 装饰器：

```python
from claude_agent_sdk import tool

@tool("my_tool", "Tool description", {
    "param1": str,
    "param2": int
})
async def my_tool(args):
    result = do_something(args["param1"], args["param2"])
    return {"content": [{"type": "text", "text": result}]}
```

### 添加新插件

1. 在 `plugins/` 创建插件目录
2. 继承 `BasePlugin` 类
3. 实现必要的方法

## 📚 文档

- [A2A 网络配置](docs/a2a_configuration.md)
- [Butler 网络设计](docs/butler_network_design.md)
- [SDK 迁移计划](docs/implementation_plan_sdk_migration.md)
- [变更日志](docs/CHANGELOG_A2A.md)

## 🧪 测试

```bash
# 运行测试
python test_agents.py

# 测试 A2A 网络
python tests/verify_a2a.py

# 测试 Web 集成
python tests/test_web_integration.py
```

## 🐳 Docker 部署

```bash
# 构建镜像
docker build -t ai-personal-assistant .

# 使用 docker-compose 启动
docker-compose up -d

# 或使用测试脚本
./docker-test.sh
```

## 🔧 常见问题

### 服务无法启动

1. 检查环境变量配置
2. 确认端口未被占用
3. 查看日志输出

### MCP 连接失败

1. 确认 Butler 服务正在运行
2. 检查网络连接
3. 验证 MCP 端点地址

### 图像生成失败

1. 检查 ModelScope API 密钥
2. 确认网络连接正常
3. 查看错误日志

## 📄 许可证

本项目使用的 Z-Image-Turbo 模型遵循 Apache License 2.0。

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📧 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。