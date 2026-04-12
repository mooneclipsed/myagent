# Phase 8: Parity & Demo Flows - Research

**Researched:** 2026-04-12
**Domain:** agentscope-runtime session parity, demo script automation, skill/tool/MCP capability documentation
**Confidence:** HIGH

## Summary

Phase 8 validates parity across JSON and Redis session backends and provides documented runnable examples for all capability classes (skill, tool, MCP, resume). The core technical work is well-scoped because Phases 1-7 already built all the underlying capabilities; this phase assembles verification and documentation around them.

The critical D-01 research question is resolved: agentscope-runtime provides a **distinct skill mechanism** via `Toolkit.register_agent_skill(skill_dir)`, separate from `register_tool_function()`. Skills are directory-based knowledge packs (containing a `SKILL.md` with YAML front matter) that inject context into the agent's system prompt via `toolkit.get_agent_skill_prompt()`. They do NOT execute code like tools. The framework dependency `python-frontmatter` (v1.1.0) is already installed. This means Phase 8 creates a separate `demo_skill.py` with a skill directory example, fully covering the skill capability class.

Parity validation (RES-05) compares conversation content consistency across JSON and Redis backends using the same session save/load/resume flow. The existing `test_session.py` (457 lines, 10 tests) establishes the fakeredis pattern and `SESSION_BACKEND` switching that the parity test will reuse. Demo scripts (DEV-01, DEV-03) are standalone Python automation scripts with built-in assertions, placed in `scripts/demos/` and executed via `uv run`.

**Primary recommendation:** Build 4 demo scripts (tool, skill, MCP, resume) plus a parity pytest test, then update README.md as the unified getting-started guide. All infrastructure already exists in the codebase.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Research agentscope-runtime's independent skill mechanism during the research phase. If the framework provides a distinct skill API (e.g., pipeline, workflow, service functions), create a separate skill demo example. If skill and tool are the same concept in the framework, document tool examples as covering the skill category with an explicit note.
- **D-02:** Demo flows are Python automation scripts with built-in assertions. Scripts exit with non-zero code on failure, making them suitable for automated validation.
- **D-03:** One independent script per capability class: `demo_tool.py`, `demo_mcp.py`, `demo_resume.py`, and `demo_skill.py` (pending D-01 research outcome). Each script can run standalone.
- **D-04:** Scripts are placed in `scripts/demos/` directory and executed via `uv run`. Dependency on `httpx` (already a dev dependency).
- **D-05:** Parity validation verifies **conversation content consistency** -- the same session data resumed from JSON and Redis backends produces the same conversation result. This is the core RES-05 requirement.
- **D-06:** Parity is implemented as a **pytest test** (not a demo script). The test runs the same resume flow against both backends and asserts the final responses are consistent.
- **D-07:** Redis is simulated with **fakeredis** in parity tests. CI remains zero-dependency. Consistent with Phase 7 test pattern.
- **D-08:** Update **README.md** as the unified getting-started guide. No separate docs/ directory.
- **D-09:** README content is concise and practical: project introduction, quick-start instructions, demo run commands per capability, and expected output examples.

### Claude's Discretion
- Exact pytest test structure for parity validation, as long as it covers conversation content consistency.
- README formatting and section organization.
- Whether demo scripts need a shared helper module (e.g., common httpx client setup).
- Internal structure of each demo script.
- How to handle demo scripts that require a running service (pre-start check, auto-start, or document prerequisite).

