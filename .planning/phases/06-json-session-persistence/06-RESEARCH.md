# Phase 6: JSON Session Persistence - Research

**Researched:** 2026-04-12
**Domain:** agentscope-runtime session persistence, InMemoryMemory serialization
**Confidence:** HIGH

## Summary

Phase 6 adds server-side session persistence using agentscope-runtime's built-in `JSONSession` class. The framework already provides all the necessary primitives: `JSONSession` handles file I/O with async `save_session_state` / `load_session_state` methods, and `InMemoryMemory` provides `state_dict()` / `load_state_dict()` for memory serialization. The `AgentRequest` schema already includes `session_id` and `user_id` fields, and the `Runner.stream_query` already auto-generates a UUID for `session_id` when absent. The primary work is wiring these existing primitives into the query handler lifecycle: load memory before agent creation, save memory after the response completes.

The key integration point is `src/agent/query.py`. The `chat_query` handler currently creates a fresh `InMemoryMemory()` per request. Phase 6 wraps this with session load (before agent creation) and session save (after streaming completes). The existing SSE streaming contract and request-scoped agent pattern are fully preserved -- session persistence is an additive layer.

**Primary recommendation:** Use `JSONSession` with keyword argument naming for state modules (e.g., `memory=agent.memory`) and integrate save/load into the existing `chat_query` handler. Add `SESSION_DIR` to `Settings` for configurable storage location.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use agentscope-runtime's built-in `JSONSession` for session storage and `InMemoryMemory.state_dict()` / `load_state_dict()` for memory serialization. Leverage the framework's existing serialization rather than building custom JSON storage.
- **D-02:** Persist only the agent's memory (conversation history). Do NOT persist `agent_config` -- each resume re-evaluates config from request or `.env` defaults.
- **D-03:** Agent config changes between save and resume are allowed. If the client provides `agent_config` during resume, it is used; otherwise `.env` defaults apply. No config locking to original session values.
- **D-04:** Client provides `session_id` in the request body. When absent or empty, a new session is created and the generated `session_id` is returned in the response. When present, the server loads the existing session and resumes.
- **D-05:** Extend the existing `/process` endpoint by adding an optional `session_id` field to the request body. When `session_id` is absent, behavior is identical to current stateless flow (backward compatible). When present, session persistence is activated.
- **D-06:** Request body becomes: `{ "messages": [...], "agent_config": {...}, "session_id": "abc123" }`. All three top-level fields are optional.
- **D-07:** On resume, the server loads the saved memory state from JSON, creates a fresh `ReActAgent` with the restored `InMemoryMemory`, and processes the new message. The client only needs to send `session_id` + new message -- no need to resend full conversation history.
- **D-08:** After each request with a `session_id`, the updated memory state is saved back to the JSON file. This ensures the session is always up-to-date for the next resume.
- **D-09:** Sessions are stored in a flat `sessions/` directory (configurable via environment variable, e.g., `SESSION_DIR`). Each session is one JSON file: `{session_id}.json`.
- **D-10:** No automatic cleanup or TTL expiration. Session files persist until manually deleted. Cleanup strategy deferred to Phase 8 or later.
- **D-11:** Verification follows the established pattern: `pytest` automated tests + smoke script. Tests validate save, load, resume round-trip, and backward compatibility (requests without session_id).
- **D-12:** Success criteria tests: (1) a chat with session_id persists session state to JSON file, (2) a subsequent chat with same session_id resumes and has access to prior context, (3) a chat without session_id behaves identically to Phase 5 (backward compatibility).

### Claude's Discretion
- Exact `session_id` generation format (UUID, nanoid, etc.) -- as long as it's unique and URL-safe.
- Exact JSON file internal structure -- as long as JSONSession's built-in format is used.
- Internal module layout for session management code.
- Exact test structure and smoke script shape, following established Phase 1-5 patterns.
- How to integrate session save/load into the query handler lifecycle (before/after agent call).

