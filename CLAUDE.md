# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

用中文对话,文档生成用英文

## Project

**AgentScope Skill/Tool/MCP Validation Platform** — a FastAPI-based agent testing shell for personal R&D validation, built around `agentscope-runtime` with `uv` project management. The platform creates an agent per client request with SSE streaming to test skill calls, tool calls, MCP calls, and session persistence (JSON-file and Redis backends).

### Constraints

- Core runtime relies on `agentscope-runtime` — the primary framework under evaluation
- Chat exposed via FastAPI with SSE streaming responses
- Near-stateless server design — one active bootstrapped session per pod
- Session resume supports both JSON-file and Redis backends
- Model/provider config externalized to `.env`
- Use `uv` for all dependency/project management

## Development Commands

```bash
# Install dependencies
uv sync

# Start the service (127.0.0.1:8000)
bash scripts/run_service.sh

# Run all tests
uv run pytest tests/ -x -v

# Run a single test file
uv run pytest tests/test_session.py -x -v

# Run a single test function
uv run pytest tests/test_session.py::test_session_save_load -x -v

# Run demo scripts (service must be running)
uv run scripts/demos/demo_tool.py
uv run scripts/demos/demo_skill.py
uv run scripts/demos/demo_mcp.py
uv run scripts/demos/demo_resume.py
```

## Architecture

### Dual-Path Request Model

The system has two distinct request paths that converge at the agent query layer:

1. **Legacy path** (`POST /process` without matching session_id): creates an ephemeral agent per request using the global toolkit. Config resolved from request `agent_config` with `.env` fallback.

2. **Bootstrap path** (`POST /sessions/bootstrap` → `POST /process` with session_id): creates a persistent `SessionRuntime` that owns its own toolkit, agent, memory, skill registry, and MCP clients. Only one active bootstrapped session per pod (`_active_runtime` singleton in `session_runtime.py`).

3. **Shutdown** (`POST /sessions/{session_id}/shutdown`): closes MCP clients and clears the runtime.

### Key Flow: `POST /process`

`src/agent/query.py:chat_query` → validates session_id → checks for matching `SessionRuntime` → if found, reuses its agent; if not, creates ephemeral agent with global toolkit → streams via `stream_printing_messages` → saves memory to session backend.

### Session Persistence

`src/agent/session.py` provides a backend factory (`get_session_backend()`) that returns either `JSONSession` (files in `./sessions/`) or `RedisSession` (key prefix `agentops:`), selected by `SESSION_BACKEND` env var. Session IDs are validated against path traversal and format rules.

### Skill System

Skills are declared as directories with a `SKILL.md` containing YAML frontmatter (name, description, scripts). Two execution modes:
- `python_callable`: imports and calls a Python function directly
- `python_file`: runs a script via subprocess with JSON stdin

Skills are registered on the session toolkit with lazy/eager activation. The `activate_skill` tool reveals skill instructions to the agent at runtime. See `src/agent/skill_runtime.py` and `skills/example_skill/SKILL.md`.

### MCP Integration

Bootstrap accepts MCP server configs of two types:
- `StdioMCPServerConfig` → `StdIOStatefulClient` (subprocess-based)
- `HttpMCPServerConfig` → `HttpStatefulClient` (SSE or streamable_http)

A startup MCP server (`src/mcp/server.py` via FastMCP) provides a `get_time` tool and is started in the app lifespan.

### Configuration Resolution

`src/core/config.py:resolve_effective_config` merges per-request `AgentConfig` overrides with `.env` defaults field-by-field. Settings are loaded once via `lru_cache` in `src/core/settings.py`.

## Testing Patterns

- All tests auto-mock the startup MCP client via `conftest.py:_mock_mcp_client` (patches `StdIOStatefulClient` to avoid subprocess dependency)
- Each test gets `configured_env` fixture with test env vars and `clear_settings_cache` to reset the `lru_cache`
- Redis tests use `fakeredis` — no real Redis needed
- `pythonpath = ["."]` in `pyproject.toml` enables `src.` imports

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | >=3.11 | Runtime |
| agentscope-runtime | 1.1.3 | Agent framework under test |
| FastAPI | 0.135.3 | HTTP/SSE server (via agentscope-runtime) |
| pydantic-settings | >=2.0 | `.env` config loading |
| python-frontmatter | >=1.1.0 | SKILL.md parsing |
| pytest | 9.0.3 | Test runner (dev) |
| httpx | 0.28.1 | HTTP client for demos (dev) |
| fakeredis | >=2.31.0 | Redis mock for tests (dev) |

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
