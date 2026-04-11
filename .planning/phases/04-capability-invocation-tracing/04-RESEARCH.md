# Phase 4: Capability Invocation Tracing - Research

**Researched:** 2026-04-11
**Domain:** agentscope-runtime tool/MCP registration and invocation
**Confidence:** HIGH

## Summary

Phase 4 makes the ReActAgent "capable" by registering tool functions and MCP server tools so they can be invoked through the existing streaming chat endpoint. The core framework (`agentscope` v1.0.18, `agentscope-runtime` v1.1.3) provides all necessary primitives: `Toolkit` for tool management, `ToolResponse` for tool return values, and `StdIOStatefulClient` for MCP server connections. The existing `query.py` handler creates a `ReActAgent` without a toolkit (defaults to empty). Phase 4 must build a `Toolkit` with registered tools, optionally register MCP clients, and pass it to the `ReActAgent` constructor.

The framework handles the ReAct reasoning loop automatically: when the LLM decides to call a tool, the agent's `_acting()` method invokes `toolkit.call_tool_function()`, feeds the result back to the model, and continues reasoning until a final response is generated. All of this streams through the existing `stream_printing_messages` pipeline without changes to the SSE lifecycle.

Structured tracing (CAP-05, "observe structured events" portions of CAP-01/02/03) is deferred per CONTEXT.md decisions D-06 and D-07. The success criterion for Phase 4 is: user can trigger tool and MCP calls through chat and confirm the calls execute, visible in agent responses.

