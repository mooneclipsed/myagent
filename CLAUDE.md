# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Repository Commands

- Python: `3.11+`
- Package manager: `uv`
- Install dependencies: `uv sync`
- Start the app: `bash scripts/run_service.sh`
- Alternate start: `uv run uvicorn src.main:app --host 127.0.0.1 --port 8000`
- Run all tests: `uv run pytest tests/ -x -v`
- Run one file: `uv run pytest tests/test_session_bootstrap.py -x -v`
- Run one case pattern: `uv run pytest tests/test_session_bootstrap.py -k bootstrap_same_session -x -v`
- Run demos after the service is up:
  - `uv run scripts/demos/demo_tool.py`
  - `uv run scripts/demos/demo_skill.py`
  - `uv run scripts/demos/demo_mcp.py`
  - `uv run scripts/demos/demo_resume.py`

## Repository Architecture

- `src/main.py` builds the `AgentApp`, installs lifespan hooks, registers session routes, and imports `src.agent` to register query handlers.
- `src/app/lifespan.py` prepares JSON session storage, checks Redis when enabled, registers the always-on local MCP client, and closes session runtimes plus MCP clients on shutdown.
- `src/agent/query.py` owns `/process` plus the shared chat execution helpers `_build_query_execution_context()` and `_stream_agent_messages()`, while `src/app/session_routes.py` registers the explicit `/chat`, bootstrap, and shutdown HTTP routes.
- `src/agent/session.py` handles persisted conversation state with `JSONSession` or `RedisSession`.
- `src/agent/session_runtime.py` handles the in-memory bootstrapped runtime for the active session, including the agent, toolkit, dynamic skills, and per-session MCP clients. Only one bootstrapped runtime can be active at once.
- `src/tools/registry.py` is the name-based tool registry used during session bootstrap.
- `src/agent/skill_runtime.py` loads `SKILL.md` frontmatter, registers dynamic skills, and exposes session-local helpers like `list_available_skills`, `activate_skill`, `read_file`, `edit_file`, and `run_local_shell`.
- There are two MCP paths: the startup stdio MCP registered in `src/app/lifespan.py`, and per-session stdio/HTTP MCP clients created from `/sessions/bootstrap`.
- Tests in `tests/conftest.py` auto-mock the startup MCP client, so streaming and bootstrap tests usually do not spawn a real MCP subprocess.