### Deferred Ideas (OUT OF SCOPE)
- Session cleanup / TTL / expiration -- deferred to Phase 8 or later. Manual cleanup is acceptable for R&D use.
- Persisting `agent_config` alongside session state -- deferred. Could be useful for reproducibility but adds complexity.
- Session listing / management API -- deferred. Not needed for core save/resume validation.
- Session metadata (timestamps, turn counts) -- deferred. Not required for RES-01/RES-03.
- Redis session persistence -- Phase 7.
- Parity validation between JSON and Redis -- Phase 8.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RES-01 | User can persist session state to JSON-file backend | `JSONSession.save_session_state()` + `InMemoryMemory.state_dict()` provide complete save mechanism. Session directory configurable via `SESSION_DIR` env var. |
| RES-03 | User can resume chat from previously persisted session in JSON backend | `JSONSession.load_session_state()` + `InMemoryMemory.load_state_dict()` provide complete restore mechanism. Agent created fresh with restored memory. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| agentscope-runtime | 1.1.3 | Agent runtime with session support | Built-in `JSONSession` and `InMemoryMemory` serialization eliminate need for custom session code. [VERIFIED: source code inspection in .venv] |
| agentscope (via runtime) | bundled | JSONSession, InMemoryMemory, Msg | Framework primitives for session persistence. [VERIFIED: source code inspection + live round-trip test] |
| aiofiles | bundled dependency | Async file I/O used by JSONSession | Required by `JSONSession` internally; already installed as transitive dependency. [VERIFIED: import succeeds] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | >=2.0 | `SESSION_DIR` env var config | Add `SESSION_DIR` to existing `Settings` class. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSONSession (built-in) | Custom JSON file storage | Custom storage reinvents serialization; JSONSession handles Msg serialization/de-serialization natively. No reason to hand-roll. |
| uuid4 session_id | nanoid, ulid | UUID is already used by Runner.stream_query auto-generation; consistent with framework. |

**Installation:**
No new packages needed. All required modules are already available via `agentscope-runtime==1.1.3`.

**Version verification:**
```
agentscope-runtime==1.1.3 (installed, pyproject.toml)
JSONSession import: verified working
InMemoryMemory serialization: verified round-trip with live test
aiofiles: installed as transitive dependency
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── agent/
│   ├── query.py          # MODIFY: add session load/save around agent lifecycle
│   └── session.py        # NEW: JSONSession wrapper, session_id generation
├── core/
│   ├── config.py         # UNCHANGED
│   └── settings.py       # MODIFY: add SESSION_DIR setting
├── app/
│   └── lifespan.py       # MODIFY: add session directory initialization at startup
└── main.py               # UNCHANGED
```

### Pattern 1: Session-Scoped Agent with Memory Restore
**What:** Load saved memory before agent creation, save updated memory after response.
**When to use:** Every request where `session_id` is present in the request.
**Example:**
```python
# Source: [VERIFIED: agentscope source code inspection + live test]
from agentscope.session import JSONSession
from agentscope.memory import InMemoryMemory

# Initialize session backend (once, at startup or per-request)
session = JSONSession(save_dir=session_dir)

# On resume: create memory, load state into it
memory = InMemoryMemory()
await session.load_session_state(
    session_id="test-session-1",
    memory=memory,  # keyword arg name becomes key in JSON
)

# Create agent with restored memory
agent = ReActAgent(name="agentops", memory=memory, ...)

# After agent processes message, save updated memory
await session.save_session_state(
    session_id="test-session-1",
    memory=agent.memory,  # agent.memory is the same InMemoryMemory instance
)
```

### Pattern 2: Conditional Session Activation
**What:** When `session_id` is absent, skip session load/save entirely (backward compatible).
**When to use:** Every request -- check `request.session_id` presence.
**Example:**
```python
# In chat_query handler:
session_id = request.session_id if request else None

if session_id:
    memory = InMemoryMemory()
    await session.load_session_state(session_id=session_id, memory=memory)
else:
    memory = InMemoryMemory()  # fresh, no load

agent = ReActAgent(name="agentops", memory=memory, ...)

# ... streaming ...

# After streaming completes:
if session_id:
    await session.save_session_state(session_id=session_id, memory=agent.memory)
```

### Pattern 3: JSONSession as Singleton or Per-Request
**What:** `JSONSession` is lightweight and only stores `save_dir`. Can be created once at startup and reused.
**When to use:** At startup (lifespan) or as module-level singleton.
**Example:**
```python
# Module-level singleton
from agentscope.session import JSONSession
from src.core.settings import get_settings

_session_backend: JSONSession | None = None

def get_session_backend() -> JSONSession:
    global _session_backend
    if _session_backend is None:
        settings = get_settings()
        _session_backend = JSONSession(save_dir=settings.SESSION_DIR)
    return _session_backend
```

