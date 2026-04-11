# Phase 2: Streaming Chat Contract - Research

**Researched:** 2026-04-11
**Domain:** agentscope-runtime agent streaming over FastAPI SSE
**Confidence:** HIGH

## Summary

AgentScope Runtime provides a complete Agent-as-a-Service framework built on top of FastAPI. The core class `AgentApp` **directly inherits from FastAPI**, meaning it is not a separate service -- it IS a FastAPI app with additional agent capabilities layered on. The framework handles SSE streaming natively through the `@app.query()` decorator pattern, which registers a `/process` endpoint that accepts agent requests and streams responses using Server-Sent Events.

The streaming protocol is well-defined: a response lifecycle goes through `created` -> `in_progress` -> `completed` states, with incremental text deltas sent as `content` events. For the chat agent, the `ReActAgent` class from the agentscope framework handles model calls, and `stream_printing_messages` bridges the agent's output into an async generator yielding `(msg, last)` pairs.

**Primary recommendation:** Use `AgentApp` as the FastAPI application entry point, replacing the current bare `FastAPI()` instance. Register the chat query handler with `@agent_app.query(framework="agentscope")`. The existing lifespan pattern and settings loading carry forward because `AgentApp` supports standard FastAPI lifespan management.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The Phase 2 chat endpoint accepts a `messages` array as the request body shape, rather than a single `message` string.
- **D-02:** The request contract should stay minimal in this phase; additional runtime/session/config fields belong to later phases unless absolutely required to make streaming work.
- **D-03:** Streaming responses use typed SSE events rather than raw text-only chunks.
- **D-04:** The event lifecycle should be explicit and testable, with distinct event types for stream start, incremental output, and normal completion.
- **D-05:** Validation and request-shape failures should return normal HTTP errors before streaming starts.
- **D-06:** Once a stream has started, runtime failures should be emitted as SSE error events and then terminate the stream cleanly.
- **D-07:** Phase 2 acceptance should combine automated `pytest` coverage with a runnable smoke-test script, following the reproducible workflow style established in Phase 1.
- **D-08:** Repeat-request stability in this phase means the stream lifecycle completes reliably on repeated calls without server-side state drift; exact response text does not need to be identical across runs.

### Claude's Discretion
- Exact endpoint path naming and internal module layout.
- Exact event names and payload field names, as long as they preserve the typed lifecycle above and remain easy to verify.
- Exact smoke-test command shape, as long as it is reproducible via `uv` and aligns with the endpoint contract.

