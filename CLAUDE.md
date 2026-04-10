<!-- GSD:project-start source:PROJECT.md -->
## Project

**AgentScope Skill/Tool/MCP Validation Platform**

A FastAPI-based agent testing shell for personal R&D validation, built around `agentscope-runtime` with `uv` project management. The platform creates an agent per client request and supports streaming chat responses so we can quickly test skill calls, tool calls, MCP calls, and context handling behavior. It also explores resume/session recovery with both JSON-file and Redis backends.

**Core Value:** The platform must provide a stable, repeatable call chain where one chat session can reliably trigger and complete skill/tool/MCP interactions.

### Constraints

- **Runtime Dependency**: Core runtime should rely on `agentscope-runtime` — this is the primary framework under evaluation.
- **API Form**: Must expose chat via FastAPI with streaming responses — enables direct conversational testing.
- **State Model**: Prefer near-stateless server design — avoid unnecessary in-memory coupling.
- **Session Backends**: Resume must support both JSON-file and Redis storage — required for comparative validation.
- **Environment**: Model/provider config comes from `.env` — keep config externalized.
- **Tooling**: Use `uv` for project/dependency management — standardize local workflow.
- **Versioning**: Track progress with git commits — preserve development checkpoints.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11 | Primary runtime | Widest ecosystem support for FastAPI + MCP SDKs; stable async support without the edge-case churn of 3.12/3.13 for toolchain compatibility. |
| FastAPI | 0.135.3 | API framework with streaming | Officially supports SSE and streaming JSON lines needed for chat streaming validation; high-performance ASGI with strong typing. |
| Starlette | >=0.46.0 (via FastAPI) | ASGI toolkit underlying FastAPI | Required for proper streaming behavior with `yield` and exception-group handling in streaming responses. |
| Uvicorn | 0.44.0 | ASGI server | Standard ASGI server for FastAPI; stable and lightweight for local R&D loops. |
| agentscope-runtime | 1.1.3 | Agent runtime under test | Primary framework being validated; official docs specify Python 3.10+ and CLI/env config support. |
| Model Context Protocol SDK (Python) | 1.27.0 | MCP client/server | Official MCP SDK for tool/resource/prompt protocols; Tier-1 SDK in official MCP docs. |
| Redis | 7.x | Session persistence backend | Industry standard for resumable sessions; supported by redis-py 7.x. |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.12.5 | Request/response validation | Use for strict typing and schema validation of chat and tool payloads. |
| pydantic-settings | 2.13.1 | `.env` configuration | Use to load provider/model config from `.env` into typed settings. |
| redis | 7.4.0 | Redis client | Use for Redis-backed session resume and state snapshots. |
| orjson | 3.x | Fast JSON serialization | Use when streaming large response payloads or storing session blobs to reduce overhead. |
| sse-starlette | 2.x | SSE utilities | Use if you need explicit SSE event formatting beyond FastAPI’s built-in support. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package manager | Use `uv sync` and `uv run` for reproducible local flows; latest is 0.11.6. |
| ruff | Linting + formatting | Fast checks to keep experimentation code clean; keep config minimal. |
| pytest | Test runner | Use for validating call-chain stability in API flows. |
## Installation
# Core
# Supporting
# Dev dependencies
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI | Starlette-only | Use Starlette-only if you need full control and minimal framework overhead. |
| Uvicorn | Hypercorn | Use Hypercorn if you need HTTP/2 or advanced ASGI features. |
| Redis (redis-py) | Valkey + valkey-py | Use Valkey if you want a fully open-source Redis-compatible backend. |
| MCP SDK (modelcontextprotocol) | modelcontextprotocol-client | Use client-only package if you only need MCP client features and want a smaller dependency. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Flask + Gunicorn | WSGI stack blocks async streaming patterns needed for tool/MCP flows | FastAPI + Uvicorn (ASGI) |
| Pydantic v1 | FastAPI now targets Pydantic v2; v1 adds incompatibilities and migration drag | Pydantic 2.x |
| In-memory session cache only | Breaks resume semantics and cross-request reproducibility | JSON-file backend or Redis |
## Stack Patterns by Variant
- Use JSON-file persistence + local MCP servers
- Because it removes network dependencies while still validating tool/MCP call chains
- Use Redis + periodic snapshotting of agent state
- Because it mimics production-like session persistence and recovery
## Version Compatibility
| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| fastapi@0.135.3 | starlette>=0.46.0 | Required for streaming with `yield` and SSE support. |
| pydantic@2.12.5 | fastapi@0.135.3 | FastAPI release notes set minimum Pydantic v2 bounds in 2026. |
| agentscope-runtime@1.1.3 | python>=3.10 | Official install docs specify Python 3.10+. |
## Sources
- https://fastapi.tiangolo.com/release-notes/ — FastAPI 0.135.3, SSE and streaming updates (MEDIUM)
- https://pypi.org/pypi/uv/json — uv latest version 0.11.6 (MEDIUM)
- https://pypi.org/pypi/pydantic/json — Pydantic 2.12.5 latest stable (MEDIUM)
- https://pypi.org/pypi/uvicorn/json — Uvicorn 0.44.0 latest (MEDIUM)
- https://pypi.org/pypi/redis/json — redis-py 7.4.0 latest (MEDIUM)
- https://runtime.agentscope.io/en/install.html — agentscope-runtime install + Python 3.10+ (MEDIUM)
- https://runtime.agentscope.io/en/cli.html — agentscope-runtime env/CLI config (MEDIUM)
- https://modelcontextprotocol.io/docs/sdk — MCP SDK Tier list (MEDIUM)
- https://pypi.org/pypi/modelcontextprotocol/json — MCP Python SDK 1.27.0 (MEDIUM)
- https://pypi.org/pypi/modelcontextprotocol-client/json — MCP client-only package 0.1.3 (LOW)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