### Deferred Ideas (OUT OF SCOPE)
- Session cleanup / TTL / expiration -- still deferred. Manual cleanup acceptable for R&D use.
- Session listing / management API -- still deferred. Not needed for core validation.
- Structured call-chain tracing (CAP-05) -- still deferred to future phase with OpenTelemetry.
- Full API documentation (OpenAPI/Swagger) -- deferred. README covers practical usage.
- Performance benchmarking between JSON and Redis backends -- deferred. Parity focuses on correctness, not performance.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RES-05 | User can verify JSON/Redis resume behavior is consistent for core flows | Parity test switches `SESSION_BACKEND` between `"json"` and `"redis"`, runs identical resume flow, compares conversation results. fakeredis for Redis simulation (D-06, D-07). Existing `test_session.py` patterns provide proven fixture setup. |
| DEV-01 | User can start and validate the service through a documented runnable demo flow | README.md updated with quick-start: clone -> configure .env -> `uv sync` -> `bash scripts/run_service.sh` -> run demo scripts. Demo scripts exit non-zero on failure. |
| DEV-03 | User can run at least one documented example per capability class (skill/tool/MCP/resume) | Four standalone scripts in `scripts/demos/`: `demo_tool.py`, `demo_skill.py`, `demo_mcp.py`, `demo_resume.py`. Each sends HTTP requests to `/process` endpoint, parses SSE responses, asserts expected content. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | HTTP client for demo scripts | Already a dev dependency; synchronous API suitable for standalone scripts; supports streaming for SSE parsing |
| fakeredis | 2.35.0 | Redis simulation in parity tests | Already a dev dependency; consistent with Phase 7 test pattern; CI stays zero-dependency |
| pytest | 9.0.3 | Test runner for parity test | Project standard test runner; existing conftest.py fixtures reusable |
| python-frontmatter | 1.1.0 | Parse SKILL.md YAML front matter | Installed as agentscope dependency; used by `Toolkit.register_agent_skill()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| agentscope-runtime | 1.1.3 | Core framework | Provides `Toolkit.register_agent_skill()`, `JSONSession`, `RedisSession`, `ReActAgent` |
| FastAPI/TestClient | via agentscope | Demo script HTTP target | Demo scripts hit the `/process` endpoint; parity tests use TestClient |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx for demo scripts | requests | httpx already a project dependency; requests would add another dep |
| fakeredis for parity | Real Redis in Docker | fakeredis keeps CI zero-dep per D-07; real Redis better for integration but out of scope |

**Installation:**
No new packages needed. All dependencies are already in `pyproject.toml`:
```
[dependency-groups]
dev = [
    "fakeredis>=2.31.0",
    "httpx==0.28.1",
    "pytest==9.0.3",
]
```

**Version verification (all confirmed via `uv pip show`):**
- httpx: 0.28.1 [VERIFIED: uv pip show]
- fakeredis: 2.35.0 [VERIFIED: uv pip show]
- pytest: 9.0.3 [VERIFIED: uv pip show]
- python-frontmatter: 1.1.0 [VERIFIED: uv pip show]

## Architecture Patterns

### Recommended Project Structure
```
scripts/
├── demos/                    # NEW: demo scripts directory
│   ├── _helpers.py           # shared httpx client + SSE parsing utilities (Claude's discretion)
│   ├── demo_tool.py          # tool capability demo
│   ├── demo_skill.py         # skill capability demo
│   ├── demo_mcp.py           # MCP capability demo
│   └── demo_resume.py        # resume/session persistence demo
├── run_service.sh            # EXISTING: service starter
└── verify_phase*.sh          # EXISTING: phase verification scripts

skills/                       # NEW: skill directory for demo_skill.py
└── example_skill/
    └── SKILL.md              # skill definition with YAML front matter

tests/
├── test_parity.py            # NEW: RES-05 parity test
├── test_session.py           # EXISTING: session tests (reuse patterns)
└── conftest.py               # EXISTING: shared fixtures

README.md                     # UPDATE: unified getting-started guide
```

### Pattern 1: D-01 Skill Registration (Distinct from Tools)
**What:** agentscope-runtime provides a separate `register_agent_skill()` mechanism for injecting domain knowledge into the agent's system prompt. Skills are NOT tool functions -- they are directory-based knowledge packs.
**When to use:** For CAP-01 skill capability validation.
**Example:**
```python
# Source: agentscope/tool/_toolkit.py lines 1323-1389 [VERIFIED: source code inspection]
# Skill directory structure:
# skills/example_skill/SKILL.md
# ---
# name: example-skill
# description: A demo skill that provides example knowledge to the agent.
# ---
# This skill provides example knowledge about [topic].
# The agent should use this context when responding to relevant queries.

