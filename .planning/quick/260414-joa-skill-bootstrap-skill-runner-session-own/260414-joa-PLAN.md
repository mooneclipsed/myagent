---
phase: quick-260414-joa
plan: 01
type: execute
wave: 1
depends_on: []
mode: quick-full
description: Implement session-owned dynamic skill bootstrap and a separate skill runner with explicit catalog, activation, local runtime tools, and script-backed execution channels.
date: 2026-04-14
autonomous: true
files_modified:
  - src/core/config.py
  - src/agent/session_runtime.py
  - src/tools/__init__.py
  - src/tools/examples.py
  - src/agent/skill_runtime.py
  - skills/example_skill/SKILL.md
  - tests/test_session_bootstrap.py
  - tests/test_tools.py
  - tests/test_skill_runtime.py
  - tests/test_skill_local_runtime.py
  - tests/test_skill_process_flow.py
  - scripts/demos/demo_skill_activation.py
must_haves:
  truths:
    - "A bootstrapped session can declare dynamic skills in its bootstrap contract and owns the resulting skill catalog/tool state for that session only."
    - "The agent can discover available skills first, then explicitly activate a skill before its structured tools become callable."
    - "After activation, the agent gains progressive disclosure for the selected skill and can use local file-reading plus shell execution capabilities within the session runtime."
    - "Script-backed skills can execute through both `python_callable` and `python_file` channels without relying on global toolkit mutation."
    - "The legacy shared toolkit continues to serve `/process` default behavior without inheriting session-only skill state."
    - "Skill activation state is live-runtime-only for this quick task and is not required to survive shutdown, pod teardown, or re-bootstrap."
  artifacts:
    - path: "src/core/config.py"
      provides: "Session bootstrap schema for dynamic skill declarations and script capability metadata"
      contains: "SessionBootstrapRequest"
    - path: "src/agent/skill_runtime.py"
      provides: "Skill catalog parsing, activation flow, and script runner registration"
      contains: "list_available_skills"
    - path: "src/agent/session_runtime.py"
      provides: "Session-owned runtime bootstrap wiring for skill catalog, tool groups, and local capability registration"
      contains: "bootstrap_session_runtime"
    - path: "skills/example_skill/SKILL.md"
      provides: "Canonical skill metadata with explicit script-backed frontmatter"
      contains: "python_callable"
    - path: "tests/test_skill_runtime.py"
      provides: "Regression coverage for catalog, activation, and script execution modes"
      contains: "activate_skill"
  key_links:
    - from: "src/core/config.py"
      to: "src/agent/session_runtime.py"
      via: "SessionBootstrapRequest.skill config parsed during bootstrap"
      pattern: "skills|dynamic_skills|skill_dirs"
    - from: "src/agent/session_runtime.py"
      to: "src/agent/skill_runtime.py"
      via: "session bootstrap builds catalog and registers inactive tool groups"
      pattern: "skill_runtime|activate_skill|list_available_skills"
    - from: "src/agent/skill_runtime.py"
      to: "skills/example_skill/SKILL.md"
      via: "frontmatter parsing and gradual disclosure"
      pattern: "frontmatter|SKILL\.md"
    - from: "src/agent/skill_runtime.py"
      to: "src/tools/examples.py"
      via: "python_callable/python_file execution adapters and local capability helpers"
      pattern: "subprocess|callable|ToolResponse"
---

# Quick Task 260414-joa: Dynamic skill bootstrap and session-owned skill runner

## Objective
Implement dynamic skill bootstrap on top of the existing session runtime so each bootstrapped session owns its skill catalog, activation state, local runtime capabilities, and script-backed execution path.

Purpose: Deliver the missing execution layer behind the current prompt-only skill registration flow while preserving the existing MCP/session bootstrap architecture and the legacy shared toolkit path.
Output: A session-safe bootstrap contract for skills, a dedicated skill runtime module, explicit catalog/activation tools, local file and shell capabilities, migrated example skill metadata, and regression/demo coverage for `python_callable` plus `python_file`, with skill activation state treated as live-runtime-only.

## Decision Coverage Matrix

