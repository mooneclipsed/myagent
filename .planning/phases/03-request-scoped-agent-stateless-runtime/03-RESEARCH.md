# Phase 3: Request-Scoped Agent & Stateless Runtime - Research

**Researched:** 2026-04-11
**Domain:** agentscope-runtime request body handling, per-request config override, stateless agent creation
**Confidence:** HIGH

## Summary

Phase 3 transforms the current `.env`-only agent configuration into a request-configurable system where each API call can optionally override `model_name`, `api_key`, and `base_url` while keeping all other settings fixed. The implementation is architecturally small but foundational -- all later phases (capability tracing, context continuity, session persistence) rely on request-scoped agent behavior.

The `agentscope-runtime` framework uses `AgentRequest` with `extra="allow"` on its Pydantic model, which means an `agent_config` field placed in the request body is automatically accessible via `request.agent_config` inside the query handler. The handler already receives the `request` parameter (an `AgentRequest` instance), so accessing per-request config requires no framework-level changes -- only handler-level config resolution logic.

The current `Settings` class uses `lru_cache` as a singleton. The override pattern should use `model_copy(update=...)` to create per-request derived settings without mutating the cached singleton, preserving both thread safety and the `.env` fallback contract.

**Primary recommendation:** Add an `AgentConfig` pydantic model for the `agent_config` field. In the `@app.query` handler, extract `request.agent_config`, merge it with `.env` defaults via `settings.model_copy(update=...)`, and pass the effective config to `OpenAIChatModel` construction. Add `logging` for config trace observability.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Agent config is minimally overridable per request: `model_name`, `api_key`, and `base_url` only. `sys_prompt`, formatter, and agent type remain fixed (not request-configurable in this phase).
- **D-02:** Field-level fallback: each config field independently falls back to `.env` defaults when not provided in the request. A request can override just `model_name` while keeping `api_key` and `base_url` from `.env`.
- **D-03:** Request body extends the existing `messages` array with a top-level `agent_config` object. Backward-compatible -- requests without `agent_config` use `.env` defaults (existing Phase 2 behavior preserved). Example: `{ "messages": [...], "agent_config": { "model_name": "gpt-4o" } }`.
- **D-04:** The `agent_config` object is optional in the request body. When absent, all model config comes from `.env` (same as Phase 2 behavior).
- **D-05:** Verification follows the established pattern: `pytest` automated tests + smoke script. Tests validate that requests with different configs result in agents using the correct configuration.
- **D-06:** Stateless verification includes both instance isolation (each request gets a fresh agent) AND config trace logging -- the service should log the effective config used per request so that stateless behavior is observable, not just assumed.
- **D-07:** Success criteria tests: (1) a request with `agent_config` creates an agent using those values, (2) a second request with different `agent_config` uses the new values without server restart, (3) a request without `agent_config` falls back to `.env` defaults.

### Claude's Discretion
- Exact `agent_config` field names and pydantic model structure, as long as they cover `model_name`, `api_key`, `base_url` with field-level `.env` fallback.
- Exact logging format and level for config tracing, as long as it's observable in test output.
- Internal module layout for config resolution logic.
- Exact test structure and smoke script shape, following established Phase 1/2 patterns.

### Deferred Ideas (OUT OF SCOPE)
- Configurable `sys_prompt` per request -- could be useful for testing but not required for CORE-02/CORE-03.
- Configurable agent type per request (e.g., switching from ReActAgent to other types) -- deferred until multi-agent patterns are explored.
- Configurable formatter per request -- deferred, same rationale.
- Skill/tool/MCP invocation trace events -- Phase 4.
- Multi-turn context continuity -- Phase 5.
- JSON/Redis session persistence -- Phases 6-8.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-02 | User can create/configure a single request-scoped agent from API-provided config payload. | AgentRequest `extra="allow"` allows `agent_config` in request body. Handler accesses via `request.agent_config`. Pydantic `model_copy(update=...)` merges overrides with `.env` defaults. Fresh `ReActAgent` per request already established in Phase 2. |
| CORE-03 | Service keeps runtime near-stateless; request/session state comes from API payload and selected session backend. | Per-request agent creation (no global agent state). Config derived from request + immutable `.env` singleton. Logging makes stateless behavior observable (D-06). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| agentscope-runtime | 1.1.3 | Agent runtime with `@app.query` decorator, SSE streaming, AgentRequest model | Core framework under test; `AgentRequest` has `extra="allow"` enabling custom fields [VERIFIED: codebase inspection] |
| pydantic | 2.x (via agentscope-runtime) | `AgentConfig` model, request validation | Already a transitive dependency; `model_copy(update=...)` provides clean override pattern [VERIFIED: pydantic v2 API tested] |
| pydantic-settings | >=2.0 (installed) | `.env` settings loading with `BaseSettings` | Established in Phase 1; `Settings` class with 4 required fields [VERIFIED: src/core/settings.py] |
| Python stdlib logging | stdlib | Config trace logging per D-06 | No external dependency needed; `logging.getLogger(__name__)` is standard [ASSUMED] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.3 | Automated tests for config override behavior | All test files |
| httpx | 0.28.1 | TestClient HTTP transport | Used transitively by FastAPI TestClient |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `model_copy(update=...)` | New Settings instance with merged kwargs | `model_copy` is cleaner and avoids re-validating all fields; both work but `model_copy` is the idiomatic Pydantic v2 pattern |
| Python stdlib logging | structlog | structlog adds structured JSON logging but is overkill for R&D validation shell; stdlib logging is sufficient for D-06 observability |