### Anti-Patterns to Avoid
- **Hand-rolling JSON serialization of Msg objects:** `Msg.to_dict()` / `Msg.from_dict()` have specific format requirements; `InMemoryMemory.state_dict()` / `load_state_dict()` handle this correctly. Always use framework methods. [VERIFIED: source code shows Msg serialization includes id, timestamp, metadata, invocation_id fields]
- **Saving memory before streaming completes:** Memory must be saved AFTER the agent finishes processing (after the `async for` loop), not before. The agent adds messages to memory during processing.
- **Persisting agent_config:** D-02 explicitly forbids this. Config is re-resolved from request or .env on each resume.
- **Blocking the SSE stream for save:** `save_session_state` is async and uses `aiofiles`. It should be called after the last SSE event is yielded, not during streaming.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON file storage for sessions | Custom file writer/reader with JSON serialization | `JSONSession` | Handles path construction, directory creation (`os.makedirs`), async I/O, Msg serialization. [VERIFIED: source code] |
| Memory serialization | Custom dict construction from Msg objects | `InMemoryMemory.state_dict()` / `load_state_dict()` | Handles nested `Msg.to_dict()` / `Msg.from_dict()`, compressed summary, marks. [VERIFIED: live round-trip test] |
| Session ID generation | Custom ID format | `uuid.uuid4()` (already used by Runner.stream_query) | Runner auto-generates UUID when session_id is absent; consistent with framework. [VERIFIED: runner.py line 225] |

**Key insight:** agentscope-runtime provides a complete session persistence layer. Phase 6's job is wiring, not building.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None -- no databases or external stores currently exist | New: JSON files in `sessions/` directory created by this phase |
| Live service config | None -- no external service config outside git | None |
| OS-registered state | None | None |
| Secrets/env vars | New: `SESSION_DIR` env var (defaults to `./sessions/`) | Code edit: add to Settings class |
| Build artifacts | None | None |

**Nothing found in category:** No existing runtime state conflicts. This is a greenfield addition.

## Common Pitfalls

### Pitfall 1: Runner Overwrites session_id
**What goes wrong:** `Runner.stream_query` (line 225) does `request.session_id = request.session_id or str(uuid.uuid4())`. This means even if the client sends an empty string, it gets replaced with a UUID.
**Why it happens:** The framework normalizes missing session_ids.
**How to avoid:** When the client sends a non-empty `session_id`, it passes through unchanged. The planner must understand that the handler receives the already-normalized `request.session_id` -- it will always be a non-empty string. To distinguish "client wants new session" from "client wants to resume", check if the session file exists on disk (via `load_session_state` with `allow_not_exist=True`).
**Warning signs:** Session always creates new files even when client provides an ID.

### Pitfall 2: Accessing agent.memory After Streaming
**What goes wrong:** The `agent.memory` attribute must be accessed after the streaming loop completes. During streaming, messages are still being added.
**Why it happens:** The async generator pattern means the handler function runs concurrently with SSE delivery.
**How to avoid:** Place the save call AFTER the `async for msg, last in stream_printing_messages(...)` loop exits. At that point, all messages have been added to memory.
**Warning signs:** Saved sessions contain incomplete conversation history.

### Pitfall 3: State Module Keyword Argument Naming
**What goes wrong:** `JSONSession.save_session_state(**state_modules_mapping)` uses the keyword argument name as the key in the JSON file. If you use `memory=agent.memory` on save but `memory=m` on load, the keys match. But using different names (e.g., `mem=...`) would cause a mismatch.
**Why it happens:** The state dict structure is `{"memory": {...}}` because the kwarg name was "memory".
**How to avoid:** Always use the same keyword argument name (e.g., `memory=`) for both save and load calls.
**Warning signs:** `load_session_state` silently skips loading because the key doesn't match.

### Pitfall 4: Session Directory Not Created at Startup
**What goes wrong:** `JSONSession._get_save_path()` calls `os.makedirs(self.save_dir, exist_ok=True)` before each save, but if the directory path is invalid or permissions are wrong, it fails at first save attempt.
**Why it happens:** Directory creation is lazy (on first save).
**How to avoid:** Create and validate the session directory at startup (in lifespan). This also provides fail-fast behavior for misconfigured paths.
**Warning signs:** First session save fails with `PermissionError` or `OSError`.

### Pitfall 5: Backward Compatibility with Phase 5 Tests
**What goes wrong:** Adding session logic to the query handler could break existing tests that mock the handler at `app._runner.query_handler`. If session save/load is called inside the handler, the mock must account for it.
**Why it happens:** Existing tests patch `app._runner.query_handler` to bypass the real handler. The mock handler doesn't call session methods.
**How to avoid:** Either (a) keep session save/load outside the mock boundary (in the runner layer), or (b) mock the session backend in existing tests. The cleanest approach is to have session logic inside `chat_query` so that mocking `query_handler` bypasses all session code.
**Warning signs:** Existing Phase 2-5 tests start failing.