from src.tools import toolkit
toolkit.register_agent_skill(skill_dir="skills/example_skill")
# After registration, toolkit.get_agent_skill_prompt() returns the combined prompt.
# ReActAgent.sys_prompt property auto-appends this to _sys_prompt.
```

### Pattern 2: Parity Test (Session Backend Consistency)
**What:** Run identical resume flow against both JSON and Redis backends, compare conversation results.
**When to use:** RES-05 verification.
**Example:**
```python
# Source: tests/test_session.py patterns [VERIFIED: codebase inspection]
import fakeredis.aioredis
from agentscope.session import JSONSession, RedisSession
from src.agent.session import reset_session_backend

def test_parity_json_redis_resume(client, configured_env, clear_settings_cache, monkeypatch, session_dir):
    """RES-05: Same session data produces same conversation result across backends."""
    session_id = "parity-test-001"
    # ... save session with JSON backend, save same data with Redis (fakeredis),
    #     resume both, compare agent memory/content ...
    reset_session_backend()
```

### Pattern 3: Demo Script Structure
**What:** Standalone Python script with httpx, SSE parsing, and assertions.
**When to use:** DEV-01, DEV-03 demo scripts.
**Example:**
```python
# scripts/demos/demo_tool.py
"""Demo: trigger a tool call through the chat endpoint."""
import sys
import httpx

SERVICE_URL = "http://127.0.0.1:8000"

def main():
    # Check service is running (or document prerequisite)
    response = httpx.post(f"{SERVICE_URL}/process", json={
        "input": [{"role": "user", "content": [{"type": "text", "text": "What is the weather in Tokyo?"}]}]
    }, timeout=30.0)
    # Parse SSE events, assert tool was called, assert response contains weather data
    assert "sunny" in response.text.lower() or response.status_code == 200
    print("PASS: demo_tool.py")

if __name__ == "__main__":
    main()
```

### Anti-Patterns to Avoid
- **Running demo scripts without a live service:** Demo scripts hit the real HTTP endpoint. They MUST either check service availability first and exit with a clear message, or the README must document the prerequisite step of starting the service. Do not silently fail with connection errors.
- **Using real Redis in parity tests:** D-07 mandates fakeredis. Real Redis would break CI.
- **Registering skills as tool functions:** Skills and tools are distinct mechanisms in agentscope-runtime. Skills inject prompt context; tools execute code. Do not confuse them.
- **Testing performance instead of correctness:** RES-05 is about conversation content consistency, not response time or throughput.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE response parsing | Custom SSE parser | httpx streaming + simple line parsing | SSE format is simple (`data: {...}` lines); complex parsers add unnecessary dependencies |
| Skill registration | Manual prompt injection | `toolkit.register_agent_skill(skill_dir)` | Framework handles SKILL.md parsing, YAML front matter validation, prompt template formatting |
| Session state comparison | Custom serialization diff | Direct `memory.get_memory()` comparison | Both backends serialize/deserialize through the same `save_session_state`/`load_session_state` interface |
| Redis simulation in tests | Docker Compose / real Redis | fakeredis | D-07 locked decision; fakeredis is proven in Phase 7 tests (test_session.py) |

**Key insight:** The session backend abstraction layer (`save_session_state` / `load_session_state`) makes parity testing straightforward -- no need to peek into JSON files or Redis keys directly.

## Common Pitfalls

### Pitfall 1: Demo Scripts Require Running Service
**What goes wrong:** Demo scripts try to connect to `http://127.0.0.1:8000` but the service is not running. Connection refused error confuses the user.
**Why it happens:** Demo scripts are HTTP clients, not in-process tests. They need a separate running server.
**How to avoid:** Add a pre-check at the top of each demo script: `httpx.get(f"{SERVICE_URL}/docs", timeout=2.0)`. If it fails, print a clear message like "Start the service first: bash scripts/run_service.sh" and exit with code 1.
**Warning signs:** Demo script exits with `ConnectionRefusedError` or `httpx.ConnectError`.

### Pitfall 2: Skill Directory Not Found at Runtime
**What goes wrong:** `toolkit.register_agent_skill(skill_dir="skills/example_skill")` raises `ValueError: The skill directory does not exist` because the path is relative and CWD is not the project root.
**Why it happens:** Demo scripts run via `uv run` from the project root, but the skill directory path must be correct relative to the CWD.
**How to avoid:** Use an absolute path derived from `__file__` or `Path(__file__).parent.parent.parent / "skills" / "example_skill"` in the registration code. Or ensure the skill is registered in `src/tools/__init__.py` with a path relative to the project root.
**Warning signs:** `ValueError` at import time when toolkit tries to register the skill.