**Primary recommendation:** Build a shared `Toolkit` at service startup with example tools registered via `toolkit.register_tool_function()`. For MCP, connect a `StdIOStatefulClient` to a local example MCP server in the lifespan hook and register it into the toolkit. Pass the populated toolkit to each new `ReActAgent` in `query.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use agentscope-runtime's framework-native tool registration mechanism (e.g., `@app.tool` or `agent.tool()`) to register tools with the ReActAgent. Do not build a custom registration layer.
- **D-02:** Register tools at service startup time. All requests share the same set of registered tools. Do not implement per-request dynamic tool registration in this phase.
- **D-03:** Include concrete example tools (e.g., `get_weather`, `calculate`) for end-to-end verification. These tools must be simple, deterministic, and callable through the streaming chat flow without external dependencies.
- **D-04:** Use agentscope-runtime's built-in MCP support for MCP server/tool registration. Do not add a separate MCP SDK dependency.
- **D-05:** Include a local example MCP server for end-to-end verification. The server should be simple (e.g., file read, time query), have no network dependencies, and be startable alongside the main service.
- **D-06:** Structured call-chain tracing (CAP-05: run correlation ID, ordered step inspection, structured invocation/result/error events) is deferred to a future phase. The future implementation will use OpenTelemetry or a similar observability SDK rather than a custom tracing solution.
- **D-07:** Phase 4 success criteria is revised: the user must be able to trigger tool and MCP calls through chat and confirm the calls execute (visible in agent responses). The "observe structured trace events" requirement is not in scope.

### Claude's Discretion
- Exact example tool implementations, as long as they cover at least one tool call and one MCP call end-to-end.
- Exact MCP server implementation and protocol details.
- Internal module layout for tool/MCP registration code.
- How tools are declared in the agentscope-runtime framework (decorator vs config vs programmatic API).
- Verification approach, following established Phase 1/2/3 patterns (pytest + smoke script).

### Deferred Ideas (OUT OF SCOPE)
- Structured call-chain trace events (CAP-05: run correlation ID, ordered step inspection) -- deferred to future phase with OpenTelemetry integration.
- Observing structured invocation/result/error events for tool/skill/MCP calls (the "observe" portions of CAP-01, CAP-02, CAP-03) -- deferred alongside tracing.
- Per-request dynamic tool registration -- startup-time fixed registration is sufficient for R&D validation.
- Configurable tool set per request -- deferred until tool registration is proven stable.
- Skill invocation (CAP-01 mentions "skill") -- agentscope-runtime distinguishes skills from tools; skills are directory-based instruction sets registered via `toolkit.register_agent_skill(skill_dir)` that modify the system prompt. Skill invocation is deferred.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAP-01 | User can run a chat that triggers skill invocation and observe structured invocation/result events | Invocation side: agent triggers tool calls through ReAct loop. Structured observation: DEFERRED per D-06. Skill distinction: agentscope skills are directory-based prompt modifiers, not callable functions -- deferred. |
| CAP-02 | User can run a chat that triggers tool invocation and observe structured invocation/result/error events | Invocation side: `toolkit.register_tool_function()` registers Python functions; ReActAgent calls them via `_acting()`. Structured observation: DEFERRED per D-06. Example tools: `get_weather`, `calculate` per D-03. |
| CAP-03 | User can run a chat that triggers MCP invocation and observe structured request/response events | Invocation side: `StdIOStatefulClient` + `toolkit.register_mcp_client()` registers MCP tools. Structured observation: DEFERRED per D-06. Local MCP server per D-05. |
| CAP-05 | User can inspect call-chain trace data for one run with ordered steps and run correlation ID | ENTIRELY DEFERRED per D-06. Future phase with OpenTelemetry integration. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| agentscope | 1.0.18 | Agent framework (ReActAgent, Toolkit, MCP clients) | Installed dependency; provides all tool/MCP primitives [VERIFIED: uv pip show] |
| agentscope-runtime | 1.1.3 | FastAPI integration (AgentApp, query handler, SSE) | Installed dependency; wraps agentscope for web serving [VERIFIED: uv pip show] |
| mcp | 1.27.0 | MCP protocol SDK (transitive dependency of agentscope) | Already installed via agentscope; provides StdioServerParameters for MCP server subprocess [VERIFIED: uv pip show] |
| fastapi | (via agentscope-runtime) | HTTP framework | Already in dependency tree [VERIFIED: pyproject.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.3 | Test runner | All test verification [VERIFIED: pyproject.toml] |
| httpx | 0.28.1 | Test HTTP client | TestClient and smoke tests [VERIFIED: pyproject.toml] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Toolkit.register_tool_function | Custom tool registry | Custom registry would bypass framework's auto-schema generation, ReAct loop integration, and middleware support. No valid reason to use custom. |
| StdIOStatefulClient | HttpStatefulClient / HttpStatelessClient | StdIO is best for local example MCP server (no network). HTTP clients useful for remote MCP servers in future. |

**Installation:**
No new packages required. All dependencies are already installed via `agentscope-runtime==1.1.3`.

**Version verification:**
```
agentscope-runtime==1.1.3 (installed)
agentscope==1.0.18 (transitive, via agentscope-runtime)
mcp==1.27.0 (transitive, via agentscope)
pytest==9.0.3 (dev dependency)
httpx==0.28.1 (dev dependency)
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── agent/
│   ├── __init__.py
│   └── query.py          # EXISTING - extend with toolkit parameter
├── app/
│   ├── __init__.py
│   └── lifespan.py       # EXISTING - extend with MCP client lifecycle
├── core/
│   ├── __init__.py
│   ├── config.py          # EXISTING - unchanged
│   └── settings.py        # EXISTING - unchanged
├── tools/                 # NEW - example tool functions
│   ├── __init__.py
│   └── examples.py        # get_weather, calculate functions
├── mcp/                   # NEW - example MCP server + registration
│   ├── __init__.py
│   └── server.py          # local MCP server implementation
├── main.py                # EXISTING - may store toolkit reference
└── __init__.py
```

### Pattern 1: Toolkit Registration at Startup
**What:** Create a shared `Toolkit` instance, register tool functions and MCP clients into it at service startup, then pass it to each per-request agent.
**When to use:** This is the primary pattern for Phase 4 per D-02 (startup-time registration).
**Example:**
```python
# Source: agentscope/tool/_toolkit.py (installed framework source)
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

# Create shared toolkit
toolkit = Toolkit()

# Register a tool function - schemas auto-generated from docstring + type hints
def get_weather(city: str) -> ToolResponse:
    """Get the current weather for a city.

    Args:
        city (str): The name of the city to get weather for.

    Returns:
        ToolResponse: The weather information for the specified city.
    """
    # Deterministic mock for testing
    return ToolResponse(
        content=[TextBlock(type="text", text=f"The weather in {city} is sunny, 22C.")],
    )

toolkit.register_tool_function(
    tool_func=get_weather,
    group_name="basic",  # "basic" group is always active
)
```

### Pattern 2: MCP Client Lifecycle in Lifespan
**What:** Connect to MCP servers in FastAPI lifespan startup, register tools into the shared toolkit, and close connections on shutdown.
**When to use:** When MCP servers need to be available for the full service lifetime per D-05.
**Example:**
```python
# Source: agentscope/mcp/_stdio_stateful_client.py, _stateful_client_base.py
from contextlib import asynccontextmanager
from agentscope.mcp import StdIOStatefulClient