## Code Examples

### Verified: JSONSession Save/Load Round-Trip
```python
# Source: [VERIFIED: live test execution 2026-04-12]
from agentscope.session import JSONSession
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
import asyncio, tempfile

async def round_trip():
    tmpdir = tempfile.mkdtemp()
    session = JSONSession(save_dir=tmpdir)

    # Save
    memory = InMemoryMemory()
    await memory.add(Msg(name="user", content="hello world", role="user"))
    await session.save_session_state(session_id="test-1", memory=memory)

    # Load
    memory2 = InMemoryMemory()
    await session.load_session_state(session_id="test-1", memory=memory2)

    msgs = await memory2.get_memory()
    assert msgs[0].content == "hello world"  # PASSES
```

### Verified: InMemoryMemory state_dict Format
```python
# Source: [VERIFIED: live test execution 2026-04-12]
# state_dict output format:
# {
#   "_compressed_summary": "",
#   "content": [
#     [{"id": "...", "name": "user", "role": "user",
#       "content": "hello", "metadata": {}, "timestamp": "..."}, []]
#   ]
# }
# The outer list is [msg_dict, marks_list] pairs.
```

### Verified: JSONSession File Storage
```python
# Source: [VERIFIED: source code inspection of _json_session.py]
# File path: {save_dir}/{session_id}.json
# File content: {"memory": {"_compressed_summary": "", "content": [...]}}
# The kwarg name "memory" becomes the top-level key in the JSON.
```

### Verified: AgentRequest session_id Flow
```python
# Source: [VERIFIED: runner.py source code + agent_schemas.py]
# AgentRequest has session_id: Optional[str] = None
# Runner.stream_query line 225: request.session_id = request.session_id or str(uuid.uuid4())
# Runner.stream_query line 228: request.user_id = request.user_id or request.session_id
# Response includes: response.session_id = request.session_id (line 234)
# AgentRequest has extra="allow", so agent_config passes through as extra field
```