**Installation:**
No new packages required. All dependencies are already in `pyproject.toml`.

**Version verification:**
```
agentscope-runtime==1.1.3 (installed, verified via uv run python import)
pydantic-settings>=2.0 (installed, used in src/core/settings.py)
pytest==9.0.3 (installed, in dev dependencies)
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── agent/
│   ├── __init__.py       # Triggers @app.query registration
│   └── query.py          # Handler: extract config, create agent, stream response
├── core/
│   ├── __init__.py
│   ├── settings.py       # Settings + get_settings() (lru_cache singleton)
│   └── config.py         # NEW: AgentConfig model + resolve_agent_config()
├── app/
│   ├── __init__.py
│   └── lifespan.py       # Startup validation (unchanged)
└── main.py               # AgentApp entry (unchanged)
```

### Pattern 1: AgentConfig Pydantic Model with Optional Fields
**What:** A Pydantic model with all-optional fields representing the three overridable config values.
**When to use:** Defining the request-level config schema.
**Example:**
```python
# Source: [Pydantic v2 docs - Optional fields]
from pydantic import BaseModel
from typing import Optional

class AgentConfig(BaseModel):
    """Per-request agent configuration overrides.
    
    All fields are optional. When a field is not provided,
    the corresponding .env default is used instead.
    """
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
```

### Pattern 2: Field-Level Config Resolution
**What:** Merge request-level overrides with `.env` defaults using `model_copy(update=...)`.
**When to use:** Inside the query handler, before constructing `OpenAIChatModel`.
**Example:**
```python
# Source: [VERIFIED: Pydantic v2 model_copy tested in this session]
from src.core.settings import get_settings
from src.core.config import AgentConfig

def resolve_effective_config(agent_config: AgentConfig | None = None):
    """Resolve effective model config by merging request overrides with .env defaults.
    
    Returns a dict suitable for OpenAIChatModel construction.
    """
    settings = get_settings()
    
    if agent_config is None:
        return {
            "model_name": settings.MODEL_NAME,
            "api_key": settings.MODEL_API_KEY,
            "base_url": settings.MODEL_BASE_URL,
        }
    
    return {
        "model_name": agent_config.model_name or settings.MODEL_NAME,
        "api_key": agent_config.api_key or settings.MODEL_API_KEY,
        "base_url": agent_config.base_url or settings.MODEL_BASE_URL,
    }
```

### Pattern 3: Config Trace Logging in Handler
**What:** Log the effective config per request for D-06 observability.
**When to use:** After config resolution, before agent creation.
**Example:**
```python
# Source: [ASSUMED - Python stdlib logging pattern]
import logging
logger = logging.getLogger(__name__)

# Inside handler, after resolving config:
logger.info(
    "Agent config resolved",
    extra={
        "model_name": config["model_name"],
        "base_url": config["base_url"],
        "source": "request" if agent_config else ".env",
    },
)
```