# Shared toolkit and MCP client references (module-level or app state)
toolkit = Toolkit()
_mcp_clients: list[StdIOStatefulClient] = []

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Startup: settings validation (existing)
    get_settings()

    # Startup: connect MCP server
    mcp_client = StdIOStatefulClient(
        name="example-mcp",
        command="python",
        args=["-m", "src.mcp.server"],
    )
    await mcp_client.connect()
    await toolkit.register_mcp_client(mcp_client)
    _mcp_clients.append(mcp_client)

    yield

    # Shutdown: close MCP clients in LIFO order
    for client in reversed(_mcp_clients):
        await client.close()
```

### Pattern 3: Pass Toolkit to ReActAgent
**What:** Pass the shared toolkit to each new ReActAgent instance in the query handler.
**When to use:** Every request in Phase 4.
**Example:**
```python
# Source: agentscope/agent/_react_agent.py constructor
# Modified src/agent/query.py
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
    toolkit=toolkit,  # NEW: pass the shared toolkit
)
```

### Pattern 4: Local MCP Server Implementation
**What:** A simple Python script that starts an MCP server using the `mcp` SDK with one or two tools.
**When to use:** For the local example MCP server per D-05.
**Example:**
```python
# Source: mcp SDK (installed as transitive dependency)
# src/mcp/server.py - example MCP server
import mcp.server.stdio
from mcp.server import Server

server = Server("example-mcp")

@server.call_tool()
async def get_time() -> list[dict]:
    """Get the current date and time."""
    from datetime import datetime
    return [{"type": "text", "text": f"Current time: {datetime.now().isoformat()}"}]

@server.list_tools()
async def list_tools() -> list[dict]:
    return [{
        "name": "get_time",
        "description": "Get the current date and time.",
        "inputSchema": {"type": "object", "properties": {}},
    }]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Anti-Patterns to Avoid
- **Creating a new Toolkit per request:** Wasteful and breaks D-02 (startup-time registration). The toolkit is designed to be shared.
- **Custom tool dispatch logic:** The ReActAgent handles the full reasoning-acting loop. Do not intercept tool calls outside the framework.
- **Registering MCP clients per request:** Connection overhead is significant. Register once at startup in the lifespan hook.
- **Ignoring LIFO close order for MCP clients:** The framework explicitly warns that multiple StdIOStatefulClient instances must be closed in last-in-first-out order to avoid errors. [VERIFIED: agentscope/mcp/_stdio_stateful_client.py docstring]
- **Using raw dict return from tool functions:** Tool functions MUST return `ToolResponse` objects. The framework does not auto-wrap plain strings or dicts. [VERIFIED: agentscope/tool/_toolkit.py register_tool_function docstring]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tool JSON schema generation | Manual JSON schema dicts | `toolkit.register_tool_function()` with docstrings | Framework auto-generates schemas from Python docstrings and type hints via `_parse_tool_function()` [VERIFIED: agentscope/tool/_toolkit.py] |
| Tool dispatch in ReAct loop | Custom tool call routing | ReActAgent's built-in `_acting()` method | Agent handles tool_use block parsing, invocation, and result formatting automatically [VERIFIED: agentscope/agent/_react_agent.py] |
| MCP protocol handling | Custom MCP client code | `StdIOStatefulClient` + `toolkit.register_mcp_client()` | Framework manages connection lifecycle, tool discovery, and schema registration [VERIFIED: agentscope/mcp/_stdio_stateful_client.py] |
| SSE streaming for tool results | Custom SSE event injection | Existing `stream_printing_messages` pipeline | Tool call results stream through the same pipeline as regular chat messages [VERIFIED: src/agent/query.py existing pattern] |
| Tool result formatting | Custom result objects | `ToolResponse` with `TextBlock` | Framework requires `ToolResponse` return type; `TextBlock` is the standard content unit [VERIFIED: agentscope/tool/_response.py] |

**Key insight:** The agentscope framework provides a complete tool lifecycle: registration, schema generation, dispatch, execution, and result streaming. The only code Phase 4 needs to write is (1) tool function implementations returning `ToolResponse`, (2) a simple MCP server script, and (3) wiring code to register everything and pass the toolkit to the agent.

## Runtime State Inventory

