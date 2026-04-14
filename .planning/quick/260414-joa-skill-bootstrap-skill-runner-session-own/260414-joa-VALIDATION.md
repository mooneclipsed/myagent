# Quick Task 260414-joa - Validation

## Validation Goal

Validate the dynamic skill bootstrap and session-owned skill runner implementation against the quick task decisions and plan.

## Scope Decision

This quick task validates **live-runtime-only skill activation state**.

That means:
- skill catalog and activation state live on the active in-memory session runtime
- activation state is not required to persist across shutdown, pod teardown, or re-bootstrap
- JSON/Redis session persistence continues to cover conversation memory only for this quick task

## Task-to-Test Mapping

### Task 1: Bootstrap contract and session-owned skill state
- Bootstrap accepts dynamic skill declarations
- Shared global toolkit remains legacy/default only
- Session runtime owns skill catalog/tool state

Automated checks:
- `uv run pytest tests/test_session_bootstrap.py -q`
- `uv run pytest tests/test_skill_runtime.py -q -k "bootstrap or catalog"`

### Task 2: Skill runtime catalog, activation, local runtime capabilities, and runners
- Agent can list available skills before activation
- `activate_skill` activates only the intended group
- Local file-read capability can expose `SKILL.md` content
- Local shell execution capability returns `ToolResponse`
- `python_callable` and `python_file` both execute correctly

Automated checks:
- `uv run pytest tests/test_skill_runtime.py -q`
- `uv run pytest tests/test_skill_local_runtime.py -q`
- `uv run pytest tests/test_skill_process_flow.py -q`

### Task 3: Example skill migration and end-to-end proof
- Example skill frontmatter declares script-backed metadata
- Example skill proves gradual disclosure and activation-driven execution
- Legacy shared-toolkit behavior remains intact

Automated checks:
- `uv run pytest tests/test_tools.py tests/test_skill_runtime.py tests/test_skill_process_flow.py -q`
- `sh scripts/run_service.sh` + `uv run python scripts/demos/demo_skill_activation.py`

## Regression Guardrails

- Dynamic skill registration must not mutate `src.tools.toolkit`
- Existing MCP bootstrap flow must remain intact
- Legacy `/process` callers without session bootstrap must continue to use the shared default toolkit
- Skill activation must be additive from the session perspective and must not silently activate unrelated skill groups

## Sampling Strategy

- Per task: run the task-local targeted pytest command
- Before summary: run all quick-task skill tests together
- Before final handoff: run live demo for activation flow

## Pass Criteria

The quick task passes when:
- bootstrap skill declarations are accepted and wired into the session runtime
- skill discovery, activation, local file read, and script-backed execution all work in automated tests
- live activation demo succeeds
- no regression is introduced to legacy toolkit behavior or MCP bootstrap behavior
