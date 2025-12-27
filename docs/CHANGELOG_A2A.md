# Changelog - A2A Network & Sidecar

## [v1.0.0] - 2025-12-27

### Added
- **Butler Core Integration**:
    - `agents/network/models.py`: Unified A2A message and registry models.
    - `agents/network/registry.py`: Agent registration management with heartbeat support.
    - `agents/network/client.py`: Async HTTP client for agent communication.
    - `agents/network/dispatch.py`: `DispatchTool` for LLM delegation.
- **Sidecar Service**:
    - `sidecar/app.py`: FastAPI-based bridge service.
    - `sidecar/adapters/cli.py`: Subprocess wrapper for CLI tools.
    - `sidecar/adapters/openai.py`: Proxy for OpenAI-compatible APIs.
- **Tools & Scripts**:
    - `scripts/start_sidecar_with_tunnel.sh`: One-click Cloudflared integration.
    - `tests/verify_a2a.py`: Integration test suite.
- **Documentation**:
    - `docs/A2A_TESTING.md`: Detailed testing guide.
    - `docs/sidecar_design.md`: Sidecar architecture.
    - `docs/butler_network_design.md`: Network topology.

### Fixed
- Standalone execution bug in `sidecar/app.py` regarding relative imports.
- `parser` and `CLIAdapter` NameErrors in Sidecar entry point.