> Phase 4 is a greenfield feature addition (adding tool/MCP capabilities to existing agent). No rename/refactor/migration is involved.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None -- no databases or persistent stores in Phase 4 scope | None |
| Live service config | None -- tool registration is code-level, not UI/database config | None |
| OS-registered state | None -- no OS-level registrations | None |
| Secrets/env vars | None -- no new secrets; existing MODEL_API_KEY etc. unchanged | None |
| Build artifacts | None -- pure Python, no compiled artifacts | None |

## Common Pitfalls

### Pitfall 1: Tool Function Not Returning ToolResponse
**What goes wrong:** Tool function returns a plain string or dict instead of `ToolResponse(content=[TextBlock(...)])`.
**Why it happens:** The framework's auto-schema generation from docstrings makes it look like any function works, but the return type must be `ToolResponse`.
**How to avoid:** Always return `ToolResponse(content=[TextBlock(type="text", text=...)])`.
**Warning signs:** `TypeError` or `AttributeError` during tool invocation in the ReAct loop.

### Pitfall 2: MCP Client Not Connected Before Registration
**What goes wrong:** Calling `toolkit.register_mcp_client(client)` before `await client.connect()`.
**Why it happens:** The registration method is on `Toolkit`, not on the client, so the connection step is easy to forget.
**How to avoid:** Always follow the sequence: create client -> `await client.connect()` -> `await toolkit.register_mcp_client(client)`.
**Warning signs:** `RuntimeError: The MCP server is not connected` [VERIFIED: agentscope/mcp/_stateful_client_base.py].

### Pitfall 3: LIFO Close Order for MCP Clients
**What goes wrong:** Closing MCP clients in wrong order when multiple are registered.
**Why it happens:** The underlying MCP SDK has a known issue with session management when multiple stdio clients are open simultaneously.
**How to avoid:** Always close in reverse order of registration. Store clients in a list and iterate `reversed()` on shutdown.
**Warning signs:** `Stdio` pipe errors or hangs during shutdown [VERIFIED: agentscope/mcp/_stdio_stateful_client.py docstring, github.com/modelcontextprotocol/python-sdk/issues/577].

### Pitfall 4: Docstring Format Mismatch
**What goes wrong:** Tool function docstring doesn't follow the expected format, resulting in missing or wrong parameter descriptions in the JSON schema.
**Why it happens:** The framework uses `_parse_tool_function()` which expects Google-style docstrings with `Args:` section.
**How to avoid:** Use standard Google-style docstrings with `Args:` and `Returns:` sections. Include type annotations in the docstring.
**Warning signs:** LLM doesn't know how to use the tool (missing descriptions in schema).

### Pitfall 5: Toolkit Not Thread-Safe for Concurrent Requests
**What goes wrong:** Multiple concurrent requests modifying the toolkit state simultaneously.
**Why it happens:** D-02 says all requests share the same toolkit. While tool calls are read-only (dispatching to registered functions), concurrent modification would be unsafe.
**How to avoid:** Only register tools at startup (in lifespan). Never modify the toolkit during request handling. The toolkit's `call_tool_function` is safe for concurrent reads.
**Warning signs:** Intermittent tool not found errors under load.

### Pitfall 6: MCP Server Subprocess Path Issues
**What goes wrong:** `StdIOStatefulClient(command="python", args=["-m", "src.mcp.server"])` fails because the module path is not resolvable.
**Why it happens:** The MCP server runs as a subprocess and needs the correct Python path and module resolution.
**How to avoid:** Test the MCP server standalone first (`python -m src.mcp.server`). Consider using `sys.executable` for the command to match the venv Python. Alternatively, use an absolute path to the server script.
**Warning signs:** `StdIOStatefulClient.connect()` raises `RuntimeError` or times out.

## Code Examples

### Complete Tool Function Pattern
```python
# Source: agentscope/tool/_toolkit.py, _response.py (VERIFIED: installed framework)
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

def calculate(operation: str, a: float, b: float) -> ToolResponse:
    """Perform a basic arithmetic calculation.

    Args:
        operation (str): The operation to perform. One of: add, subtract, multiply, divide.
        a (float): The first operand.
        b (float): The second operand.

    Returns:
        ToolResponse: The result of the calculation.
    """
    ops = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else "Error: division by zero",
    }
    if operation not in ops:
        result = f"Error: unknown operation '{operation}'"
    else:
        result = f"{ops[operation](a, b)}"
    return ToolResponse(
        content=[TextBlock(type="text", text=result)],
    )
```