### Pattern: Integrating Session into chat_query
```python
# Source: [ASSUMED] -- recommended integration pattern
from agentscope.session import JSONSession
from src.agent.session import get_session_backend

@app.query(framework="agentscope")
async def chat_query(self, msgs, request=None, **kwargs):
    # Config resolution (unchanged from Phase 3)
    agent_config = None
    if request and hasattr(request, "agent_config") and request.agent_config:
        agent_config = AgentConfig(**request.agent_config)
    config = resolve_effective_config(agent_config)

    # Session-aware memory (new in Phase 6)
    session_id = getattr(request, "session_id", None) if request else None
    memory = InMemoryMemory()
    session_backend = get_session_backend()

    if session_id:
        await session_backend.load_session_state(
            session_id=session_id, memory=memory,
        )

    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(...),
        memory=memory,
        ...
    )

    async for msg, last in stream_printing_messages(...):
        yield msg, last

    # Save updated memory after streaming completes
    if session_id:
        await session_backend.save_session_state(
            session_id=session_id, memory=agent.memory,
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON file management | JSONSession built-in class | agentscope 1.x | No need to hand-roll file I/O or serialization |
| Custom session_id generation | Runner auto-generates UUID | agentscope-runtime 1.1.3 | Framework handles ID normalization transparently |

**Deprecated/outdated:**
- None identified -- the session API is current and actively maintained.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `agent.memory` remains the same `InMemoryMemory` instance after streaming (not replaced or wrapped) | Architecture Patterns | If agent replaces memory internally, save would capture wrong state. Low risk -- verified InMemoryMemory is passed by reference. |
| A2 | Session save after streaming loop is safe -- the generator has fully completed and all messages are in memory | Common Pitfalls | If generator yields but continues processing, save might be early. Risk is minimal with `stream_printing_messages` which is fully consumed. |
| A3 | `aiofiles` is available as a transitive dependency and does not need explicit installation | Standard Stack | If agentscope drops aiofiles dependency, save would fail. Low risk -- it's used by JSONSession internally. |

**Note:** Most claims are verified by source code inspection and live testing. Only 3 assumptions remain, all LOW risk.

## Open Questions

1. **Session save timing in the SSE lifecycle**
   - What we know: The `async for` loop in `chat_query` yields SSE events. After the loop exits, all messages are in memory.
   - What's unclear: Whether the Runner/framework does anything after the generator returns that might affect the response.
   - Recommendation: Save after the streaming loop in the handler. The response is already being streamed to the client by the Runner's stream adapter, so the save happens server-side without blocking the client.

2. **session_id presence detection**
   - What we know: `Runner.stream_query` always sets `request.session_id` to a non-empty UUID.
   - What's unclear: Whether the handler can distinguish "client sent session_id" from "runner auto-generated it".
   - Recommendation: The runner's auto-generation means the handler always gets a non-empty session_id. Always attempt session save -- this is correct behavior. If the client didn't send one, a new session file is created with the auto-generated ID. This aligns with D-04/D-08.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| agentscope-runtime | Core runtime | Yes | 1.1.3 | -- |
| agentscope.session.JSONSession | Session persistence | Yes | bundled | -- |
| agentscope.memory.InMemoryMemory | Memory serialization | Yes | bundled | -- |
| aiofiles | Async file I/O (JSONSession dependency) | Yes | bundled | -- |
| uv | Package management | Yes | -- | -- |
| pytest | Testing | Yes | 9.0.3 | -- |
| Python | Runtime | Yes | 3.14 | -- |

**Missing dependencies with no fallback:**
- None -- all dependencies are satisfied.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_session.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RES-01 | Chat with session_id persists session state to JSON file | unit | `uv run pytest tests/test_session.py::test_session_persists_to_json -x` | Wave 0 |
| RES-03 | Chat with same session_id resumes with prior context | unit | `uv run pytest tests/test_session.py::test_session_resume_has_prior_context -x` | Wave 0 |
| D-05/D-12 | Chat without session_id is backward compatible (Phase 5 behavior) | unit | `uv run pytest tests/test_session.py::test_no_session_id_backward_compatible -x` | Wave 0 |
| D-08 | Session state is updated after each request | unit | `uv run pytest tests/test_session.py::test_session_updated_after_each_request -x` | Wave 0 |
| D-07 | Resume creates fresh agent with restored memory | unit | `uv run pytest tests/test_session.py::test_resume_creates_fresh_agent -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_session.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_session.py` -- covers RES-01, RES-03, backward compatibility
- [ ] Framework install: none needed -- pytest already installed

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A -- personal R&D, no auth required |
| V3 Session Management | yes (minimal) | session_id via framework UUID generation |
| V4 Access Control | no | N/A -- single-user R&D |
| V5 Input Validation | yes | Pydantic `AgentRequest` validates `session_id` as Optional[str] |
| V6 Cryptography | no | N/A -- no encryption needed for local JSON files |

### Known Threat Patterns for Session Persistence

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via session_id | Tampering | UUID-format session_id (alphanumeric + hyphens only); JSONSession uses `os.path.join` which limits traversal; validate session_id format before use |
| Session file enumeration | Information Disclosure | UUID filenames are unguessable; directory listing restricted by OS permissions |
| Disk exhaustion (many sessions) | Denial of Service | D-10 defers cleanup; acceptable for personal R&D |

## Sources

### Primary (HIGH confidence)
- `agentscope/session/_json_session.py` -- JSONSession implementation, save/load API, file path construction [VERIFIED: source code inspection]
- `agentscope/memory/_working_memory/_in_memory_memory.py` -- InMemoryMemory state_dict/load_state_dict, content serialization format [VERIFIED: source code inspection]
- `agentscope/module/_state_module.py` -- StateModule base class, register_state, state_dict/load_state_dict contract [VERIFIED: source code inspection]
- `agentscope_runtime/engine/schemas/agent_schemas.py` -- AgentRequest.session_id field definition, extra="allow" config [VERIFIED: source code inspection]
- `agentscope_runtime/engine/runner.py` -- Runner.stream_query session_id auto-generation, request/response passing [VERIFIED: source code inspection]
- Live round-trip test -- JSONSession save/load with InMemoryMemory [VERIFIED: executed 2026-04-12]

### Secondary (MEDIUM confidence)
- `src/agent/query.py` -- current chat_query handler structure [VERIFIED: codebase read]
- `tests/conftest.py` -- existing test fixtures and patterns [VERIFIED: codebase read]
- `tests/test_chat_stream.py` -- established mock handler pattern [VERIFIED: codebase read]
- `tests/test_context.py` -- multi-turn test pattern from Phase 5 [VERIFIED: codebase read]

### Tertiary (LOW confidence)
- None -- all findings verified by source code or live testing.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all APIs verified by source code inspection and live round-trip test
- Architecture: HIGH -- integration pattern is straightforward; single handler modification + new session module
- Pitfalls: HIGH -- identified from source code analysis (Runner session_id normalization, state module naming)

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable framework, low churn expected)
