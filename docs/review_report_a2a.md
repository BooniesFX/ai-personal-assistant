# Review Report: A2A Network & Sidecar

## Overview
- **Feature**: Butler A2A Network & Sidecar Service
- **Status**: Implemented
- **Review Date**: 2025-12-27

## 1. Architecture Review
The implementation follows the "Butler" + "Sidecar" design. 
- **Core**: `AgentCore` successfully integrates `DispatchTool`.
- **Sidecar**: Standalone FastAPI service with Pluggable Adapters.

## 2. Code Quality
### Pros
- **Modularity**: Adapters (`cli`, `openai`) are well isolated from the main `app.py`.
- **Async**: Fully asynchronous communication using `httpx` and `asyncio.subprocess`.
- **Type Safety**: Uses Pydantic models for request/response validation.

### Cons / Risks 🐛
- **CLI Adapter Heuristic**: The `read_until_prompt` logic in `cli.py` is a simple heuristic (reads until silence). This may fail for slow-streaming agents or interactive REPLs that don't produce predictable output timing. **Recommendation**: Implement PTY support in Phase 2.
- **Security**: Sidecar exposes an unauthenticated HTTP endpoint. Use strictly in local/trusted networks or add API Key auth in the future.
- **Error Handling**: If the subprocess crashes, the Sidecar might need a restart or logic to respawn it.

## 3. Improvements Required 💡
- [ ] Add `API_KEY` authentication to Sidecar.
- [ ] Add Dockerfile for the Sidecar.
- [ ] Implement PTY support for `cli_adapter` for better TTY interaction.

## 4. Test Coverage
- `tests/verify_a2a.py` covers:
    - Health Check endpoint.
    - Message dispatch loop.
    - CLI echo verification.