### Complete MCP Client Registration Pattern
```python
# Source: agentscope/mcp/_stdio_stateful_client.py, agentscope/tool/_toolkit.py
from agentscope.mcp import StdIOStatefulClient
from agentscope.tool import Toolkit

# Step 1: Create client
mcp_client = StdIOStatefulClient(
    name="example-server",
    command="python",
    args=["-m", "src.mcp.server"],
)

# Step 2: Connect (async)
await mcp_client.connect()

# Step 3: Register into toolkit (async)
await toolkit.register_mcp_client(
    mcp_client,
    group_name="basic",       # tools always included in schema
    namesake_strategy="raise", # fail if tool name conflicts
)

# Step 4: On shutdown, close (LIFO order if multiple clients)
await mcp_client.close(ignore_errors=True)
```

### Updated Query Handler Pattern
```python
# Source: src/agent/query.py (existing), extended for Phase 4
from src.tools import toolkit  # shared toolkit built at startup

@app.query(framework="agentscope")
async def chat_query(self, msgs, request=None, **kwargs):
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
        toolkit=toolkit,  # NEW: shared toolkit with registered tools + MCP
    )
    agent.set_console_output_enabled(enabled=False)

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom tool registration decorators | `toolkit.register_tool_function()` with auto-schema | agentscope v1.0+ | No manual JSON schema needed |
| Separate MCP SDK integration | Built-in `toolkit.register_mcp_client()` | agentscope v1.0+ | MCP tools registered like native tools |
| Synchronous tool execution | Async generator streaming interface | agentscope v1.0+ | Tools can stream results progressively |
| Per-agent tool definition | Shared `Toolkit` passed by reference | agentscope v1.0+ | One toolkit serves all agents efficiently |

**Deprecated/outdated:**
- Manual JSON schema construction for tool functions: replaced by auto-generation from docstrings and type hints via `_parse_tool_function()` [VERIFIED: agentscope/tool/_toolkit.py]
- Custom MCP client wrappers: replaced by built-in `StdIOStatefulClient` and `HttpStatefulClient` [VERIFIED: agentscope/mcp/ module]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The MCP server can be started via `python -m src.mcp.server` from the project root | Pattern 4 | Server subprocess fails; need to adjust command/args |
| A2 | The `mcp` SDK's `mcp.server.stdio` module is the correct way to build a simple MCP server | Pattern 4 | May need different MCP server API; check mcp SDK docs |
| A3 | Sharing a single `Toolkit` instance across concurrent requests is safe as long as no modifications happen during request handling | Pitfall 5 | Race conditions under concurrent load |
| A4 | The LLM (via ReActAgent) will automatically know about registered tools and decide to call them based on user messages | Architecture | LLM may not call tools if sys_prompt or model doesn't support tool calling |
| A5 | `stream_printing_messages` correctly streams tool call results through the SSE pipeline without modification | Architecture | May need to verify tool result blocks appear in SSE events |

## Open Questions

1. **MCP server `mcp` SDK server-side API**
   - What we know: The `mcp` package (v1.27.0) is installed as a transitive dependency. The `mcp.server.stdio` module should provide the server-side API.
   - What's unclear: Exact server-side API shape (decorator vs class vs function). The framework's MCP client side is well understood, but the server implementation pattern needs verification.
   - Recommendation: Write the example MCP server early (Plan 01) and test it standalone before integrating with the client.

2. **LLM tool-calling compatibility**
   - What we know: ReActAgent uses the model's tool calling capability. The model must support function/tool calling in its API.
   - What's unclear: Whether the test model endpoint (mocked or real) supports tool calling. If using a mock, the mock must return tool_use blocks.
   - Recommendation: For integration testing, mock the LLM to return tool_use blocks in its response. For end-to-end testing, use a real model that supports tool calling (e.g., OpenAI GPT-4).

3. **Toolkit storage location**
   - What we know: The toolkit needs to be accessible in both `lifespan.py` (for MCP registration) and `query.py` (for passing to agents).
   - What's unclear: Best pattern for sharing state between lifespan and query handler in agentscope-runtime.
   - Recommendation: Use a module-level singleton in a new `src/tools/__init__.py` that both lifespan and query import.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | Build/run commands | Yes | 0.11.0 | -- |
| Python (project) | Runtime | Yes (via uv) | 3.14.3 | -- |
| agentscope-runtime | Framework | Yes | 1.1.3 | -- |
| agentscope | Agent primitives | Yes | 1.0.18 | -- |
| mcp | MCP protocol | Yes | 1.27.0 | -- |
| pytest | Testing | Yes | 9.0.3 | -- |
| httpx | HTTP test client | Yes | 0.28.1 | -- |

**Missing dependencies with no fallback:**
None -- all required dependencies are installed.

**Missing dependencies with fallback:**
None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_tools.py -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAP-02 | Tool function registered and callable through agent | unit | `uv run pytest tests/test_tools.py::test_tool_registration -x` | Wave 0 |
| CAP-02 | Tool returns correct ToolResponse format | unit | `uv run pytest tests/test_tools.py::test_tool_response_format -x` | Wave 0 |
| CAP-02 | Agent invokes tool through streaming chat | integration | `uv run pytest tests/test_tools.py::test_tool_call_in_chat -x` | Wave 0 |
| CAP-03 | MCP client connects and registers tools | integration | `uv run pytest tests/test_mcp.py::test_mcp_client_connection -x` | Wave 0 |
| CAP-03 | MCP tool callable through agent | integration | `uv run pytest tests/test_mcp.py::test_mcp_tool_in_chat -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_tools.py tests/test_mcp.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green + smoke script passes