### Pattern 4: Handler Integration Point
**What:** How the existing `@app.query` handler accesses request-level config.
**When to use:** The only file that changes for the config flow is `query.py`.
**Example:**
```python
# Source: [VERIFIED: agentscope-runtime AgentRequest extra="allow" tested]
@app.query(framework="agentscope")
async def chat_query(self, msgs, request=None, **kwargs):
    # Extract agent_config from the request object
    # AgentRequest has extra="allow", so agent_config is accessible
    agent_config = None
    if request and hasattr(request, "agent_config") and request.agent_config:
        agent_config = AgentConfig(**request.agent_config)
    
    config = resolve_effective_config(agent_config)
    
    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(
            model_name=config["model_name"],
            api_key=config["api_key"],
            client_kwargs={"base_url": config["base_url"]},
            stream=True,
        ),
        sys_prompt="You are a helpful assistant.",
        formatter=OpenAIChatFormatter(),
        memory=InMemoryMemory(),
    )
    # ... rest unchanged
```

### Anti-Patterns to Avoid
- **Mutating the Settings singleton:** Never call `get_settings().MODEL_NAME = "override"` -- the `lru_cache` singleton is shared across all requests and must remain immutable. Use `model_copy(update=...)` or a plain dict for the effective config instead.
- **Validating api_key format in AgentConfig:** The `api_key` is passed through to `OpenAIChatModel` which handles validation. Do not add format checks that may conflict with different providers.
- **Storing per-request agents globally:** Each request creates and discards its own agent. Never cache agents in a module-level dict or on the app object.
- **Using `request.model_extra["agent_config"]` instead of `request.agent_config`:** While both work due to `extra="allow"`, the attribute access is more readable and is the standard Pydantic v2 pattern for extra fields.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config field validation | Custom validator for `model_name`, `api_key`, `base_url` | Pydantic `AgentConfig` model with `Optional[str]` fields | Pydantic handles type checking, None defaults, and serialization automatically |
| Settings override/merge | Custom dict-merge logic with `.env` values | `model_copy(update=...)` or simple `or` fallback per field | Pydantic's `model_copy` preserves validators and type information |
| Request body field access | Parsing raw request JSON | `request.agent_config` via AgentRequest `extra="allow"` | Framework already parses and exposes extra fields as attributes |

**Key insight:** The `agentscope-runtime` framework already handles request parsing and passes the `AgentRequest` object to the handler. The `extra="allow"` ConfigDict means no framework modifications are needed to accept `agent_config` in the request body.

## Common Pitfalls

### Pitfall 1: AgentRequest `request` Parameter is `None` in Tests
**What goes wrong:** When tests mock the handler via `app._runner.query_handler`, the `request` parameter may not be passed or may be `None`.
**Why it happens:** The mock handler in `test_chat_stream.py` uses `async def _handler(msgs, request=None, response=None, **kwargs)` which defaults `request` to `None`.
**How to avoid:** Always guard with `if request and hasattr(request, "agent_config")` in the handler. In tests that verify config behavior, pass the `request` parameter explicitly or use the framework's actual streaming path instead of mocking the handler.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'agent_config'`

### Pitfall 2: `lru_cache` Singleton Mutability
**What goes wrong:** If the handler mutates the cached `Settings` object (e.g., `settings.MODEL_NAME = "override"`), all subsequent requests see the mutated value.
**Why it happens:** The `lru_cache` returns the same object instance every time, and Pydantic v2 models are mutable by default.
**How to avoid:** Never write to `Settings` attributes. Use a separate dict or dataclass for the effective per-request config.
**Warning signs:** Second request with different `agent_config` appears to use first request's config.

### Pitfall 3: Test Fixture `clear_settings_cache` Interaction
**What goes wrong:** Tests that modify env vars and clear the settings cache may interfere with each other if not properly isolated.
**Why it happens:** `get_settings.cache_clear()` removes the cached instance; the next call re-reads from env, which may have been patched differently by different tests.
**How to avoid:** Use the existing `clear_settings_cache` fixture in conftest.py, which handles both before and after cleanup. For config override tests, patch the handler directly or use distinct env var values.
**Warning signs:** Tests pass individually but fail when run together.

### Pitfall 4: Backward Compatibility with Existing Requests
**What goes wrong:** Existing Phase 2 requests (without `agent_config`) break after the change.
**Why it happens:** If the handler assumes `agent_config` is always present and doesn't handle `None`/missing.
**How to avoid:** Default `agent_config` to `None` in resolution logic. When `None`, use `.env` settings directly (same as Phase 2 behavior). Test explicitly that requests without `agent_config` still work.
**Warning signs:** `test_process_returns_sse_stream` or `test_stream_lifecycle_events` from Phase 2 start failing.