### Pitfall 3: Parity Test State Leakage Between Backend Switches
**What goes wrong:** After testing the JSON backend, switching to Redis backend for parity comparison still uses the cached JSON session backend because `get_session_backend()` is a singleton.
**Why it happens:** `_session_backend` is a module-level global that caches the first backend created. Tests must call `reset_session_backend()` between backend switches.
**How to avoid:** Always call `reset_session_backend()` AND `get_settings.cache_clear()` between backend switches. Existing test patterns in `test_session.py` show this clearly (lines 285-286, 331-334).
**Warning signs:** Parity test passes trivially because both runs use the same backend.

### Pitfall 4: SSE Parsing in Demo Scripts Misses Multi-Event Responses
**What goes wrong:** Demo scripts parse only the first SSE event and miss the actual content, which arrives in later `content(in_progress)` events.
**Why it happens:** The agentscope SSE lifecycle emits multiple events: `response(created)` -> `response(in_progress)` -> `message(in_progress)` -> `content(in_progress)` x N -> `message(completed)` -> `response(completed)` -> `[DONE]`.
**How to avoid:** Parse ALL SSE events, extract text from `content(in_progress)` events, and check for `response(completed)` to confirm the stream finished. Reuse `_parse_sse_events()` pattern from `test_chat_stream.py`.
**Warning signs:** Demo assertion fails because it checked the wrong event type or missed the content entirely.

### Pitfall 5: Toolkit Singleton State Persists Across Demo Script Runs
**What goes wrong:** If skills are registered to the shared `toolkit` singleton, they persist for the lifetime of the service. Re-running demo scripts against a running service sees cumulative registrations.
**Why it happens:** `toolkit` in `src/tools/__init__.py` is a module-level singleton. Skill registration is additive.
**How to avoid:** For the skill demo, register the skill in the demo's context or ensure the service restarts between demos. The README should document restarting the service between demos if needed. Alternatively, register the example skill permanently in `src/tools/__init__.py` so it is always available.
**Warning signs:** `ValueError: An agent skill with name 'X' is already registered` on service restart.

## Code Examples

### Skill Directory Structure and Registration
```python
# Source: agentscope/tool/_toolkit.py [VERIFIED: source code inspection]

# 1. Create skill directory: skills/example_skill/SKILL.md
# ---
# name: example-skill
# description: A demo skill that provides example knowledge to the agent.
# ---
# When the user asks about the demo skill topic, respond with a reference
# to this skill context.

# 2. Register in src/tools/__init__.py (or at demo time):
import os
from src.tools import toolkit

skill_dir = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "example_skill")
toolkit.register_agent_skill(skill_dir=os.path.normpath(skill_dir))

# 3. ReActAgent.sys_prompt automatically includes skill prompt:
# Source: agentscope/agent/_react_agent.py lines 366-373 [VERIFIED: source code inspection]
@property
def sys_prompt(self) -> str:
    agent_skill_prompt = self.toolkit.get_agent_skill_prompt()
    if agent_skill_prompt:
        return self._sys_prompt + "\n\n" + agent_skill_prompt
    else:
        return self._sys_prompt
```

### Parity Test Pattern
```python
# Source: tests/test_session.py patterns [VERIFIED: codebase inspection]

def test_parity_json_redis_resume(client, configured_env, clear_settings_cache, monkeypatch, tmp_path):
    """RES-05: Same session data produces consistent results across JSON and Redis backends."""
    import fakeredis.aioredis
    from agentscope.session import JSONSession, RedisSession
    from agentscope.memory import InMemoryMemory
    from agentscope.message import Msg
    from src.agent.session import reset_session_backend

    session_id = "parity-test-001"

    # --- JSON backend ---
    monkeypatch.setenv("SESSION_BACKEND", "json")
    monkeypatch.setenv("SESSION_DIR", str(tmp_path / "json_sessions"))
    reset_session_backend()
    get_settings.cache_clear()

    # ... run resume flow, capture result_json ...

    # --- Redis backend ---
    monkeypatch.setenv("SESSION_BACKEND", "redis")
    reset_session_backend()
    get_settings.cache_clear()
    # Override with fakeredis
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    fake_backend = RedisSession(connection_pool=fake_redis.connection_pool, key_prefix="agentops:")
    monkeypatch.setattr(session_mod, "_session_backend", fake_backend)

    # ... run same resume flow, capture result_redis ...

    # Compare
    assert result_json == result_redis
    reset_session_backend()
```

