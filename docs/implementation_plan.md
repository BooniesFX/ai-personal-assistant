# 实施计划 (Implementation Plan)

## 优先级排序 (Priorities)
- **P0 (必须)**: 核心网络通信 (Butler <-> Sidecar)
- **P0 (必须)**: Sidecar 基础框架 & CLI 适配器
- **P1 (高)**: Sidecar OpenAI 适配器 (支持标准 LLM 调用)
- **P1 (高)**: 自动注册流程 (Auto-Registration)
- **P2 (中)**: 错误处理与重试机制
- **P2 (中)**: Docker 部署支持

## 阶段划分 (Phases)

### Phase A: 核心网络与 CLI 支持 (已完成)
- [x] **Core Models**: `agents/network/models.py`
- [x] **Registry**: `agents/network/registry.py`
- [x] **HTTP Client**: `agents/network/client.py`
- [x] **Dispatch Tool**: `agents/network/dispatch.py`
- [x] **Sidecar App**: `sidecar/app.py`
- [x] **CLI Adapter**: `sidecar/adapters/cli.py`

### Phase B: 高级适配器与验证 (进行中)
- [ ] **OpenAI Adapter**: `sidecar/adapters/openai.py`
- [ ] **Verification**: 编写集成测试脚本 `tests/verify_a2a.py`
- [ ] **Review**: 代码评审报告 `docs/review_report_a2a.md`

### Phase C: 文档与归档
- [ ] **Context Update**: 更新 `.agent/context.md`
- [ ] **Doc Archival**: 移动设计文档到 `docs/`
