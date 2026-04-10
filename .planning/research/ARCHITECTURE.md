# Architecture Research

**Domain:** AgentScope-based agent testing platform (FastAPI streaming, dynamic agents, pluggable sessions)
**Researched:** 2026-04-10
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                               API Layer                                       │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────────┐   ┌───────────────────────────────┐  │
│  │ FastAPI      │   │ Streaming (SSE)  │   │ Request Validation / Schemas  │  │
│  │ Chat Route   │──▶│ EventSourceResp  │──▶│ Pydantic Models               │  │
│  └──────┬───────┘   └─────────┬────────┘   └───────────────────────────────┘  │
│         │                     │                                              │
├─────────┴─────────────────────┴───────────────────────────────────────────────┤
│                           Orchestration Layer                                  │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐   ┌───────────────────────┐   ┌──────────────────────┐ │
│  │ Session Manager  │   │ Agent Factory/Loader  │   │ Call-Chain Runner    │ │
│  │ (load/save)      │   │ (config-driven)       │   │ (skills/tools/MCP)   │ │
│  └──────┬───────────┘   └──────────┬────────────┘   └──────────┬───────────┘ │
│         │                          │                           │            │
├─────────┴──────────────────────────┴───────────────────────────┴────────────┤
│                           Runtime / Integration Layer                         │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐ │
│  │ AgentScope Runtime │   │ Tool/MCP Gateway     │   │ Observability Hooks   │ │
│  │ (AgentApp/Agent)   │   │ (sandbox, clients)   │   │ (events, traces)      │ │
│  └─────────┬──────────┘   └──────────┬───────────┘   └──────────┬───────────┘ │
├───────────┴─────────────────────────┴───────────────────────────┴────────────┤
│                               Persistence Layer                                │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐ │
│  │ JSON Session Store │   │ Redis Session Store  │   │ Artifact/Logs Store   │ │
│  └────────────────────┘   └──────────────────────┘   └──────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| FastAPI Chat Route | Accepts chat requests, validates inputs, selects streaming | `POST /chat` with `response_class=EventSourceResponse` |
| Streaming (SSE) | Incremental event emission, keep-alives, resume with Last-Event-ID | `EventSourceResponse` + async generator |
| Session Manager | Loads prior session state and persists new events/state | Interface wrapping JSON and Redis backends |
| Agent Factory/Loader | Creates request-scoped agent from config | Adapter to `agentscope-runtime` AgentApp/Agent |
| Call-Chain Runner | Executes LLM + skill/tool/MCP chain with deterministic event logging | Orchestrator service with explicit event log |
| Tool/MCP Gateway | Normalizes tool calls, MCP calls, and sandbox execution | Adapter layer with typed requests/responses |
| Observability Hooks | Emits call-chain events, timings, and errors | Structured logs + event stream buffers |
| JSON Session Store | File-backed session persistence | Local JSON file per session |
| Redis Session Store | Key/TTL-backed session persistence | Redis client (redis-py) with TTL |

## Recommended Project Structure

```
src/
├── api/                    # FastAPI app, routes, request/response schemas
│   ├── chat.py             # /chat endpoint with SSE streaming
│   └── schemas.py          # Pydantic models for request/response/event payloads
├── orchestration/          # Request-scoped lifecycle coordination
│   ├── session_manager.py  # Load/save session state + event log
│   ├── agent_factory.py    # Config-driven agent creation adapter
│   └── call_chain.py       # Deterministic skill/tool/MCP execution
├── runtime/                # AgentScope Runtime integration wrappers
│   ├── agentscope_app.py   # AgentApp bootstrapping, lifespan wiring
│   └── tools_gateway.py    # Tool + MCP adapters, sandbox policy
├── persistence/            # Pluggable session backends
│   ├── base.py             # SessionStore interface
│   ├── json_store.py       # JSON-file implementation
│   └── redis_store.py      # Redis implementation
├── observability/          # Event/trace emission utilities
│   ├── events.py           # Event schema + serialization
│   └── logger.py           # Structured logging hooks
└── config/                 # .env, runtime config loading
    └── settings.py         # Pydantic settings, validation
```

### Structure Rationale

