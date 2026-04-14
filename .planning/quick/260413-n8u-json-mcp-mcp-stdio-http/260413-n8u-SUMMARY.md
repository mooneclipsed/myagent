# Quick Task 260413-n8u Summary

## Completed

Implemented session-scoped dynamic MCP bootstrap with a single active runtime per pod.

### What changed
- Added bootstrap/shutdown request and response models for dynamic MCP configuration in `src/core/config.py`.
- Refactored `src/tools/__init__.py` to expose `create_base_toolkit()` plus reusable default tool/skill registration helpers.
- Added `src/agent/session_runtime.py` to own the single active session runtime, MCP client factory, bootstrap rollback, and teardown.
- Added `src/app/session_routes.py` with `POST /sessions/bootstrap` and `POST /sessions/{session_id}/shutdown`.
- Updated `src/agent/query.py` to reuse a bootstrapped session runtime when `session_id` matches an active session, while keeping the legacy `/process` path intact.
- Updated `src/app/lifespan.py` to close session runtimes before legacy startup MCP clients.
- Registered the new routes from `src/main.py`.
- Added bootstrap-focused tests in `tests/test_session_bootstrap.py` and updated shared fixtures in `tests/conftest.py`.
- Added live demo `scripts/demos/demo_bootstrap_mcp.py` and made demo base URL / service port configurable.

## Validation
- `uv run pytest tests/test_session.py tests/test_mcp.py tests/test_session_bootstrap.py -q`
- `SERVICE_URL=http://127.0.0.1:8010 uv run python scripts/demos/demo_bootstrap_mcp.py` against a live `uvicorn` instance on port `8010`

## Notes
- HTTP MCP bootstrap currently supports `HttpStatefulClient` only, with `transport` limited to `sse` or `streamable_http`.
- Bootstrap is fail-fast and all-or-nothing: if any MCP init/register step fails, the runtime is not published.
- The existing legacy startup MCP path remains available for non-bootstrapped callers.