| Decision | Plan | Task | Coverage | Notes |
|----------|------|------|----------|-------|
| D-01 Session-owned dynamic skills in bootstrap | 01 | 1 | Full | Session bootstrap schema and runtime ownership live in `src/core/config.py` and `src/agent/session_runtime.py`. |
| D-02 `register_agent_skill` is catalog only | 01 | 1 | Full | Runtime keeps discovery/prompt support separate from executable skill tool registration. |
| D-03 Gradual disclosure + explicit activation | 01 | 2 | Full | Catalog + activation tools and lazy inactive groups are introduced before execution. |
| D-04 Local file read + shell execution capability | 01 | 2 | Full | Session runtime exposes these as runtime capabilities, not per-skill hacks. |
| D-05 `python_callable` and `python_file` first | 01 | 2 | Full | Both execution adapters are part of the initial runner contract and tests. |
| D-06 `SKILL.md` frontmatter declares script capabilities | 01 | 3 | Full | Example skill migrated to explicit metadata schema. |
| D-07 Structured skill tools grouped per skill and lazy by default | 01 | 2 | Full | Each activated skill toggles its own tool group only. |
| D-08 Global shared toolkit remains legacy/default only | 01 | 1 | Full | Legacy `src.tools.toolkit` path stays untouched for non-bootstrap flows except shared helper extraction. |

## Dependency Order
Task 1 -> Task 2 -> Task 3

<objective>
Build a session-owned skill runtime that extends the existing bootstrap flow without collapsing MCP, shared toolkit, and skill execution concerns into one layer.

Purpose: The current codebase proves prompt-oriented skill discovery and one-off script tools, but it does not yet support session-scoped dynamic skills, explicit activation, or a general skill runner.
Output: Config + runtime contracts, activation/runtime tools, migrated example skill package, and focused regression/demo proof.
</objective>

<context>
@/Users/chengtong/OpenSource/myagent/CLAUDE.md
@/Users/chengtong/OpenSource/myagent/.planning/PROJECT.md
@/Users/chengtong/OpenSource/myagent/.planning/STATE.md
@/Users/chengtong/OpenSource/myagent/.planning/quick/260414-joa-skill-bootstrap-skill-runner-session-own/260414-joa-CONTEXT.md
@/Users/chengtong/OpenSource/myagent/src/core/config.py
@/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py
@/Users/chengtong/OpenSource/myagent/src/agent/query.py
@/Users/chengtong/OpenSource/myagent/src/app/session_routes.py
@/Users/chengtong/OpenSource/myagent/src/tools/__init__.py
@/Users/chengtong/OpenSource/myagent/src/tools/examples.py
@/Users/chengtong/OpenSource/myagent/skills/example_skill/SKILL.md
@/Users/chengtong/OpenSource/myagent/tests/test_session_bootstrap.py
@/Users/chengtong/OpenSource/myagent/tests/test_tools.py

<interfaces>
From `src/agent/session_runtime.py`:
```python
@dataclass
class SessionRuntime:
    session_id: str
    toolkit: Toolkit
    agent: ReActAgent
    memory: InMemoryMemory
    mcp_clients: list[StatefulClientBase] = field(default_factory=list)
    resolved_config: dict = field(default_factory=dict)
    mcp_servers: list[MCPServerSummary] = field(default_factory=list)
```
The new skill runtime state must attach here, not to the process-global toolkit, per D-01.

From `src/tools/__init__.py`:
```python
def create_base_toolkit() -> Toolkit:
    target_toolkit = Toolkit()
    register_default_tools(target_toolkit)
    register_default_skills(target_toolkit)
    return target_toolkit

toolkit = create_base_toolkit()
```
Preserve this as the legacy/default path per D-08. Session bootstrap may compose from the same helper layer but must not mutate the module-level singleton.

From AgentScope `Toolkit`:
```python
def register_agent_skill(self, skill_dir: str) -> None

def create_tool_group(self, group_name: str, description: str, active: bool = False, notes: str | None = None) -> None

def update_tool_groups(self, group_names: list[str], active: bool) -> None

def reset_equipped_tools(self, **kwargs: Any) -> ToolResponse
```
Use `register_agent_skill(...)` for prompt/catalog support only per D-02, and use tool groups for lazy activation per D-03/D-07.

From AgentScope `ReActAgent`:
```python
agent = ReActAgent(..., toolkit=toolkit)
agent.sys_prompt -> toolkit.get_agent_skill_prompt()
```
Skill discovery prompt comes from the toolkit, but execution tools must be registered separately in the session-owned toolkit before the agent can call them.