### Demo Script SSE Parsing Pattern
```python
# Source: tests/test_chat_stream.py [VERIFIED: codebase inspection]

def parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE text into a list of decoded JSON event dicts."""
    import json
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("data:"):
            continue
        data_str = line[len("data:"):].strip()
        if data_str == "[DONE]":
            break
        try:
            events.append(json.loads(data_str))
        except json.JSONDecodeError:
            continue
    return events

def extract_text_from_events(events: list[dict]) -> str:
    """Extract concatenated text from SSE content events."""
    texts = []
    for event in events:
        if event.get("type") == "response.content.delta" or "text" in str(event):
            # Extract text delta from the event structure
            delta = event.get("delta", event.get("text", ""))
            if isinstance(delta, str):
                texts.append(delta)
    return "".join(texts)
```

### Fakeredis Backend Injection Pattern
```python
# Source: tests/test_session.py lines 287-293 [VERIFIED: codebase inspection]

import fakeredis.aioredis
from agentscope.session import RedisSession
from src.agent import session as session_mod

fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
fake_backend = RedisSession(
    connection_pool=fake_redis.connection_pool,
    key_prefix="agentops:",
)
monkeypatch.setattr(session_mod, "_session_backend", fake_backend)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tool-only capability demos | Separate skill + tool + MCP demos | Phase 8 | Skills are distinct from tools in agentscope; need separate demo |
| Real Redis in tests | fakeredis simulation | Phase 7 | CI stays zero-dependency; D-07 locked decision |
| No service documentation | README.md getting-started guide | Phase 8 | DEV-01/DEV-03 requirement; users need runnable examples |

**Deprecated/outdated:**
- Phase 4 assumed skill and tool might be the same concept (deferred distinction). Phase 8 research confirms they are distinct in agentscope-runtime.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Demo scripts can trigger tool calls by asking the LLM agent to use a tool (e.g., "What is the weather in Tokyo?") and the deterministic mock tool returns a predictable response. | Architecture Patterns | If the LLM does not reliably trigger tool calls, demos become flaky. Mitigation: demo scripts should use clear, unambiguous prompts. |
| A2 | The shared `toolkit` singleton can safely register an example skill in `src/tools/__init__.py` without breaking existing tool/MCP functionality. | Architecture Patterns | If skill registration conflicts with existing tools, registration must be conditional or in a separate initialization path. |
| A3 | Demo scripts do NOT need real LLM API calls -- they can use the live service with a real API key configured in `.env`. | Architecture Patterns | If `.env` is not configured or API key is invalid, demo scripts fail. README must document this prerequisite clearly. |

**If this table is empty:** All claims in this research were verified or cited -- no user confirmation needed.

## Open Questions

1. **Demo script LLM dependency**
   - What we know: Demo scripts hit the live `/process` endpoint, which creates a real `OpenAIChatModel` and makes LLM API calls. This requires a valid `.env` configuration.
   - What's unclear: Whether the user expects demo scripts to work with mocked LLM responses (no API key needed) or with real LLM calls (API key required).
   - Recommendation: Document the `.env` prerequisite clearly in README. Demo scripts check service availability but do NOT mock the LLM -- they exercise the full stack.

2. **Skill registration timing**
   - What we know: `toolkit` is a singleton created at import time. Skills should be registered after the toolkit is created.
   - What's unclear: Whether to register the example skill in `src/tools/__init__.py` (always available) or only when demo_skill.py runs.
   - Recommendation: Register in `src/tools/__init__.py` so it is always available for both demo scripts and tests. The skill is lightweight (prompt injection only).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | Yes | 3.14 (via uv) | -- |
| uv | Package management | Yes | Available | -- |
| httpx | Demo scripts | Yes | 0.28.1 | -- |
| fakeredis | Parity tests | Yes | 2.35.0 | -- |
| pytest | Tests | Yes | 9.0.3 | -- |
| python-frontmatter | Skill registration | Yes | 1.1.0 | -- |
| agentscope-runtime | Core framework | Yes | 1.1.3 | -- |
| Redis server | Parity tests | N/A | N/A | fakeredis used per D-07 |
| FastAPI service | Demo scripts | Requires manual start | -- | Scripts check and print instructions |

**Missing dependencies with no fallback:**
- None -- all required packages are installed.

**Missing dependencies with fallback:**
- Redis server: Not needed because fakeredis is used per locked decision D-07.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_parity.py -x -v` |
| Full suite command | `uv run pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RES-05 | JSON/Redis resume behavior is consistent | unit (pytest) | `uv run pytest tests/test_parity.py -x -v` | Wave 0 (new) |
| DEV-01 | Documented runnable demo flow | manual + smoke | README instructions + run demo scripts | Wave 0 (README update) |
| DEV-03 | Examples per capability class | smoke (demo scripts) | `uv run scripts/demos/demo_tool.py && uv run scripts/demos/demo_skill.py && uv run scripts/demos/demo_mcp.py && uv run scripts/demos/demo_resume.py` | Wave 0 (new) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_parity.py -x -v`
- **Per wave merge:** `uv run pytest tests/ -x -v`
- **Phase gate:** Full suite green + all 4 demo scripts pass (service running)