- **api/**: isolates transport concerns (HTTP, SSE, schema validation) from agent logic.
- **orchestration/**: enforces a single request-scoped call chain and explicit event log.
- **runtime/**: keeps `agentscope-runtime` integration replaceable and testable.
- **persistence/**: clean interface enables JSON and Redis without leaking storage details.
- **observability/**: centralizes event emission to validate call-chain stability.

## Architectural Patterns

### Pattern 1: Request-Scoped Agent Factory

**What:** Create a new agent per request using config and session state, then dispose after response completes.
**When to use:** Single-agent chat with strict isolation and repeatability.
**Trade-offs:** Simpler determinism, but per-request creation cost.

**Example:**
```python
# Request-scoped factory to avoid cross-session state leakage.
class AgentFactory:
    def __init__(self, runtime_app):
        self.runtime_app = runtime_app

    async def create(self, config, session_state):
        agent = await self.runtime_app.create_agent(config, session_state)
        return agent
```

### Pattern 2: Append-Only Event Log for Call Chains

**What:** Record every step (LLM turn, tool call, MCP call, context update) as an ordered event stream.
**When to use:** Validating call-chain stability and enabling SSE resume with Last-Event-ID.
**Trade-offs:** More storage, but deterministic replays and debugging.

**Example:**
```python
# Event log drives both SSE streaming and persistence.
async for event in call_chain.run():
    session.append_event(event)
    yield event
```

### Pattern 3: Storage Adapter Interface

**What:** A `SessionStore` interface with JSON and Redis implementations.
**When to use:** Pluggable backends for resume behavior experiments.
**Trade-offs:** Slight abstraction overhead, but easy to swap and test.

## Data Flow

### Request Flow

```
Client POST /chat
    ↓
API validates request + loads session
    ↓
AgentFactory builds agent from config + session
    ↓
Call-Chain Runner executes LLM + skill/tool/MCP
    ↓
Events streamed via SSE
    ↓
Session persisted (JSON or Redis) on each event
```

### Key Data Flows

1. **Streaming chat:** request → call-chain → SSE events → client.
2. **Resume/replay:** client reconnects with `Last-Event-ID` → session manager replays from event log → SSE resumes.
3. **Dynamic agent creation:** config + session state → AgentFactory → AgentScope Runtime.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Single FastAPI service, JSON store for local testing |
| 1k-100k users | Redis store with TTL, structured logs, basic tracing |
| 100k+ users | Dedicated session service, buffered event ingestion, horizontal API scaling |

### Scaling Priorities

1. **First bottleneck:** SSE connection limits/timeouts; add keep-alives and prefer HTTP/2.
2. **Second bottleneck:** session persistence latency; batch writes or async persistence.

## Anti-Patterns

### Anti-Pattern 1: In-Memory Session State

**What people do:** Keep session state only in memory.
**Why it's wrong:** Breaks resume behavior and makes call-chain validation non-deterministic.
**Do this instead:** Persist an append-only event log on each step.

### Anti-Pattern 2: Streaming Without Event IDs

**What people do:** Stream plain tokens without `id` tracking.
**Why it's wrong:** SSE reconnect cannot resume at the right point.
**Do this instead:** Assign monotonic `id` to each event and honor `Last-Event-ID`.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| AgentScope Runtime | Adapter module | Use AgentApp entry point and config-driven agent creation |
| Redis | Session store | TTL per session, JSON serialization |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API ↔ Orchestration | Direct calls | Keep HTTP concerns out of orchestration |
| Orchestration ↔ Persistence | Interface | Enables JSON/Redis swap |
| Orchestration ↔ Runtime | Adapter | Keep AgentScope-specific logic contained |

## Recommended Build Order

1. **Define core contracts:** event schema, `SessionStore` interface, agent config shape.
2. **Build streaming API:** FastAPI `/chat` with SSE + Last-Event-ID handling.
3. **Implement JSON session store:** append-only event log and resume.
4. **Integrate AgentScope Runtime:** request-scoped agent creation and basic call-chain.
5. **Add tool/MCP gateway:** explicit call-chain events + sandbox policy.
6. **Add Redis session store:** TTL configuration and parity with JSON backend.
7. **Observability polish:** structured logs and per-event timings.

## Sources

- https://runtime.agentscope.io/en/intro.html
- https://runtime.agentscope.io/en/agent_app.html
- https://fastapi.tiangolo.com/uk/tutorial/server-sent-events/
- https://www.starlette.io/responses/
- https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- https://redis.io/docs/latest/develop/clients/

---
*Architecture research for: AgentScope-based agent testing platform*
*Researched: 2026-04-10*