From `skills/example_skill/SKILL.md`:
```yaml
---
name: example-skill
description: A demo skill ...
---
```
Extend this frontmatter instead of inventing a parallel manifest file, per D-06.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend bootstrap contract and isolate session-owned skill state</name>
  <files>src/core/config.py, src/agent/session_runtime.py, src/tools/__init__.py</files>
  <action>Extend `SessionBootstrapRequest` so bootstrap can accept dynamic skill declarations for session bootstrap per D-01, using an explicit schema for skill directories and lazy/activation behavior instead of implicit scanning. Add session runtime fields for skill catalog, activated skill ids/groups, and any script execution metadata needed to route future calls. Keep `register_agent_skill(...)` as catalog/prompt support only per D-02: the session bootstrap path should register discovered skills into the bootstrapped toolkit for prompt visibility, but it must not treat that API as the execution engine. Refactor toolkit helpers only as needed so `create_base_toolkit()` still builds the legacy shared toolkit for `/process`, while session bootstrap composes a fresh session-owned toolkit without mutating `src.tools.toolkit`, per D-08. Do not collapse skill state into globals, do not replace the MCP bootstrap loop, and do not remove the existing single-active-session ownership model.</action>
  <verify>
    <automated>uv run pytest tests/test_session_bootstrap.py -q</automated>
  </verify>
  <done>Bootstrapped sessions can carry skill declarations in config, runtime ownership for skills lives on `SessionRuntime`, and the shared singleton toolkit remains the default non-bootstrap path.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add skill runtime catalog, activation tools, local runtime capabilities, and script execution adapters</name>
  <files>src/agent/skill_runtime.py, src/agent/session_runtime.py, src/tools/examples.py, tests/test_skill_runtime.py, tests/test_skill_local_runtime.py, tests/test_skill_process_flow.py</files>
  <behavior>
    - Test 1: A bootstrapped session lists available skills before activation, and skill tool groups remain inactive by default per D-03/D-07.
    - Test 2: `activate_skill` reveals the selected skill’s detailed instructions and only activates that skill’s structured tool group.
    - Test 3: Local file-reading capability can return the selected `SKILL.md` body or targeted local file content without using the global toolkit.
    - Test 4: Local shell execution capability runs through a controlled subprocess path and returns stdout/stderr in `ToolResponse` form.
    - Test 5: Script-backed skill metadata with `python_callable` invokes an in-process callable, while `python_file` executes via child process, per D-05.
  </behavior>
  <action>Create a dedicated `src/agent/skill_runtime.py` module rather than overloading MCP bootstrap logic, per the context guidance. This module should parse skill metadata from `SKILL.md`, expose runtime helpers for catalog assembly, and register a lightweight skill-management layer with at least `list_available_skills` and `activate_skill` per D-03. Add session-safe local runtime capability tools for file reading and shell/bash/zsh-style command execution per D-04; these capabilities belong to the session runtime and should not be implemented as hardcoded logic inside one example skill. For executable skills, implement two first-class adapters per D-05: `python_callable` routes to a stable Python function imported from trusted code, and `python_file` launches a subprocess against the declared script file. Register structured skill tools into per-skill inactive tool groups when the skill is lazy, and activate only the selected group on `activate_skill`, per D-07. Reuse or extract helper code from `src/tools/examples.py` if that reduces duplication, but do not reintroduce arbitrary command execution through user-controlled script paths or shell interpolation. Keep MCP registration and bootstrapped agent construction intact; the new layer should compose with the existing toolkit and `ReActAgent` model rather than replace them.</action>
  <verify>
    <automated>uv run pytest tests/test_skill_runtime.py tests/test_skill_local_runtime.py tests/test_skill_process_flow.py tests/test_session_bootstrap.py -q</automated>
  </verify>
  <done>The codebase has a separate skill runtime layer with catalog/activation tools, session-local file and shell capabilities, and tested `python_callable` plus `python_file` execution channels wired into bootstrapped toolkits only; activation state is explicitly live-runtime-only for this quick task.</done>
</task>