### Deferred Ideas (OUT OF SCOPE)
- Request-scoped agent configuration payloads -- Phase 3.
- Skill/tool/MCP invocation trace events -- Phase 4.
- Multi-turn context continuity semantics -- Phase 5.
- JSON/Redis session persistence and resume behavior -- Phases 6-8.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-01 | User can call a FastAPI chat endpoint and receive streaming responses (SSE) end-to-end | AgentApp inherits FastAPI and provides native SSE streaming via `@app.query()` decorator. The `/process` endpoint accepts `AgentRequest` with `input` messages array and streams structured response events. See Architecture Patterns and Code Examples sections. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| agentscope-runtime | 1.1.3 | Agent runtime framework with built-in FastAPI integration | Directly inherits from FastAPI; provides SSE streaming, health checks, and agent lifecycle management out of the box. [VERIFIED: PyPI 1.1.3, GitHub main shows 1.1.4] |
| agentscope | >=1.0.14 (pinned by runtime) | Agent framework providing agent classes, models, tools | Required dependency of agentscope-runtime; provides `ReActAgent`, model wrappers, `stream_printing_messages`. [VERIFIED: agentscope-runtime pyproject.toml] |
| fastapi | >=0.104.0 (pinned by runtime) | HTTP framework | Already used by AgentApp which inherits from FastAPI; version constraint comes from agentscope-runtime. [VERIFIED: agentscope-runtime pyproject.toml] |
| uvicorn | >=0.24.0 (pinned by runtime) | ASGI server | Already in our stack; version constrained by agentscope-runtime. [VERIFIED: agentscope-runtime pyproject.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | >=2.11.7 (pinned by runtime) | Request/response validation | Used by AgentRequest and AgentResponse schemas from agentscope-runtime. [VERIFIED: agentscope-runtime pyproject.toml] |
| openai | latest (pinned by runtime) | OpenAI-compatible model client | Used under the hood by `OpenAIChatModel` for API calls. [VERIFIED: agentscope-runtime pyproject.toml] |
| httpx | 0.28.1 | Test client for FastAPI | Already in dev dependencies; use for testing streaming SSE endpoints. [VERIFIED: pyproject.toml] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| AgentApp (agentscope-runtime) | Manual FastAPI + custom SSE formatting | AgentApp handles SSE protocol, health checks, streaming serialization automatically; manual approach requires reimplementing all of this |
| agentscope-runtime's SSE format | Custom SSE event types | Runtime's protocol is well-structured (response/message/content lifecycle); custom events would break OpenAI SDK compatibility later |

**Installation:**
```bash
uv add agentscope-runtime==1.1.3
```

Note: `agentscope-runtime` brings substantial transitive dependencies including `fastapi`, `uvicorn`, `pydantic`, `openai`, `redis`, `dashscope`, `kubernetes`, `celery`, `docker`, and others. Since we are already using `fastapi`, `pydantic`, `pydantic-settings`, and `uvicorn`, we should remove the duplicate explicit pins from our `pyproject.toml` and let `agentscope-runtime` manage those versions. [VERIFIED: agentscope-runtime pyproject.toml dependency list]

**Version verification:**
```
agentscope-runtime: 1.1.3 on PyPI (1.1.4 on GitHub main) [VERIFIED: PyPI + GitHub]
sse-starlette: 3.3.0 [VERIFIED: pip index]
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── main.py                    # Entry point: AgentApp instance replaces bare FastAPI
├── app/
│   └── lifespan.py            # Lifespan carries forward; AgentApp supports standard lifespan
├── agent/
│   ├── __init__.py
│   └── query.py               # @app.query() handler: agent creation + streaming logic
├── core/
│   ├── __init__.py
│   └── settings.py            # Existing settings loader (unchanged)
tests/
├── test_settings.py           # Existing (unchanged)
├── test_startup.py            # Existing (unchanged)
├── test_chat_stream.py        # NEW: SSE streaming contract tests
scripts/
├── run_service.sh             # Updated: AgentApp.run() replaces uvicorn command
├── verify_phase2.sh           # NEW: streaming verification script
```

### Pattern 1: AgentApp as FastAPI Entry Point
**What:** Replace bare `FastAPI()` with `AgentApp()`, which inherits from FastAPI.
**When to use:** This is the standard agentscope-runtime pattern.
**Why it matters:** AgentApp adds `/process` (via `@app.query`), `/health`, `/readiness`, `/liveness` endpoints automatically. It also handles SSE serialization, interrupt management, and protocol adapters.

```python
# Source: [CITED: https://runtime.agentscope.io/en/agent_app.html]
from agentscope_runtime.engine import AgentApp
from src.app.lifespan import app_lifespan

app = AgentApp(
    app_name="agentops",
    app_description="AgentScope Skill/Tool/MCP Validation Platform",
    lifespan=app_lifespan,
)
```

**Key insight:** `AgentApp` is a FastAPI subclass. All existing FastAPI patterns (middleware, routes, lifespan, dependency injection) continue to work. The existing `app_lifespan` function can be passed directly.

### Pattern 2: Query Handler with Streaming
**What:** Register a query handler using `@app.query(framework="agentscope")` that creates an agent per request and streams its output.
**When to use:** This is the standard pattern for handling chat requests in agentscope-runtime.

```python
# Source: [CITED: https://runtime.agentscope.io/en/agent_app.html]
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope.memory import InMemoryMemory
from agentscope_runtime.engine.schemas.agent_schemas import AgentRequest

@app.query(framework="agentscope")
async def query_func(
    self,
    msgs,
    request: AgentRequest = None,
    **kwargs,
):
    settings = get_settings()
    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(
            model_name=settings.MODEL_NAME,
            api_key=settings.MODEL_API_KEY,
            client_kwargs={"base_url": settings.MODEL_BASE_URL},
            stream=True,
        ),
        sys_prompt="You are a helpful assistant.",
        memory=InMemoryMemory(),
    )
    agent.set_console_output_enabled(enabled=False)

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last
```

**Key insight:** The handler is an async generator that yields `(msg, last)` tuples. The `@app.query` decorator wraps this into SSE events automatically.

### Pattern 3: OpenAI-Compatible Model Configuration
**What:** Use `OpenAIChatModel` with `client_kwargs` to point at any OpenAI-compatible endpoint.
**When to use:** When `MODEL_PROVIDER` is "openai" or any OpenAI-compatible provider (DeepSeek, vLLM, etc.).

```python
# Source: [CITED: https://doc.agentscope.io/en/tutorial/203-model.html]
# [CITED: https://github.com/agentscope-ai/agentscope/issues/791]
from agentscope.model import OpenAIChatModel

model = OpenAIChatModel(
    model_name="gpt-4o-mini",
    api_key="sk-...",
    client_kwargs={
        "base_url": "https://api.example.com/v1",
    },
    stream=True,
)
```

**Important:** The `base_url` goes inside `client_kwargs`, not as a direct parameter. The `api_key` is a direct parameter. This is different from the `DashScopeChatModel` used in the quickstart examples. [VERIFIED: AgentScope model docs + GitHub issue #791]

### Pattern 4: AgentApp.run() for Service Startup
**What:** Use `AgentApp.run()` instead of manual `uvicorn` command.
**When to use:** This is the recommended startup method for agentscope-runtime services.

```python
# Source: [CITED: https://runtime.agentscope.io/en/agent_app.html]
# In main.py, add at the bottom:
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
```

**Note:** `AgentApp.run()` internally calls `uvicorn.run()`, so the behavior is equivalent to the current `scripts/run_service.sh`. The script can be updated to use `uv run python -m src.main` or keep the uvicorn target since AgentApp is a FastAPI instance.

### Pattern 5: SSE Response Protocol
**What:** The standard SSE event sequence produced by `@app.query()` handlers.
**When to use:** Understanding this is essential for writing test assertions.

```
data: {"sequence_number":0,"object":"response","status":"created", ... }
data: {"sequence_number":1,"object":"response","status":"in_progress", ... }
data: {"sequence_number":2,"object":"message","status":"in_progress", ... }
data: {"sequence_number":3,"object":"content","status":"in_progress","text":"Hello" }
data: {"sequence_number":4,"object":"content","status":"in_progress","text":" World!" }
data: {"sequence_number":5,"object":"message","status":"completed","text":"Hello World!" }
data: {"sequence_number":6,"object":"response","status":"completed", ... }
data: [DONE]
```

**Key insight:** Each SSE event has a `status` field (`created`, `in_progress`, `completed`) and an `object` field (`response`, `message`, `content`). Text deltas appear in `content` events with `status: "in_progress"`. The stream ends with `data: [DONE]`. [CITED: https://runtime.agentscope.io/en/agent_app.html + protocol.md]

### Anti-Patterns to Avoid
- **Creating AgentApp alongside existing FastAPI:** AgentApp IS a FastAPI instance; do not create both and try to mount one on the other. Replace `FastAPI()` with `AgentApp()` in `src/main.py`.
- **Mixing model config approaches:** AgentScope has two patterns: (1) dictionary-based config via `agentscope.init(model_configs=...)` and (2) direct class instantiation like `OpenAIChatModel(...)`. For per-request agent creation (this phase), use direct instantiation. Do not mix both.
- **Passing `base_url` as a direct parameter to OpenAIChatModel:** The `base_url` must go inside `client_kwargs={"base_url": "..."}`. Direct `base_url` parameter does not exist on this class. [VERIFIED: multiple GitHub issues and official docs]
- **Keeping duplicate dependency pins:** Since `agentscope-runtime` pins `fastapi>=0.104.0`, `pydantic>=2.11.7`, `uvicorn>=0.24.0`, our explicit pins on specific versions will conflict. Remove our explicit pins and let agentscope-runtime manage these.
- **Ignoring the `[DONE]` sentinel in SSE parsing:** The stream terminates with `data: [DONE]`. Test code must handle this properly or it will hang.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE event formatting | Custom `text/event-stream` response with manual `data:` formatting | `@app.query()` decorator | AgentApp handles SSE serialization, content-type headers, and the `[DONE]` sentinel automatically |
| Streaming response lifecycle | Custom state machine for start/delta/complete events | AgentApp's built-in response builder | Runtime produces a well-defined event sequence with `response` -> `message` -> `content` lifecycle |
| Health check endpoints | Custom `/health`, `/readiness` routes | AgentApp's built-in endpoints | `/health`, `/readiness`, `/liveness` are auto-registered by AgentApp |
| Agent streaming bridge | Custom async generator wrapping model calls | `stream_printing_messages()` from agentscope.pipeline | Handles the async iteration over agent output and yields `(msg, last)` tuples correctly |
| Request validation | Custom Pydantic models for request/response | `AgentRequest` from `agentscope_runtime.engine.schemas` | Already provides `input`, `session_id`, `user_id`, `stream`, `model` fields with proper types |

**Key insight:** The agentscope-runtime framework is opinionated about the SSE protocol format. Do not fight it -- use the built-in patterns and the protocol will work correctly with OpenAI SDK, AG-UI, and A2A adapters automatically.

## Common Pitfalls

### Pitfall 1: Dependency Version Conflicts
**What goes wrong:** Our `pyproject.toml` pins `fastapi==0.135.3`, `pydantic==2.12.5`, `uvicorn==0.44.0`. The `agentscope-runtime` package requires `fastapi>=0.104.0`, `pydantic>=2.11.7`, `uvicorn>=0.24.0`. If we keep exact pins, `uv` may fail to resolve or silently pick different versions.
**Why it happens:** Both packages declare overlapping dependencies with different constraint styles.
**How to avoid:** Remove our explicit version pins for `fastapi`, `pydantic`, `pydantic-settings`, and `uvicorn`. Let `agentscope-runtime` manage these. Keep our `pydantic-settings` and `uvicorn` in `pyproject.toml` but without exact pins, or simply rely on the transitive dependencies.
**Warning signs:** `uv sync` fails with resolution errors, or runtime import errors after adding `agentscope-runtime`.

### Pitfall 2: Wrong Message Format in AgentRequest
**What goes wrong:** The `input` field in `AgentRequest` expects messages with `content` as a **list of content objects** (e.g., `[{"type": "text", "text": "Hello"}]`), not a plain string.
**Why it happens:** The quickstart curl examples use structured content arrays, and the docs explicitly warn: `"content": "Hello"` is wrong; `"content": [{"type": "text", "text": "Hello"}]` is correct.
**How to avoid:** When constructing test requests, always wrap text content in the typed array format. If the user-facing API accepts a simpler format, add a transformation layer before passing to the agent.
**Warning signs:** The agent receives the message but treats it as an empty or malformed input; the response stream starts but produces no content.

### Pitfall 3: AgentApp Replaces FastAPI Completely
**What goes wrong:** Trying to create both a regular `FastAPI()` app and an `AgentApp()` and wire them together (mounting, including routers).
**Why it happens:** Not realizing that `AgentApp` directly inherits from `FastAPI`.
**How to avoid:** Use `AgentApp` as the single application instance. It IS a FastAPI app, so all existing FastAPI patterns (routes, middleware, lifespan) work unchanged.
**Warning signs:** Duplicate routes, missing middleware, lifespan not executing.

### Pitfall 4: OpenAIChatModel base_url Not Working
**What goes wrong:** Passing `base_url` as a direct argument to `OpenAIChatModel()` instead of inside `client_kwargs`.
**Why it happens:** The class constructor does not have a `base_url` parameter; it uses `client_kwargs` which are forwarded to the underlying `openai.OpenAI()` client.
**How to avoid:** Always use `client_kwargs={"base_url": settings.MODEL_BASE_URL}`.
**Warning signs:** Connection errors to the default OpenAI endpoint, 401 authentication errors.

### Pitfall 5: Heavy Dependency Footprint
**What goes wrong:** `agentscope-runtime` pulls in many dependencies (docker, kubernetes, celery, dashscope, redis, a2a-sdk, ag-ui-protocol, etc.) that are not needed for Phase 2.
**Why it happens:** The package bundles all its capabilities into a single install.
**How to avoid:** Accept the full dependency tree for now. The `[ext]` optional group adds even more (langchain, autogen, etc.) -- do NOT install that. If dependency size becomes a real problem later, investigate whether the needed components can be imported selectively.
**Warning signs:** Slow `uv sync`, large virtual environment, unexpected import errors from optional dependencies.

### Pitfall 6: Missing `set_console_output_enabled(False)`
**What goes wrong:** The agent prints output to stdout in addition to streaming it over SSE, causing noisy logs and potentially interfering with the streaming response.
**Why it happens:** Console output is enabled by default in AgentScope agents.
**How to avoid:** Always call `agent.set_console_output_enabled(enabled=False)` after creating the agent.
**Warning signs:** Text appearing in server logs during streaming; no impact on the SSE stream itself, but confusing during debugging.

## Code Examples

### Example 1: Complete AgentApp Setup (main.py replacement)
```python
# Source: [CITED: https://runtime.agentscope.io/en/agent_app.html]
# This replaces the current src/main.py
from agentscope_runtime.engine import AgentApp
from src.app.lifespan import app_lifespan

app = AgentApp(
    app_name="agentops",
    app_description="AgentScope Skill/Tool/MCP Validation Platform",
    lifespan=app_lifespan,
)

# Lifespan is supported natively since AgentApp inherits from FastAPI.
# The existing app_lifespan function carries forward unchanged.
```

### Example 2: Query Handler Registration
```python
# Source: [CITED: https://runtime.agentscope.io/en/agent_app.html]
# File: src/agent/query.py
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.pipeline import stream_printing_messages
from agentscope.memory import InMemoryMemory

from src.core.settings import get_settings
from src.main import app

@app.query(framework="agentscope")
async def chat_query(self, msgs, request=None, **kwargs):
    settings = get_settings()

    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(
            model_name=settings.MODEL_NAME,
            api_key=settings.MODEL_API_KEY,
            client_kwargs={"base_url": settings.MODEL_BASE_URL},
            stream=True,
        ),
        sys_prompt="You are a helpful assistant.",
        memory=InMemoryMemory(),
    )
    agent.set_console_output_enabled(enabled=False)

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last
```

### Example 3: Testing SSE Streaming
```python
# Source: [CITED: https://raw.githubusercontent.com/agentscope-ai/agentscope-runtime/main/cookbook/en/call.md]
import json
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_process_endpoint_stream():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        payload = {
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello, say hi back in one word."}
                    ],
                }
            ],
        }
        response = await client.post(
            "/process",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Parse SSE events
        events = []
        full_text = ""
        for line in response.text.split("\n"):
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            event = json.loads(data_str)
            events.append(event)

        # Verify lifecycle
        statuses = [e.get("status") for e in events]
        assert "created" in statuses
        assert "completed" in statuses
```

### Example 4: curl Smoke Test
```bash
# Source: [CITED: https://runtime.agentscope.io/en/agent_app.html]
curl -N \
  -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "What is 2+2? Answer in one word."}
        ]
      }
    ]
  }'
```

### Example 5: AgentApp.run() for Service Start
```python
# Source: [CITED: https://runtime.agentscope.io/en/agent_app.html]
# Add to src/main.py at the bottom:
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)

# Or keep the existing uvicorn command since AgentApp is a FastAPI instance:
# uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
# This still works because `app` is a valid ASGI application.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `agentscope.init(model_configs=...)` with dictionary configs | Direct model class instantiation: `OpenAIChatModel(...)`, `DashScopeChatModel(...)` | agentscope >= 1.0 | Per-request agent construction is now cleaner; no global config registry needed |
| `@app.init` / `@app.shutdown` decorators | Standard FastAPI `lifespan` context manager | agentscope-runtime current version | Deprecated approach; lifespan is the recommended pattern |
| Manual SSE formatting with `StreamingResponse` | `@app.query()` decorator auto-converts generators to SSE | agentscope-runtime 1.x | Eliminates boilerplate for SSE streaming |
| Bare `FastAPI()` app | `AgentApp()` (FastAPI subclass) | agentscope-runtime 1.x | Adds health checks, `/process` endpoint, interrupt management, protocol adapters automatically |

**Deprecated/outdated:**
- `@app.init` and `@app.shutdown` decorators: deprecated in favor of `lifespan` pattern [CITED: agent_app.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `OpenAIChatModel` from `agentscope.model` supports `client_kwargs={"base_url": ...}` to configure custom endpoints. Multiple GitHub issues confirm this but the official docs focus on DashScope examples. | Architecture Patterns | If wrong, we cannot connect to non-DashScope providers; would need to use a different model class or find the correct parameter name. |
| A2 | The `@app.query(framework="agentscope")` decorator works with a simple `ReActAgent` without tools, memory, or formatter. The quickstart examples always include tools and formatters but these should be optional for a basic chat. | Architecture Patterns | If wrong, agent initialization fails at runtime; would need to provide minimal tool/formatter stubs. |
| A3 | `stream_printing_messages` from `agentscope.pipeline` is the correct utility for bridging agent output to the SSE generator. This is based on all quickstart examples using this pattern. | Code Examples | If wrong, streaming output format is incorrect; would need to find alternative streaming bridge. |
| A4 | The `input` field in the request body sent to `/process` maps directly to the `msgs` parameter in the query handler. The protocol docs show `AgentRequest.input` as `List[Message]` and the handler signature shows `msgs` as the first positional arg. | Code Examples | If wrong, messages are not passed correctly to the agent; would need transformation logic. |
| A5 | `InMemoryMemory()` is sufficient for Phase 2's single-turn streaming requirement. Session persistence (Redis/JSON) is deferred to later phases. | Architecture Patterns | If wrong, multi-turn state leaks between requests; for Phase 2 single-turn, this should be fine. |

## Open Questions

1. **agentscope-runtime version: 1.1.3 vs 1.1.4?**
   - What we know: PyPI shows 1.1.3 as latest. GitHub main shows 1.1.4 in pyproject.toml.
   - What's unclear: Whether 1.1.4 has been released or is still in development.
   - Recommendation: Pin to `1.1.3` from PyPI. It is the verified stable release.

2. **Can we avoid the heavy dependency footprint?**
   - What we know: `agentscope-runtime` pulls in `docker`, `kubernetes`, `celery`, `dashscope`, `a2a-sdk`, `ag-ui-protocol` and more. None of these are needed for Phase 2.
   - What's unclear: Whether importing only `AgentApp` and the model classes works without importing the full dependency tree.
   - Recommendation: Accept the full dependency tree for now. If import errors surface, handle them. Do NOT install the `[ext]` extras.

3. **Does the existing `app_lifespan` function work with AgentApp?**
   - What we know: AgentApp documentation explicitly states it supports standard FastAPI lifespan management. The docs show `@asynccontextmanager async def lifespan(app: FastAPI)` passed to `AgentApp(lifespan=lifespan)`.
   - What's unclear: Whether the execution order might change -- AgentApp says it "first executes internal framework logic, then your defined lifespan startup logic."
   - Recommendation: The existing `app_lifespan` should work. The settings validation in lifespan will still fire before requests are served.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Runtime | N/A (assumed) | -- | -- |
| uv | Package management | N/A (assumed) | -- | -- |
| agentscope-runtime | Agent framework | Needs install | 1.1.3 | -- |
| OpenAI-compatible LLM endpoint | Model inference | Needs .env config | -- | Tests use mocked responses |

**Missing dependencies with no fallback:**
- `agentscope-runtime` must be added to `pyproject.toml` and installed via `uv sync`.

**Missing dependencies with fallback:**
- LLM endpoint for smoke tests: the actual model API must be configured in `.env`. Unit tests can mock the model layer.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio (from agentscope-runtime dev deps) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_chat_stream.py -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-01 | POST /process with valid messages returns SSE stream with lifecycle events | integration | `uv run pytest tests/test_chat_stream.py::test_process_returns_sse_stream -x` | Wave 0 |
| CORE-01 | SSE stream contains created/in_progress/completed status transitions | integration | `uv run pytest tests/test_chat_stream.py::test_stream_lifecycle_events -x` | Wave 0 |
| CORE-01 | POST /process with invalid input returns HTTP error before streaming | unit | `uv run pytest tests/test_chat_stream.py::test_invalid_input_returns_http_error -x` | Wave 0 |
| CORE-01 | Repeated requests complete stream lifecycle without server state drift | integration | `uv run pytest tests/test_chat_stream.py::test_repeated_requests_stable -x` | Wave 0 |
| CORE-01 | curl smoke test against live service produces SSE events | smoke (manual/script) | `bash scripts/verify_phase2.sh` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_chat_stream.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green + `bash scripts/verify_phase2.sh` passes

### Wave 0 Gaps
- [ ] `tests/test_chat_stream.py` -- covers CORE-01 SSE streaming contract
- [ ] `scripts/verify_phase2.sh` -- reproducible smoke test for streaming endpoint
- [ ] `src/agent/query.py` -- query handler module
- [ ] `src/main.py` update -- replace `FastAPI()` with `AgentApp()`
- [ ] `pyproject.toml` update -- add `agentscope-runtime`, resolve dependency conflicts

## Security Domain

> Security enforcement is not explicitly disabled in config.json. Including this section.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in v1; personal R&D tool |
| V3 Session Management | no | Deferred to Phases 6-8 |
| V4 Access Control | no | No multi-user access in v1 |
| V5 Input Validation | yes | Pydantic models (AgentRequest) validate input structure; FastAPI returns 422 for malformed requests |
| V6 Cryptography | no | No encryption needs this phase |

### Known Threat Patterns for Agent/FastAPI Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious prompt injection | Tampering | Agent system prompt sets boundaries; not a security boundary for R&D tool |
| Unbounded request size | Denial of Service | FastAPI default body size limits; may need explicit limit for production |
| SSE connection starvation | Denial of Service | Uvicorn worker timeout settings; not critical for personal R&D |

## Sources

### Primary (HIGH confidence)
- [agentscope-runtime pyproject.toml on GitHub](https://github.com/agentscope-ai/agentscope-runtime/blob/main/pyproject.toml) - dependency list, version pins
- [AgentApp documentation](https://runtime.agentscope.io/en/agent_app.html) - complete API reference for AgentApp, query decorator, SSE streaming, lifespan, health checks
- [Protocol specification](https://raw.githubusercontent.com/agentscope-ai/agentscope-runtime/main/cookbook/en/protocol.md) - SSE event format, message models, request/response schemas
- [Call documentation](https://raw.githubusercontent.com/agentscope-ai/agentscope-runtime/main/cookbook/en/call.md) - client invocation examples, SSE parsing code
- [AgentScope model documentation](https://doc.agentscope.io/en/tutorial/203-model.html) - model wrapper configuration, OpenAIChatModel parameters

### Secondary (MEDIUM confidence)
- [GitHub Issue #791](https://github.com/agentscope-ai/agentscope/issues/791) - OpenAIChatModel with DeepSeek (OpenAI-compatible) usage pattern
- [PyPI agentscope-runtime](https://pypi.org/project/agentscope-runtime/) - version 1.1.3 confirmed

### Tertiary (LOW confidence)
- `client_kwargs={"base_url": ...}` pattern - based on GitHub issues and community posts; not explicitly shown in official quickstart (which uses DashScope). Flagged in assumptions as A1.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all verified against agentscope-runtime pyproject.toml and official docs
- Architecture: HIGH - AgentApp documentation is comprehensive with complete examples
- Pitfalls: MEDIUM - based on documentation and community issues; some may only surface during implementation
- Model configuration: MEDIUM - OpenAIChatModel usage inferred from docs + issues, not from a working example

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable - agentscope-runtime 1.1.3 is a released package)