### Wave 0 Gaps
- [ ] `tests/test_tools.py` -- covers CAP-02 tool registration, invocation, response format
- [ ] `tests/test_mcp.py` -- covers CAP-03 MCP client lifecycle and tool invocation
- [ ] `scripts/smoke_04.sh` -- Phase 4 smoke verification script following Phase 1/2/3 pattern

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in v1 R&D platform |
| V3 Session Management | no | No session state in Phase 4 |
| V4 Access Control | no | Single-user R&D platform |
| V5 Input Validation | yes | Pydantic models for request payloads; tool function parameter type hints validated by framework |
| V6 Cryptography | no | No crypto operations in Phase 4 |

### Known Threat Patterns for agentscope Tool/MCP Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tool injection via user prompt | Tampering, Elevation | ReActAgent controls which tools are available; LLM can only call registered tools. No arbitrary code execution from user input. |
| MCP server subprocess command injection | Tampering | MCP server command is hardcoded in lifespan, not user-configurable. StdIO transport only (no network exposure). |
| Tool function argument manipulation | Tampering | Framework validates arguments against auto-generated JSON schema before passing to tool function. |

## Sources

### Primary (HIGH confidence)
- agentscope/tool/_toolkit.py -- Toolkit.register_tool_function(), register_mcp_client() signatures and implementation [VERIFIED: installed framework source]
- agentscope/agent/_react_agent.py -- ReActAgent constructor (toolkit parameter), _acting() method for tool dispatch [VERIFIED: installed framework source]
- agentscope/tool/_response.py -- ToolResponse dataclass definition [VERIFIED: installed framework source]
- agentscope/mcp/_stdio_stateful_client.py -- StdIOStatefulClient constructor and lifecycle [VERIFIED: installed framework source]
- agentscope/mcp/_stateful_client_base.py -- StatefulClientBase connect/close lifecycle [VERIFIED: installed framework source]

### Secondary (MEDIUM confidence)
- mcp SDK (v1.27.0) installed package -- provides mcp.server.stdio for building example MCP server [VERIFIED: installed transitive dependency]
- src/agent/query.py -- existing streaming query handler pattern to extend [VERIFIED: project source]
- src/app/lifespan.py -- existing lifespan pattern to extend [VERIFIED: project source]
- tests/conftest.py -- existing test fixtures to extend [VERIFIED: project source]

### Tertiary (LOW confidence)
- MCP server-side API usage pattern (mcp.server.stdio, Server class) [ASSUMED: based on mcp SDK package structure -- needs standalone verification during implementation]

## Project Constraints (from CLAUDE.md)

- Runtime Dependency: Core runtime must rely on `agentscope-runtime` -- no alternative frameworks.
- API Form: Must expose chat via FastAPI with streaming responses.
- State Model: Prefer near-stateless server design. Toolkit is shared read-only state, acceptable under D-02.
- Environment: Model/provider config from `.env` -- no code changes for config.
- Tooling: Use `uv` for project/dependency management.
- Versioning: Track progress with git commits.
- Communication: Use Chinese for dialogue, English for documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages verified installed, API signatures read from source
- Architecture: HIGH -- patterns derived from reading framework source code directly
- Pitfalls: HIGH -- based on framework docstrings and known MCP SDK issues
- MCP server pattern: MEDIUM -- mcp SDK server-side API assumed from package structure, needs verification

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable framework, no fast-moving dependencies)