<task type="auto">
  <name>Task 3: Migrate the example skill metadata and prove the end-to-end activation flow</name>
  <files>skills/example_skill/SKILL.md, src/tools/examples.py, tests/test_tools.py, tests/test_skill_runtime.py, scripts/demos/demo_skill_activation.py</files>
  <action>Extend `skills/example_skill/SKILL.md` frontmatter so it explicitly declares script-backed capabilities per D-06, including script kind, entrypoint/callable target, exposure mode, and parameter schema. Use the example skill as the first bundle that proves both execution modes: keep the existing script-backed report path, and add or expose a stable `python_callable` target from trusted project code so the runtime can exercise both D-05 channels. Update or split tool tests so legacy shared-toolkit behavior and new dynamic-session skill behavior are both covered without conflating them. Add a focused demo script that bootstraps a session with the example skill, verifies the skill is discoverable before activation, activates it, and then proves the response path can use the activated script capability through the session-owned runtime. Make the demo assertions strict enough to distinguish real activation/script execution from generic model text. Do not remove the current legacy example tool path unless the implementation intentionally migrates it behind a compatibility wrapper.</action>
  <verify>
    <automated>uv run pytest tests/test_tools.py tests/test_skill_runtime.py -q && bash -lc 'bash scripts/run_service.sh >/tmp/260414-joa-skill.log 2>&1 & PID=$!; trap "kill $PID" EXIT; for i in {1..30}; do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 1; done; uv run python scripts/demos/demo_skill_activation.py'</automated>
  </verify>
  <done>The example skill declares executable metadata in `SKILL.md`, both script modes are exercised through project code, and there is a runnable end-to-end demo for bootstrap -> discover -> activate -> execute.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client → `/sessions/bootstrap` | Untrusted bootstrap payload selects session id, MCP config, and dynamic skill declarations |
| session runtime → local filesystem | Activated skills and local file tools read project-local files that must stay within declared paths |
| session runtime → subprocess shell/python | Local shell and `python_file` execution cross from agent intent into OS command execution |
| `SKILL.md` metadata → runner registration | Frontmatter drives executable registration and must be validated before use |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-260414-01 | T | `src/agent/skill_runtime.py` metadata loader | mitigate | Validate `SKILL.md` frontmatter with explicit pydantic models; reject undeclared script kinds, missing targets, and invalid parameter schema before registration. |
| T-260414-02 | E | local shell execution tool | mitigate | Keep shell execution in a dedicated session runtime tool with explicit subprocess invocation, bounded working directory/inputs, and no hidden activation in the global toolkit. |
| T-260414-03 | I | local file-reading capability | mitigate | Restrict reads to declared/expected local paths for session skills or repository workspace roots; return controlled text output only. |
| T-260414-04 | T | `python_file` runner | mitigate | Resolve script paths from declared skill metadata only and execute via child process without arbitrary user-supplied file paths. |
| T-260414-05 | E | `python_callable` runner | mitigate | Import only trusted project callables referenced by explicit metadata and fail closed on unresolved import targets. |
| T-260414-06 | R | activation state on toolkit groups | mitigate | Persist activation in session runtime state and assert group toggling behavior with regression tests so skills cannot silently activate unrelated groups. |
| T-260414-07 | D | failed bootstrap or runner registration | mitigate | Roll back partially registered skill tools on bootstrap failure using the same cleanup discipline already used for MCP clients; keep failure messages redacted and specific. |
| T-260414-08 | S | global shared toolkit | accept | The shared toolkit remains a legacy default path per D-08; risk is limited if new skill state never mutates the singleton and tests lock that boundary down. |
</threat_model>

<verification>
- `uv run pytest tests/test_session_bootstrap.py -q`
- `uv run pytest tests/test_skill_runtime.py tests/test_tools.py -q`
- `bash -lc 'bash scripts/run_service.sh >/tmp/260414-joa-skill.log 2>&1 & PID=$!; trap "kill $PID" EXIT; for i in {1..30}; do curl -sf http://127.0.0.1:8000/docs >/dev/null && break; sleep 1; done; uv run python scripts/demos/demo_skill_activation.py'`
</verification>

<success_criteria>
- Session bootstrap accepts dynamic skill declarations and stores skill state on `SessionRuntime`, not on the process-global toolkit.
- `register_agent_skill(...)` remains discovery/prompt support only, while execution comes from the dedicated skill runtime layer.
- The agent can list skills, activate one explicitly, read local skill files, and run local shell/script-backed workflows within the bootstrapped session.
- `python_callable` and `python_file` both execute through declared metadata from `SKILL.md` and are covered by tests.
- The example skill proves gradual disclosure plus activation-driven structured tool enablement, the legacy `/process` toolkit path remains intact, and skill activation semantics are explicitly live-runtime-only.
</success_criteria>

<output>
After completion, create `/Users/chengtong/OpenSource/myagent/.planning/quick/260414-joa-skill-bootstrap-skill-runner-session-own/260414-joa-SUMMARY.md`.
</output>