### Wave 0 Gaps
- [ ] `tests/test_parity.py` -- covers RES-05
- [ ] `scripts/demos/demo_tool.py` -- covers DEV-03 (tool)
- [ ] `scripts/demos/demo_skill.py` -- covers DEV-03 (skill)
- [ ] `scripts/demos/demo_mcp.py` -- covers DEV-03 (MCP)
- [ ] `scripts/demos/demo_resume.py` -- covers DEV-03 (resume)
- [ ] `skills/example_skill/SKILL.md` -- skill definition for demo_skill.py
- [ ] `README.md` update -- covers DEV-01

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in R&D platform |
| V3 Session Management | yes | Session ID validation via `validate_session_id()` (already implemented, T-6-01) |
| V4 Access Control | no | Single-user R&D tool |
| V5 Input Validation | yes | Pydantic `Settings` model + `validate_session_id()` path traversal prevention |
| V6 Cryptography | no | No encryption at rest for sessions (R&D scope) |

### Known Threat Patterns for FastAPI + Session Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via session_id | Tampering | `validate_session_id()` rejects `/`, `\`, `.`, `..` characters |
| SSRF via model base_url | Tampering | `.env` configuration only; no user-supplied URLs in demo scope |
| Unvalidated SSE content | Tampering | Demo scripts parse JSON events with error handling |

## Sources

### Primary (HIGH confidence)
- agentscope/tool/_toolkit.py lines 1323-1434 -- `register_agent_skill()`, `get_agent_skill_prompt()` implementation [VERIFIED: source code inspection]
- agentscope/agent/_react_agent.py lines 366-373 -- `sys_prompt` property with skill prompt injection [VERIFIED: source code inspection]
- agentscope/tool/_types.py lines 152-160 -- `AgentSkill(TypedDict)` definition [VERIFIED: source code inspection]
- tests/test_session.py -- existing session test patterns, fakeredis injection, backend switching [VERIFIED: codebase inspection]
- tests/conftest.py -- shared fixtures (configured_env, clear_settings_cache, client) [VERIFIED: codebase inspection]
- pyproject.toml -- dependency declarations verified against installed versions [VERIFIED: uv pip show]

### Secondary (MEDIUM confidence)
- tests/test_chat_stream.py -- `_parse_sse_events()` and `_make_mock_handler()` patterns for SSE parsing [VERIFIED: codebase inspection]
- scripts/run_service.sh -- service startup command [VERIFIED: codebase inspection]

### Tertiary (LOW confidence)
- None -- all findings verified from source code or installed packages.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all versions verified via `uv pip show`, all dependencies already installed
- Architecture: HIGH - skill mechanism confirmed via source code inspection; parity pattern proven in existing tests
- Pitfalls: HIGH - derived from existing codebase patterns and framework behavior verification

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable framework, no fast-moving dependencies)