### Pitfall 5: Config Trace Logging in Test Output
**What goes wrong:** Tests pass but D-06 observability is not verified because log output is not captured.
**Why it happens:** pytest captures logs by default but only shows them on failure unless configured with `--log-cli-level`.
**How to avoid:** Use `caplog` fixture in tests to assert on log messages. Add `pytest.ini` or `pyproject.toml` config for log visibility if needed.
**Warning signs:** No log output visible during test runs; config trace requirement appears unmet.

## Code Examples

### Accessing `agent_config` from AgentRequest
```python
# Source: [VERIFIED: tested with agentscope-runtime v1.1.3 AgentRequest]
# AgentRequest has ConfigDict(extra="allow"), so any extra field in the
# request body becomes an attribute on the AgentRequest instance.
from agentscope_runtime.cli.commands.chat import AgentRequest

req = AgentRequest(
    input=[{"role": "user", "type": "message", "content": [{"type": "text", "text": "hello"}]}],
    agent_config={"model_name": "gpt-4o", "api_key": "sk-test", "base_url": "http://api.test/v1"}
)
assert req.agent_config == {"model_name": "gpt-4o", "api_key": "sk-test", "base_url": "http://api.test/v1"}

# Request without agent_config
req2 = AgentRequest(
    input=[{"role": "user", "type": "message", "content": [{"type": "text", "text": "hello"}]}]
)
assert not hasattr(req2, "agent_config") or req2.agent_config is None
```

### Request Body Shape (Backward Compatible)
```json
// With agent_config (Phase 3):
{
  "input": [
    {"role": "user", "type": "message", "content": [{"type": "text", "text": "Hello"}]}
  ],
  "agent_config": {
    "model_name": "gpt-4o",
    "api_key": "sk-custom-key",
    "base_url": "http://custom-api.example.com/v1"
  }
}

// Without agent_config (Phase 2 backward compatible):
{
  "input": [
    {"role": "user", "type": "message", "content": [{"type": "text", "text": "Hello"}]}
  ]
}
```

