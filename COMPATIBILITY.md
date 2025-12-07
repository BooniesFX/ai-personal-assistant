# Docker 集成与兼容性说明

本文档说明 Claude Agent 架构在 Docker 环境中的集成情况和与原有系统的兼容性。

## 🐳 Docker 集成状态

### ✅ 已完成集成

1. **Dockerfile 更新**
   - 使用新的启动脚本 `entrypoint.sh`
   - 自动检测 Claude API 密钥并选择运行模式
   - 保持向后兼容性

2. **智能启动脚本**
   - 自动检测环境变量配置
   - 根据 Claude API 密钥可用性选择运行模式
   - 提供详细的启动日志

3. **环境变量支持**
   - 新增 `ANTHROPIC_API_KEY` 用于 Claude Agent
   - 新增可选的 Claude 配置参数
   - 原有环境变量保持不变

4. **数据持久化**
   - `/app/data` 目录挂载保持不变
   - Claude Agent 的记忆数据存储在 `data/claude_memory.json`
   - 会话数据自动持久化

### 🔧 更新内容

| 组件 | 变更 | 兼容性 |
|------|------|--------|
| **Dockerfile** | 更新 CMD 为入口点脚本 | ✅ 完全向后兼容 |
| **启动方式** | 自动选择传统/混合模式 | ✅ 根据配置自动适配 |
| **环境变量** | 新增 Claude 相关配置 | ✅ 可选，不影响原有功能 |
| **数据存储** | 新增 Claude 记忆文件 | ✅ 原有数据不受影响 |

## 📋 运行模式

### 模式 1: 完整 Claude Agent（推荐）
**条件**: 配置了 `ANTHROPIC_API_KEY`

**功能**:
- ✅ 自然语言理解
- ✅ 持久化会话记忆
- ✅ 传统命令支持
- ✅ 工具调用集成

**启动命令**:
```bash
docker-compose up -d
```

### 模式 2: 传统命令机器人
**条件**: 未配置 `ANTHROPIC_API_KEY`

**功能**:
- ✅ 传统命令支持（与之前完全相同）
- ❌ 无自然语言理解
- ❌ 无会话记忆

**启动命令**:
```bash
docker-compose up -d
```

## 🔄 向后兼容性保证

### 配置兼容性
| 配置项 | Claude Agent 模式 | 传统模式 | 说明 |
|--------|------------------|----------|------|
| `TELEGRAM_BOT_TOKEN` | ✅ 必需 | ✅ 必需 | 无变化 |
| `MODELSCOPE_API_KEY` | ✅ 必需 | ✅ 必需 | 无变化 |
| `ADMIN_ID` | ✅ 必需 | ✅ 必需 | 无变化 |
| `ANTHROPIC_API_KEY` | ✅ 必需 | ⚠️ 可选 | 新增，传统模式可不配置 |
| 其他原有配置 | ✅ 完全兼容 | ✅ 完全兼容 | 无变化 |

### 数据兼容性
- **原有数据**: `./data` 目录中的权限文件、OPS 数据等完全兼容
- **新增数据**: Claude Agent 在 `./data` 中创建新的记忆文件
- **互不干扰**: 新旧数据格式完全独立，互不影响

### API 兼容性
- **传统命令**: 所有 `/img`, `/ops`, `/help` 等命令工作方式不变
- **插件系统**: 所有原有插件无需修改即可工作
- **权限系统**: 用户白名单、群组权限系统保持不变

## 🚀 部署指南

### 从旧版本升级
1. **备份原有数据** (可选但建议)
   ```bash
   cp -r data data_backup_$(date +%Y%m%d)
   ```

2. **更新代码**
   ```bash
   git pull origin main
   ```

3. **更新 .env 文件**
   添加 Claude API 密钥：
   ```env
   ANTHROPIC_API_KEY=your_claude_api_key_here
   ```

4. **重新构建并启动**
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

### 全新安装
1. **复制环境模板**
   ```bash
   cp .env.example .env
   ```

2. **编辑 .env 文件**
   填写所有必需和可选的 API 密钥

3. **启动服务**
   ```bash
   docker-compose up -d
   ```

## 🧪 测试兼容性

运行测试脚本验证集成：
```bash
./docker-test.sh
```

## ⚠️ 已知限制

1. **资源使用**
   - Claude Agent 模式内存使用略高（约 +50-100MB）
   - 响应时间略长（自然语言处理开销）

2. **网络要求**
   - 需要访问 Anthropic API 端点
   - 可能需要配置代理

3. **数据迁移**
   - 传统会话数据不自动迁移到 Claude 记忆系统
   - 用户需要重新建立会话上下文

## 🔧 故障排除

### 问题: Claude Agent 无法启动
**解决**: 检查 `ANTHROPIC_API_KEY` 是否有效

### 问题: 传统命令不工作
**解决**: 确保 `MODELSCOPE_API_KEY` 等原有配置正确

### 问题: 权限系统异常
**解决**: 检查 `./data` 目录挂载和权限

## 📞 支持

如有兼容性问题：
1. 查看容器日志: `docker-compose logs -f bot`
2. 检查环境变量: `docker-compose exec bot env`
3. 回滚到传统模式: 移除 `ANTHROPIC_API_KEY` 重启

---

**总结**: Docker 集成已完成，保持完全向后兼容性，用户可根据需要选择传统模式或 Claude Agent 模式。