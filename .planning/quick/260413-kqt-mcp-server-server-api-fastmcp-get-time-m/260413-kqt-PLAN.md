---
phase: quick-260413-kqt
plan: 01
type: execute
wave: 1
depends_on: []
mode: quick
description: Migrate the local MCP server from low-level Server API to FastMCP, preserve the `get_time` tool behavior, fix the positional-argument invocation error, and verify `/process` reaches the MCP tool successfully.
date: 2026-04-13
autonomous: true
files_modified:
  - src/mcp/server.py
  - tests/test_mcp.py
  - scripts/demos/demo_mcp.py
must_haves:
  truths:
    - "`python -m src.mcp.server` launches a stdio MCP server implemented with FastMCP."
    - "The exposed MCP tool is still named `get_time` and the tool function itself remains zero-argument."
    - "A `/process` request can trigger `get_time` without raising `get_time() takes 0 positional arguments but 2 were given`."
  artifacts:
    - "`src/mcp/server.py` exports the FastMCP server object and runnable module entrypoint."
    - "`tests/test_mcp.py` asserts the module shape and zero-argument tool contract."
    - "`scripts/demos/demo_mcp.py` verifies the `/process` -> MCP -> `get_time` happy path with a deterministic response check."
  key_links:
    - "`src/app/lifespan.py` keeps `StdIOStatefulClient(... args=[\"-m\", \"src.mcp.server\"])` unchanged, so the new FastMCP server stays compatible with the existing startup path."
    - "`scripts/demos/demo_mcp.py` exercises the same `/process` endpoint wired by `src/agent/query.py`."
---

# Quick Task 260413-kqt: FastMCP migration for local time server

**Dependency order:** Task 1 -> Task 2 -> Task 3

<objective>
Replace the local MCP server implementation with FastMCP while preserving the existing `get_time` capability and stdio startup path.

Purpose: Remove the low-level handler mismatch that currently causes `get_time() takes 0 positional arguments but 2 were given` during MCP invocation.
Output: A FastMCP-backed `src.mcp.server` module, matching regression coverage, and an end-to-end `/process` verification path that proves the MCP tool is callable again.
</objective>

<context>
@src/mcp/server.py
@src/app/lifespan.py
@src/agent/query.py
@tests/test_mcp.py
@scripts/demos/demo_mcp.py

<interfaces>
From `src/app/lifespan.py`:
```python
mcp_client = StdIOStatefulClient(
    name="example-mcp",
    command="python",
    args=["-m", "src.mcp.server"],
)
```
Keep this invocation compatible. Do not switch transport away from stdio and do not rename the module entrypoint target.

From `src/agent/query.py`:
```python
agent = ReActAgent(..., toolkit=toolkit)
```
The fix must keep the shared toolkit/MCP registration path intact; only the local MCP server implementation changes.

From `scripts/demos/demo_mcp.py`:
```python
"text": "What is the current time? Use the get_time MCP tool."
```
Use this same `/process` path for the final proof, but make the assertion strict enough to distinguish real `get_time` output from a generic model-only answer.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace the low-level MCP server with a FastMCP stdio server</name>
  <files>src/mcp/server.py</files>
  <action>Rewrite `src/mcp/server.py` to use `from mcp.server.fastmcp import FastMCP` instead of the low-level `Server` + `list_tools`/`call_tool` handler pair. Keep the module-level server export name as `server` to minimize downstream churn, but make it a `FastMCP("example-mcp")` instance. Register `get_time` as a FastMCP tool so the framework handles MCP call envelopes, while the Python tool function itself stays zero-argument. Preserve the current user-visible behavior: tool name stays `get_time`, description remains time-focused, and returned text still follows `Current time: {datetime.now().isoformat()}` semantics. Keep the module runnable via `python -m src.mcp.server` using stdio transport only, e.g. `server.run("stdio")`. Do not add HTTP/SSE transport, extra tools, or placeholder compatibility shims.</action>
  <verify><automated>uv run python -c "import src.mcp.server as s; import inspect; assert hasattr(s, 'server'); assert hasattr(s, 'get_time'); assert hasattr(s, 'main'); assert len(inspect.signature(s.get_time).parameters) == 0"</automated></verify>
  <done>`src.mcp.server` is FastMCP-backed, imports cleanly, and exposes a zero-argument `get_time` tool plus a runnable stdio entrypoint.</done>
</task>

<task type="auto">
  <name>Task 2: Align regression coverage with the FastMCP implementation</name>
  <files>tests/test_mcp.py</files>
  <action>Update `tests/test_mcp.py` so it validates the new FastMCP module shape rather than low-level Server API details. Keep the existing lifecycle tests for `StdIOStatefulClient` and `_mcp_clients`, but update the server-module assertions to check the exported `server` object, `main` entrypoint, and zero-argument `get_time` contract. Add one regression-focused assertion that would fail if the module reverted to low-level `call_tool`/`list_tools` handlers instead of FastMCP registration, using `inspect` or direct type checks rather than subprocess integration. Keep the test isolated from real MCP subprocess startup, consistent with `tests/conftest.py` mocking.</action>
  <verify><automated>uv run pytest tests/test_mcp.py -q</automated></verify>
  <done>The MCP regression test suite passes and encodes the FastMCP-backed contract clearly enough to catch a reintroduction of the handler-signature bug.</done>
</task>

<task type="auto">
  <name>Task 3: Prove `/process` can reach `get_time` end-to-end</name>
  <files>scripts/demos/demo_mcp.py</files>
  <action>Tighten `scripts/demos/demo_mcp.py` so it proves the response came from the `get_time` MCP tool path, not a generic LLM answer. Keep the existing `/process` request shape, but change the assertion to require `Current time:` and an ISO-like timestamp fragment in the streamed response text. Do not loosen this to generic words like `time` or `current`. Use the existing service startup path from `scripts/run_service.sh`; no new demo script is needed.</action>
  <verify><automated>bash -lc 'bash scripts/run_service.sh >/tmp/260413-kqt-mcp.log 2>&1 & PID=$!; trap "kill $PID" EXIT; for i in {1..30}; do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 1; done; uv run python scripts/demos/demo_mcp.py'</automated></verify>
  <done>The demo passes against a real local service, and `/process` successfully triggers the local MCP `get_time` tool without the positional-argument error.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_mcp.py -q`
- `bash -lc 'bash scripts/run_service.sh >/tmp/260413-kqt-mcp.log 2>&1 & PID=$!; trap "kill $PID" EXIT; for i in {1..30}; do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 1; done; uv run python scripts/demos/demo_mcp.py'`
</verification>

<success_criteria>
- `src/mcp/server.py` uses FastMCP rather than low-level `Server` handlers.
- The exported MCP tool remains `get_time` with no user-defined parameters.
- `tests/test_mcp.py` passes and guards the FastMCP contract.
- The local service answers a `/process` time request by successfully invoking the MCP tool.
</success_criteria>

<output>
After completion, create `.planning/quick/260413-kqt-mcp-server-server-api-fastmcp-get-time-m/260413-kqt-SUMMARY.md`.
</output>