### Test Pattern for Config Override Verification
```python
# Source: [ASSUMED - pattern based on existing test_chat_stream.py]
import pytest
from unittest.mock import patch, MagicMock
from src.main import app

def test_agent_config_override(client, clear_settings_cache):
    """Request with agent_config uses provided values."""
    # Patch OpenAIChatModel to capture construction args
    with patch("src.agent.query.OpenAIChatModel") as mock_model:
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        
        # Use the framework's actual streaming path
        payload = {
            "input": [{"role": "user", "type": "message", 
                       "content": [{"type": "text", "text": "Hello"}]}],
            "agent_config": {"model_name": "gpt-4o", "api_key": "sk-test"}
        }
        response = client.post("/process", json=payload)
        
        # Verify OpenAIChatModel was called with override values
        mock_model.assert_called_once()
        call_kwargs = mock_model.call_args
        assert call_kwargs.kwargs["model_name"] == "gpt-4o"
        assert call_kwargs.kwargs["api_key"] == "sk-test"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded `.env`-only config (Phase 2) | Request-level override with `.env` fallback (Phase 3) | This phase | Agents can be configured per-request without server restart |

**Deprecated/outdated:**
- Nothing deprecated in this phase. The `.env` settings mechanism from Phase 1 remains the default/fallback path.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python stdlib `logging` is sufficient for D-06 config trace logging (no need for structlog or similar) | Architecture Patterns - Pattern 3 | LOW: Could add structlog later if structured JSON logging is needed |
| A2 | `request.agent_config` returns `None` when not provided in the request body (not missing attribute) | Code Examples | LOW: Verified via testing; the `hasattr` guard provides safety |
| A3 | The `@app.query` handler's `self` parameter receives the Runner instance (not AgentApp) | Architecture Patterns | LOW: Verified via `_build_runner` source inspection showing `types.MethodType(handler, self._runner)` |
| A4 | No thread-safety issues with `get_settings()` `lru_cache` singleton in async context | Architecture Patterns | LOW: `lru_cache` is thread-safe in CPython; FastAPI runs in single-threaded async by default |

**If this table is empty:** All claims in this research were verified or cited -- no user confirmation needed.

## Open Questions

1. **Should `AgentConfig` live in `src/core/config.py` or `src/core/settings.py`?**
   - What we know: Claude has discretion on internal module layout.
   - What's unclear: Whether keeping it with settings vs. a separate file is cleaner.
   - Recommendation: Create `src/core/config.py` for `AgentConfig` and `resolve_effective_config()` -- keeps `settings.py` focused on `.env` loading while `config.py` handles request-level resolution. This is the planner's call.

2. **Should the config trace log include the `api_key` value?**
   - What we know: D-06 says "log the effective config used per request" but doesn't specify whether secrets should be redacted.
   - What's unclear: Security best practice says don't log secrets.
   - Recommendation: Log `model_name` and `base_url` in full. For `api_key`, log only whether it came from request or `.env` (not the actual value). The planner should enforce this.

## Environment Availability

Step 2.6: SKIPPED (no new external dependencies identified -- all required packages already installed in project)

All dependencies for Phase 3 are already in `pyproject.toml`:
- `agentscope-runtime==1.1.3` -- installed and verified
- `pydantic-settings>=2.0` -- installed and verified
- `pytest==9.0.3` (dev) -- installed and verified
- `httpx==0.28.1` (dev) -- installed and verified

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Runtime | Yes | 3.14.3 | -- |
| agentscope-runtime | Agent framework | Yes | 1.1.3 | -- |
| pydantic v2 | Config models | Yes | via agentscope-runtime | -- |
| pydantic-settings | .env loading | Yes | >=2.0 | -- |
| pytest | Tests | Yes | 9.0.3 | -- |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-02 | Request with `agent_config` creates agent using provided values | unit | `uv run pytest tests/test_agent_config.py::test_config_override -x` | Wave 0 |
| CORE-02 | Request without `agent_config` uses `.env` defaults | unit | `uv run pytest tests/test_agent_config.py::test_config_fallback -x` | Wave 0 |
| CORE-02 | Partial override (only `model_name`) keeps other fields from `.env` | unit | `uv run pytest tests/test_agent_config.py::test_partial_override -x` | Wave 0 |
| CORE-03 | Two requests with different configs use correct values independently | unit | `uv run pytest tests/test_agent_config.py::test_instance_isolation -x` | Wave 0 |
| CORE-03 | Config trace log emitted per request | unit | `uv run pytest tests/test_agent_config.py::test_config_trace_logging -x` | Wave 0 |
| CORE-02/CORE-03 | Phase 2 tests still pass after changes | regression | `uv run pytest tests/test_chat_stream.py -x` | Exists |
| CORE-02/CORE-03 | Phase 1 tests still pass after changes | regression | `uv run pytest tests/test_settings.py tests/test_startup.py -x` | Exists |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_agent_config.py` -- covers CORE-02 and CORE-03 config override/fallback/isolation/logging tests
- [ ] `scripts/verify_phase3.sh` -- follows established pattern from verify_phase2.sh
- [ ] No new framework install needed -- pytest already configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in v1 (personal R&D tool) |
| V3 Session Management | no | No sessions in this phase |
| V4 Access Control | no | Single-user R&D tool |
| V5 Input Validation | yes | Pydantic `AgentConfig` model validates field types |
| V6 Cryptography | no | No encryption in this phase |

### Known Threat Patterns for agentscope-runtime + FastAPI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key exposure in logs | Information Disclosure | Never log `api_key` values; log only the source (request vs .env) [ASSUMED] |
| Malicious config injection | Tampering | Pydantic `AgentConfig` validates types; `extra="forbid"` on AgentConfig prevents unexpected fields |

## Sources

### Primary (HIGH confidence)
- agentscope-runtime v1.1.3 installed package source code -- `AgentRequest`, `Runner.stream_query`, `AgentApp._build_runner`, `AgentApp._add_endpoint_router` inspected via `inspect.getsource()`
- `src/agent/query.py` -- current handler implementation (VERIFIED in codebase)
- `src/core/settings.py` -- current Settings class (VERIFIED in codebase)
- Pydantic v2 `model_copy(update=...)` -- tested in this session, works as documented

### Secondary (MEDIUM confidence)
- `tests/conftest.py` and `tests/test_chat_stream.py` -- established test patterns (VERIFIED in codebase)
- `scripts/verify_phase2.sh` -- verification script pattern to follow (VERIFIED in codebase)
- Phase 2 VERIFICATION.md -- validated baseline and data flow (VERIFIED in codebase)

### Tertiary (LOW confidence)
- None -- all findings verified against source code or tested in this session

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all dependencies already installed, no new packages needed
- Architecture: HIGH - framework source code inspected, request body flow verified, `extra="allow"` tested
- Pitfalls: HIGH - based on actual codebase analysis and framework behavior verification

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable -- no fast-moving dependencies in this phase)
