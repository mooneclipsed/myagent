# Quick Task 260414-joa - Research

**Researched:** 2026-04-14 [VERIFIED: task context]
**Domain:** Session-owned AgentScope skill bootstrap, activation, and structured skill execution [VERIFIED: task context]
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

The content below is copied from `/Users/chengtong/OpenSource/myagent/.planning/quick/260414-joa-skill-bootstrap-skill-runner-session-own/260414-joa-CONTEXT.md`. [VERIFIED: CONTEXT.md]

### Locked Decisions

### Session integration
- Dynamic skills must be part of the session bootstrap contract, alongside model and MCP configuration.
- Skill state belongs to the active session runtime, not to the process-global shared toolkit.
- The existing single active session runtime model remains the runtime owner for skill catalog, activated skill groups, and skill execution metadata.

### Skill discovery and activation
- `register_agent_skill(...)` should be used as a skill catalog / prompt discovery mechanism, not as the execution engine.
- Skills must support gradual disclosure: the agent first discovers that a skill exists, then explicitly activates it when needed.
- Activated skills should reveal their detailed `SKILL.md` guidance and enable their associated execution tools.
- A lightweight skill management layer should expose at least `list_available_skills` and `activate_skill`.

### Local runtime capabilities
- The agent is expected to have local file-reading capability and terminal execution capability (shell/bash/zsh style execution path).
- Skill activation should work with these local capabilities: after activation, the agent may read local skill files and choose whether to execute scripts.
- Local file and shell tools are considered runtime capabilities, not per-skill hacks.

### Script-backed skill execution
- Script-backed skills must support two execution modes in the initial implementation:
  - `python_callable`: direct in-process callable execution
  - `python_file`: subprocess execution of a Python script file
- `python_callable` is preferred when the capability is stable and naturally represented as a Python function.
- `python_file` must run through a child process rather than inline execution.
- High-value skill scripts may also be exposed as structured tool functions in the toolkit, in addition to the generic local shell path.

### Skill package format
- Skill packages continue to require `SKILL.md` as the canonical entrypoint.
- `SKILL.md` frontmatter should be extended to describe script-backed capabilities, including script name, kind, entrypoint or callable target, exposure mode, and parameter schema.
- The runtime should rely on explicitly declared skill scripts rather than scanning every file in a skill directory automatically.

### Tool exposure strategy
- Structured skill script tools should be grouped per skill and default to inactive when the skill is configured as lazy.
- Skill activation should enable the relevant tool group instead of mutating unrelated toolkit state.
- The global shared toolkit should continue to serve legacy/default behavior only.

### Claude's Discretion
- Exact naming of the skill metadata models and helper functions.
- Whether local file/shell capabilities live in dedicated tool groups or the basic group, as long as they remain session-safe and composable with skill activation.
- Whether activation returns the full `SKILL.md` body directly or a condensed activation response that points the agent to read the file, as long as gradual disclosure is preserved.

### Deferred Ideas (OUT OF SCOPE)
- None provided in CONTEXT.md. [VERIFIED: CONTEXT.md]
</user_constraints>

## Project Constraints (from CLAUDE.md)

- Keep `agentscope-runtime` as the primary runtime under evaluation. [VERIFIED: `/Users/chengtong/OpenSource/myagent/CLAUDE.md`]
- Expose chat through FastAPI with streaming responses and preserve the stable skill/tool/MCP call chain. [VERIFIED: `/Users/chengtong/OpenSource/myagent/CLAUDE.md`; `/Users/chengtong/OpenSource/myagent/.planning/PROJECT.md`]
- Prefer a near-stateless server design and avoid pushing new skill state into process-global singletons. [VERIFIED: `/Users/chengtong/OpenSource/myagent/CLAUDE.md`; `/Users/chengtong/OpenSource/myagent/.planning/PROJECT.md`]
- Keep JSON-file and Redis resume compatibility in mind for any session-owned skill state that must survive beyond the live runtime. [VERIFIED: `/Users/chengtong/OpenSource/myagent/CLAUDE.md`; `/Users/chengtong/OpenSource/myagent/.planning/PROJECT.md`]
- Keep model/provider config in `.env` and keep `uv` as the standard workflow tool. [VERIFIED: `/Users/chengtong/OpenSource/myagent/CLAUDE.md`]
- This repository requires Chinese conversation but English-generated documents. [VERIFIED: `/Users/chengtong/OpenSource/myagent/CLAUDE.md`]
- No project skill indexes were present under `.claude/skills/` or `.agents/skills/` during this research. [VERIFIED: filesystem probe]

## Summary

The current repo already has the right session boundary for this task: `bootstrap_session_runtime()` creates a per-session `Toolkit`, `ReActAgent`, and `InMemoryMemory`, while the legacy `/process` path still falls back to the process-global `toolkit`. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py`; `/Users/chengtong/OpenSource/myagent/src/agent/query.py`; `/Users/chengtong/OpenSource/myagent/src/tools/__init__.py`]

AgentScope already provides the three primitives this task needs: prompt-only skill catalog registration via `register_agent_skill(...)`, inactive/active tool groups plus notes, and absolute-state group activation via `reset_equipped_tools(...)`. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]

The cleanest implementation is therefore not a custom skill framework inside the agent loop. It is a thin session-scoped `skill_runtime` layer that parses extended `SKILL.md` frontmatter, registers per-skill tool groups on the session toolkit, exposes `list_available_skills` and `activate_skill`, and binds declared `python_callable` / `python_file` runners as structured tools. [VERIFIED: CONTEXT.md; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`; `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py`]

For gradual disclosure, use `register_agent_skill(...)` for the catalog, keep file-reading available so the agent can inspect `SKILL.md`, and let `activate_skill` reveal concise activation notes plus enable the relevant structured tool group. [VERIFIED: CONTEXT.md; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/agent/_react_agent.py`]

**Primary recommendation:** Add a session-scoped `skill_runtime` helper that owns parsed skill metadata, registers lazy per-skill groups on the session toolkit, keeps file-read capability always available, gates shell/structured runners explicitly, and implements `activate_skill` as a safe wrapper around `Toolkit.reset_equipped_tools(...)`. [VERIFIED: CONTEXT.md; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]

## Standard Stack

### Core
| Library / Primitive | Version | Purpose | Why Standard |
|---|---|---|---|
| `agentscope-runtime` | `1.1.3` [VERIFIED: virtualenv version inspection; `pyproject.toml`] | Runtime package already used by the repo. [VERIFIED: `pyproject.toml`] | Keeps this phase inside the repo's locked runtime choice. [VERIFIED: `CLAUDE.md`] |
| `agentscope` (`Toolkit`, `ReActAgent`, sessions) | `1.0.18` [VERIFIED: virtualenv version inspection] | Provides skill catalog prompt injection, tool groups, activation APIs, and state modules. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/agent/_react_agent.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/session/_session_base.py`] | Reuses installed framework behavior instead of adding a parallel skill engine. [VERIFIED: codebase inspection] |
| `python-frontmatter` (`import frontmatter`) | `1.1.0` [VERIFIED: virtualenv version inspection] | Parses `SKILL.md` frontmatter for both installed AgentScope skill registration and the proposed custom script metadata loader. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`] | Best fit because the installed Toolkit already uses the same parser family. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`] |
| `pydantic` | `2.12.5` [VERIFIED: virtualenv version inspection] | Validates bootstrap skill config and parsed script metadata models. [VERIFIED: repo stack and installed version inspection] | Already standard in this repo and aligns with existing request model patterns. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/core/config.py`; `CLAUDE.md`] |

### Supporting
| Library / Primitive | Version | Purpose | When to Use |
|---|---|---|---|
| `view_text_file` | `agentscope 1.0.18` [VERIFIED: installed source inspection] | Progressive `SKILL.md` disclosure with ranged file reads. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_text_file/_view_text_file.py`] | Keep this available from bootstrap so the agent can actually follow AgentScope's own “read `SKILL.md` carefully” instruction. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`] |
| Thin shell wrapper over `subprocess` using `zsh -lc` or `bash -lc` | Python stdlib [VERIFIED: environment probe] | Explicit local shell execution path with chosen shell semantics and repo-controlled `cwd`. [VERIFIED: environment probe] | Prefer this over raw `execute_shell_command` when the requirement is specifically bash/zsh-style execution. [VERIFIED: CONTEXT.md; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_coding/_shell.py`] |
| `subprocess` + `sys.executable` | Python stdlib [VERIFIED: code inspection] | `python_file` runner via child process on the same interpreter as the app. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/tools/examples.py`] | Use for declared script files; do not route declared scripts through shell strings. [VERIFIED: CONTEXT.md; `/Users/chengtong/OpenSource/myagent/src/tools/examples.py`] |
| `JSONSession` / `RedisSession` + `Toolkit.state_dict()` | `agentscope 1.0.18` [VERIFIED: installed source inspection] | Optional persistence of active tool groups across session reloads. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/session/_json_session.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/session/_redis_session.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`] | Use if planner wants skill activation state to survive beyond the live `_active_runtime`. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py`; `/Users/chengtong/OpenSource/myagent/src/agent/query.py`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| Raw process-global `toolkit` mutation [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/tools/__init__.py`] | Session-owned toolkit registration [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py`] | Session ownership matches the existing bootstrap model and avoids leaking dynamic skills into legacy `/process`. [VERIFIED: codebase inspection] |
| Exposing raw `reset_equipped_tools` directly to the model [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/agent/_react_agent.py`] | Wrapping it behind `activate_skill` [VERIFIED: toolkit API inspection] | The raw API is absolute-state and easy to misuse; the wrapper can preserve unrelated active groups while still reusing AgentScope notes/schema behavior. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`] |
| Generic `execute_python_code` [VERIFIED: installed source inspection] | Declared `python_file` child-process runner [VERIFIED: CONTEXT.md; `/Users/chengtong/OpenSource/myagent/src/tools/examples.py`] | `execute_python_code` runs arbitrary code strings in a temp file; it is the wrong abstraction for declared skill-owned scripts. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_coding/_python.py`] |
| Generic shell-only skill execution [VERIFIED: installed source inspection] | Structured per-skill tools plus generic shell as fallback [VERIFIED: CONTEXT.md] | Structured tools are easier to test, safer to document, and easier to activate lazily; shell remains useful as an escape hatch. [VERIFIED: codebase inspection; installed source inspection] |

**Installation:**
```bash
uv add python-frontmatter
```
This is the only new direct dependency I would add if application code starts importing `frontmatter`; the package is present in the current virtualenv but is not declared directly in `pyproject.toml`. [VERIFIED: virtualenv version inspection; `/Users/chengtong/OpenSource/myagent/pyproject.toml`]

**Version verification:** The current environment was verified as `agentscope-runtime=1.1.3`, `agentscope=1.0.18`, `python-frontmatter=1.1.0`, `pydantic=2.12.5`, `fastapi=0.135.3`, and `pytest=9.0.3`. [VERIFIED: virtualenv version inspection]

## Architecture Patterns

### Recommended Project Structure
```text
src/
├── agent/
│   ├── session_runtime.py      # existing session owner
│   └── skill_runtime.py        # parse catalog, register groups, expose helpers
├── tools/
│   ├── __init__.py             # legacy defaults only
│   ├── local_runtime.py        # file-read + shell wrappers
│   └── skill_runners.py        # python_callable / python_file wrappers
skills/
└── <skill>/
    ├── SKILL.md                # canonical entrypoint + extended frontmatter
    └── *.py                    # declared callable/file targets
```

### Pattern 1: Session-Owned Skill Catalog on Top of the Existing Bootstrap Runtime
**What:** Parse bootstrap skill config inside session bootstrap, register each skill directory with `toolkit.register_agent_skill(...)`, and keep the parsed skill catalog on `SessionRuntime`, not in the module-global `toolkit`. [VERIFIED: CONTEXT.md; `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py`; `/Users/chengtong/OpenSource/myagent/src/tools/__init__.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]

**When to use:** Every bootstrapped session that needs dynamic skills, lazy activation, or session-specific local runtime capability composition. [VERIFIED: CONTEXT.md]

**Example:**
```python
# Source: synthesized from src/agent/session_runtime.py and agentscope/tool/_toolkit.py
session_toolkit = create_base_toolkit()
skill_catalog = load_skill_catalog(request.skills)

for skill in skill_catalog.skills:
    session_toolkit.register_agent_skill(skill.dir)
    session_toolkit.create_tool_group(
        skill.group_name,
        description=skill.description,
        active=not skill.lazy,
        notes=skill.activation_notes,
    )
    for runner in skill.runners:
        session_toolkit.register_tool_function(
            runner.tool_func,
            group_name=skill.group_name,
            func_name=runner.tool_name,
            json_schema=runner.json_schema,
            namesake_strategy="raise",
        )
```

### Pattern 2: Incremental Activation via a Wrapper Around `reset_equipped_tools`
**What:** Keep `activate_skill` as the human-readable tool, but internally compute the merged active-group state and delegate to `toolkit.reset_equipped_tools(...)` so activation is additive from the agent's perspective. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]

**When to use:** Whenever the agent should activate one skill without accidentally dropping previously active local runtime or other skill groups. [VERIFIED: CONTEXT.md; toolkit API inspection]

**Example:**
```python
# Source: synthesized from agentscope/tool/_toolkit.py

def activate_skill(skill_name: str) -> ToolResponse:
    skill = catalog[skill_name]
    final_state = {
        name: group.active
        for name, group in toolkit.groups.items()
        if name != "basic"
    }
    final_state[skill.group_name] = True
    return toolkit.reset_equipped_tools(**final_state)
```

### Pattern 3: Structured Skill Runners Registered with Hidden Preset Metadata
**What:** Use `register_tool_function(...)` with a partial/wrapper so script path, callable target, skill name, and other internal values stay hidden from the model while input parameters remain schema-driven. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]

**When to use:** For `python_callable` and `python_file` tools that should be stable, testable, and lazy-activatable. [VERIFIED: CONTEXT.md]

**Example:**
```python
# Source: synthesized from agentscope/tool/_toolkit.py and src/tools/examples.py
from functools import partial

runner = partial(
    run_skill_python_file,
    script_path=str(skill_script_path),
    skill_name=skill.name,
)

toolkit.register_tool_function(
    tool_func=runner,
    group_name=skill.group_name,
    func_name="run_example_skill_platform_report",
    json_schema=skill_script.json_schema,
    namesake_strategy="raise",
)
```

### Pattern 4: Progressive Disclosure with Catalog Prompt + Group Notes + File Read
**What:** Let `register_agent_skill(...)` expose only catalog metadata in the system prompt, let `activate_skill` return concise notes from the activated group, and keep file reading available so the agent can inspect the full `SKILL.md` on demand. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/agent/_react_agent.py`; CONTEXT.md]

**When to use:** Always; this is the most natural way to implement “discover -> activate -> read details -> run”. [VERIFIED: CONTEXT.md]

### Anti-Patterns to Avoid
- **Treating `register_agent_skill(...)` as an execution engine:** It only records `name`, `description`, and `dir`, then injects prompt text; it does not parse or execute declared scripts. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]
- **Exposing raw `reset_equipped_tools` as the primary UX:** Its semantics are absolute-state, not additive. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]
- **Registering dynamic skill tools on the shared module-global `toolkit`:** That would violate the session-owned design already introduced for bootstrap runtimes. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/tools/__init__.py`; `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py`; CONTEXT.md]
- **Using generic shell execution as the only script path:** It makes deterministic testing and parameter contracts much harder than structured runners. [VERIFIED: installed shell tool inspection; CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Skill catalog prompt injection | Custom system-prompt concatenation | `toolkit.register_agent_skill(skill_dir)` | AgentScope already parses `SKILL.md` frontmatter and formats catalog entries for the agent prompt. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/agent/_react_agent.py`] |
| Lazy tool activation plumbing | A separate custom activation registry | Tool groups + `reset_equipped_tools(...)` behind `activate_skill` | The existing Toolkit already tracks active groups and emits group notes. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`] |
| File-reading capability | Custom file viewer for `SKILL.md` | `view_text_file` or a thin repo-bounded wrapper | The installed text-file tool already returns `ToolResponse` and supports ranged reads. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_text_file/_view_text_file.py`] |
| Session serialization for active groups | Custom JSON/Redis format for toolkit state | `Toolkit.state_dict()` / `load_state_dict()` through existing session backends | Toolkit is already a `StateModule` and sessions already persist named state modules. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/session/_json_session.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/session/_redis_session.py`] |
| Declared `python_file` execution | Arbitrary code-string execution via `execute_python_code` | Child process runner with `sys.executable` and declared script path | `execute_python_code` is for ad hoc code text, not declared repo-owned scripts. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_coding/_python.py`; `/Users/chengtong/OpenSource/myagent/src/tools/examples.py`] |

**Key insight:** Use generic local tools for discovery and debugging, but use declared structured runners for repeatable skill workflows; the generic path should not become the main contract for a stable skill bundle. [VERIFIED: CONTEXT.md; installed tool source inspection]

## Common Pitfalls

### Pitfall 1: `register_agent_skill(...)` Looks More Powerful Than It Is
**What goes wrong:** A planner assumes skill registration will execute skill scripts or parse extended script metadata automatically. [VERIFIED: current repo baseline; installed Toolkit inspection]

**Why it happens:** The installed implementation only loads top-level `SKILL.md`, validates `name` and `description`, and stores `{name, description, dir}` in `toolkit.skills`. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`; `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_types.py`]

**How to avoid:** Keep catalog registration and execution registration as two explicit steps in bootstrap. [VERIFIED: CONTEXT.md]

**Warning signs:** The skill appears in the system prompt, but no new runnable tool exists and no script metadata has been loaded. [VERIFIED: current repo behavior in `/Users/chengtong/OpenSource/myagent/skills/example_skill/SKILL.md`; `/Users/chengtong/OpenSource/myagent/src/tools/examples.py`]

### Pitfall 2: `reset_equipped_tools(...)` Is Absolute-State, Not Additive
**What goes wrong:** Activating one skill silently deactivates previously active groups. [VERIFIED: installed Toolkit inspection]

**Why it happens:** The implementation first deactivates all groups, then re-activates only the groups passed as `True`. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]

**How to avoid:** Wrap it with `activate_skill` that merges the current state before calling the Toolkit API. [VERIFIED: Toolkit API inspection]

**Warning signs:** A tool that worked earlier now returns `FunctionInactiveError` right after another skill was activated. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]

### Pitfall 3: Current Session Persistence Saves Only `memory`
**What goes wrong:** Skill activation survives while `_active_runtime` stays in memory, but disappears after runtime teardown or process restart. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py`; `/Users/chengtong/OpenSource/myagent/src/agent/query.py`]

**Why it happens:** Current load/save calls pass only `memory=...` to the session backends. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py`; `/Users/chengtong/OpenSource/myagent/src/agent/query.py`; session backend source inspection]

**How to avoid:** If cross-restart resume matters for this task, re-register groups first and then load/save `toolkit=session_toolkit` alongside `memory`. [VERIFIED: session backend and Toolkit state API inspection]

**Warning signs:** A resumed session still remembers prior chat context but no longer exposes previously activated skill tools. [VERIFIED: code path analysis]

### Pitfall 4: Generic AgentScope Shell Execution Is `/bin/sh`-Style, Not Explicit `bash` / `zsh`
**What goes wrong:** A planner assumes the built-in shell tool satisfies the task's explicit bash/zsh requirement. [VERIFIED: CONTEXT.md; installed shell tool inspection]

**Why it happens:** `execute_shell_command(...)` delegates to `asyncio.create_subprocess_shell(command)`, which does not let the caller choose `bash` or `zsh` and does not expose `cwd`. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_coding/_shell.py`]

**How to avoid:** Keep file-read on the built-in path, but implement shell execution through a thin wrapper that chooses `zsh -lc` or `bash -lc`, sets a deterministic `cwd`, and still returns `ToolResponse`. [VERIFIED: environment probe; installed shell tool inspection]

**Warning signs:** Commands relying on shell-specific startup behavior or shell-specific syntax behave differently from local terminal expectations. [VERIFIED: installed shell tool inspection]

### Pitfall 5: Interpreter Drift Between System `python3` and the Project Virtualenv
**What goes wrong:** `python_file` uses the wrong interpreter and misses project-installed packages or behaves differently from the app runtime. [VERIFIED: environment probe]

**Why it happens:** This machine currently exposes `python3=3.7.13`, while the project virtualenv exposes Python `3.14.3`. [VERIFIED: environment probe]

**How to avoid:** Always run declared `python_file` scripts with `sys.executable`, exactly as the existing `run_platform_report()` tool already does. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/tools/examples.py`; environment probe]

**Warning signs:** A script succeeds when called from the app but fails when copied into a terminal command that uses `python3`. [VERIFIED: environment probe; existing tool pattern]

### Pitfall 6: Group-State Restore Requires Group Registration Before Load
**What goes wrong:** Saved toolkit state loads, but no skill group becomes active. [VERIFIED: installed Toolkit inspection]

**Why it happens:** `Toolkit.load_state_dict()` only toggles groups that already exist in `self.groups`. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]

**How to avoid:** Parse skills and create all required groups before calling `load_session_state(..., toolkit=session_toolkit)`. [VERIFIED: session backend and Toolkit state API inspection]

**Warning signs:** Persisted session files or Redis keys contain `active_groups`, but reloaded sessions still expose only `basic` tools. [VERIFIED: session and Toolkit source inspection]

## Code Examples

Verified patterns from installed and current sources:

### Catalog + Lazy Group Registration
```python
# Source: agentscope/tool/_toolkit.py; src/agent/session_runtime.py
session_toolkit = create_base_toolkit()

session_toolkit.register_agent_skill(skill_dir=skill.dir)
session_toolkit.create_tool_group(
    group_name=skill.group_name,
    description=skill.description,
    active=False,
    notes=skill.activation_notes,
)
```

### `python_file` Registration with Hidden Internal Path
```python
# Source: agentscope/tool/_toolkit.py; src/tools/examples.py
from functools import partial

runner = partial(run_skill_python_file, script_path=str(script_path))
session_toolkit.register_tool_function(
    tool_func=runner,
    group_name=skill.group_name,
    func_name=script.tool_name,
    json_schema=script.json_schema,
)
```

### Safe `python_file` Runner Pattern
```python
# Source: src/tools/examples.py (same interpreter + argv list)
completed = subprocess.run(
    [sys.executable, str(script_path)],
    capture_output=True,
    text=True,
    check=True,
)
```

### Activation Wrapper That Preserves Existing State
```python
# Source: agentscope/tool/_toolkit.py
current = {
    name: group.active
    for name, group in toolkit.groups.items()
    if name != "basic"
}
current[target_group] = True
return toolkit.reset_equipped_tools(**current)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Shared singleton `toolkit` with a hardcoded `run_platform_report` tool in `basic`. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/tools/__init__.py`; `/Users/chengtong/OpenSource/myagent/src/tools/examples.py`] | Session-owned skill catalog plus per-skill lazy groups and structured runners. [VERIFIED: recommended architecture grounded in existing session runtime and Toolkit APIs] | Repo baseline on 2026-04-13 -> this task's recommended design. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.planning/STATE.md`; current code inspection] | Makes activation explicit, testable, and session-safe. [VERIFIED: architecture analysis] |
| Prompt-only example skill guidance. [VERIFIED: `/Users/chengtong/OpenSource/myagent/skills/example_skill/SKILL.md`] | Prompt catalog + explicit `activate_skill` + file-read disclosure + structured execution. [VERIFIED: CONTEXT.md; Toolkit inspection] | This task. [VERIFIED: task context] | Matches the requested “discover -> activate -> read -> execute” flow. [VERIFIED: CONTEXT.md] |
| Generic shell/file capability not yet integrated into the bootstrapped session flow. [VERIFIED: current code inspection] | File read kept readily available; shell exposed deliberately through session-owned runtime capability registration. [VERIFIED: current code inspection; CONTEXT.md] | This task. [VERIFIED: task context] | Keeps local capability explicit instead of hiding it inside per-skill hacks. [VERIFIED: CONTEXT.md] |

**Deprecated/outdated:**
- Treating `register_agent_skill(...)` as a full skill runner is outdated for this repo; the installed implementation is prompt-only. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py`]
- Using `execute_python_code` for declared skill-owned scripts is the wrong abstraction; it executes ad hoc code strings, not declared repo files. [VERIFIED: `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_coding/_python.py`]

## Assumptions Log

All implementation-relevant factual claims in this research were verified from the current repo, the installed AgentScope source, or the current environment. No unverified factual claims were used as planning anchors. [VERIFIED: research trace]

## Open Questions (RESOLVED)

1. **Should skill activation survive session reloads, or is live-runtime-only state enough for this quick task?** **RESOLVED** [VERIFIED: updated PLAN.md and VALIDATION.md]
   - Resolution: activation state is explicitly **live-runtime-only** for this quick task.
   - Rationale: current session persistence in the project stores `memory` only, and expanding this quick task to persist toolkit activation state would broaden the scope beyond the intended bootstrap/activation runner work.
   - Planner impact: no toolkit-state persistence is required; tests should lock in live-runtime-only semantics instead.

2. **Should generic shell be always available or separately activated?** **RESOLVED** [VERIFIED: updated task direction]
   - Resolution: local file-read capability is treated as a base runtime capability, while shell execution is exposed through the session-owned runtime capability layer and can be grouped separately from per-skill structured tools.
   - Rationale: the agent must have terminal execution ability, but shell should remain an explicit runtime capability rather than being hidden inside one skill or forcing every skill into shell-first behavior.
   - Planner impact: implement dedicated local runtime tools, keep structured skill runners separate, and avoid process-global exposure.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Project virtualenv Python | `python_callable` / `python_file` runners | ✓ [VERIFIED: environment probe] | `3.14.3` [VERIFIED: environment probe] | — |
| System `python3` | Local shell path may hit it by default | ✓ [VERIFIED: environment probe] | `3.7.13` [VERIFIED: environment probe] | Use `sys.executable` for structured `python_file`. [VERIFIED: existing tool pattern] |
| `uv` | Standard project workflow | ✓ [VERIFIED: environment probe] | `0.11.2` [VERIFIED: environment probe] | `.venv/bin/python` and `.venv/bin/pytest` exist if needed. [VERIFIED: environment probe] |
| `pytest` | Validation architecture | ✓ [VERIFIED: environment probe] | `9.0.3` [VERIFIED: environment probe] | — |
| `zsh` | Explicit zsh shell wrapper | ✓ [VERIFIED: environment probe] | `5.9` [VERIFIED: environment probe] | `bash 3.2` is also available. [VERIFIED: environment probe] |
| `redis-cli` | Manual Redis inspection only | ✗ [VERIFIED: environment probe] | — | Use `fakeredis` tests and the Python Redis client already used by the app. [VERIFIED: `pyproject.toml`; tests fixtures] |

**Missing dependencies with no fallback:**
- None identified for the minimal `python_callable` / `python_file` implementation path. [VERIFIED: environment probe; codebase inspection]

**Missing dependencies with fallback:**
- `redis-cli` is missing, but this is not blocking because the repo already uses `fakeredis` in tests and `redis.asyncio` in application code. [VERIFIED: `pyproject.toml`; `/Users/chengtong/OpenSource/myagent/tests/conftest.py`; session source inspection]

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | `pytest 9.0.3` [VERIFIED: environment probe] |
| Config file | `/Users/chengtong/OpenSource/myagent/pyproject.toml` [VERIFIED: `pyproject.toml`] |
| Quick run command | `uv run pytest tests/test_skill_runtime.py tests/test_session_bootstrap.py -q` [VERIFIED: repo test layout + recommended additions] |
| Full suite command | `uv run pytest -q` [VERIFIED: repo tooling conventions + current test infrastructure] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| `QT-01` | Bootstrap registers session-owned skill catalog and lazy groups. [VERIFIED: task context] | unit | `uv run pytest tests/test_skill_runtime.py::test_bootstrap_registers_skill_catalog_and_groups -q` | ❌ Wave 0 |
| `QT-02` | `activate_skill` enables only the intended group and preserves unrelated active groups. [VERIFIED: task context; Toolkit semantics] | unit | `uv run pytest tests/test_skill_runtime.py::test_activate_skill_preserves_existing_groups -q` | ❌ Wave 0 |
| `QT-03` | `python_callable` runner executes in-process and returns `ToolResponse`. [VERIFIED: task context] | unit | `uv run pytest tests/test_skill_runtime.py::test_python_callable_runner_executes_declared_target -q` | ❌ Wave 0 |
| `QT-04` | `python_file` runner executes via child process using `sys.executable`. [VERIFIED: task context; existing pattern] | unit | `uv run pytest tests/test_skill_runtime.py::test_python_file_runner_uses_sys_executable -q` | ❌ Wave 0 |
| `QT-05` | End-to-end `/process` flow can discover a skill, activate it, read `SKILL.md`, and use the structured runner. [VERIFIED: task context] | integration | `uv run pytest tests/test_skill_process_flow.py::test_process_skill_activation_flow -q` | ❌ Wave 0 |
| `QT-06` | Legacy non-bootstrap path keeps current shared-toolkit behavior. [VERIFIED: current code inspection] | regression | `uv run pytest tests/test_tools.py tests/test_session_bootstrap.py -q` | ✅ / partial |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_skill_runtime.py -q` [VERIFIED: recommended validation scope]
- **Per wave merge:** `uv run pytest tests/test_skill_runtime.py tests/test_skill_process_flow.py tests/test_session_bootstrap.py tests/test_tools.py -q` [VERIFIED: recommended validation scope]
- **Phase gate:** `uv run pytest -q` [VERIFIED: repo-wide validation convention]

### Wave 0 Gaps
- [ ] `/Users/chengtong/OpenSource/myagent/tests/test_skill_runtime.py` — unit coverage for catalog parsing, lazy groups, activation, and structured runners. [VERIFIED: test gap analysis]
- [ ] `/Users/chengtong/OpenSource/myagent/tests/test_skill_process_flow.py` — integration coverage for discover -> activate -> read -> execute. [VERIFIED: test gap analysis]
- [ ] `/Users/chengtong/OpenSource/myagent/tests/test_skill_local_runtime.py` — local file-read and shell capability boundaries, especially bash/zsh wrapper behavior. [VERIFIED: test gap analysis]
- [ ] Bootstrap/session persistence test update — if toolkit state persistence is included, extend `/Users/chengtong/OpenSource/myagent/tests/test_session_bootstrap.py`. [VERIFIED: current session test layout]

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no [VERIFIED: current task scope] | Not in scope for this quick task. [VERIFIED: task scope analysis] |
| V3 Session Management | yes [VERIFIED: session-owned runtime and JSON/Redis resume context] | Keep session state inside the existing session runtime/session backend boundary; avoid new process-global state. [VERIFIED: CONTEXT.md; session runtime inspection] |
| V4 Access Control | yes [VERIFIED: tool-group activation as capability gating] | Use per-skill tool groups plus explicit activation instead of exposing every skill runner in `basic`. [VERIFIED: CONTEXT.md; Toolkit inspection] |
| V5 Input Validation | yes [VERIFIED: current config model patterns] | Validate bootstrap skill config and script metadata with `pydantic`; validate file/shell inputs before execution. [VERIFIED: `/Users/chengtong/OpenSource/myagent/src/core/config.py`; stack inspection] |
| V6 Cryptography | no [VERIFIED: current task scope] | Not needed for this phase. [VERIFIED: task scope analysis] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Path traversal through local file-read | Information Disclosure | Resolve paths against repo/skill roots, normalize them, and reject out-of-scope paths if the implementation wraps file-read. [VERIFIED: local file-read requirement; current built-in tool behavior] |
| Shell injection through generic shell capability | Tampering / Elevation | Keep generic shell separate from structured skill runners; do not route declared scripts through shell strings. [VERIFIED: CONTEXT.md; installed shell tool inspection] |
| Wrong interpreter for `python_file` | Integrity / Availability | Use `sys.executable` instead of `python` or `python3`. [VERIFIED: existing `run_platform_report()` pattern; environment probe] |
| Over-exposed skill tools before activation | Elevation | Register structured tools into inactive per-skill groups and activate them explicitly. [VERIFIED: CONTEXT.md; Toolkit inspection] |
| Hidden state leakage across sessions | Tampering | Keep dynamic skill registration on the session toolkit, not the shared module-global toolkit. [VERIFIED: current code inspection; CONTEXT.md] |

## Sources

### Primary (HIGH confidence)
- `/Users/chengtong/OpenSource/myagent/src/agent/session_runtime.py` — current session-owned runtime model and bootstrap ownership.
- `/Users/chengtong/OpenSource/myagent/src/agent/query.py` — current legacy `/process` fallback path and persistence scope.
- `/Users/chengtong/OpenSource/myagent/src/tools/__init__.py` — current shared-toolkit defaults and example skill registration.
- `/Users/chengtong/OpenSource/myagent/src/tools/examples.py` — current safe `python_file`-style subprocess pattern using `sys.executable`.
- `/Users/chengtong/OpenSource/myagent/skills/example_skill/SKILL.md` — current prompt-oriented skill baseline.
- `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_toolkit.py` — `register_agent_skill`, tool groups, `reset_equipped_tools`, `register_tool_function`, and Toolkit state APIs.
- `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/agent/_react_agent.py` — how skill prompt injection reaches the system prompt.
- `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_coding/_shell.py` — current generic shell execution semantics.
- `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_coding/_python.py` — current arbitrary code-string execution semantics.
- `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/tool/_text_file/_view_text_file.py` — current file-read capability behavior.
- `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/session/_json_session.py` — JSON session save/load semantics.
- `/Users/chengtong/OpenSource/myagent/.venv/lib/python3.14/site-packages/agentscope/session/_redis_session.py` — Redis session save/load semantics.
- `/Users/chengtong/OpenSource/myagent/CLAUDE.md` — project constraints and workflow requirements.
- `/Users/chengtong/OpenSource/myagent/.planning/PROJECT.md` — platform-level session/statelessness goals.
- `/Users/chengtong/OpenSource/myagent/.planning/config.json` — `workflow.nyquist_validation=true`.
- Environment probes (`python`, `uv`, `pytest`, `zsh`, `bash`, `redis-cli`) — machine availability and version facts.

### Secondary (MEDIUM confidence)
- `/Users/chengtong/OpenSource/myagent/.planning/quick/260413-m0d-example-skill-skill/260413-m0d-SUMMARY.md` — prior quick-task summary confirming the repo's current script-backed skill pattern is prompt guidance plus a dedicated tool.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified directly from the current repo, installed package sources, and active virtualenv. [VERIFIED: research trace]
- Architecture: HIGH - recommendations are anchored to the exact session runtime and Toolkit APIs already present. [VERIFIED: codebase inspection]
- Pitfalls: HIGH - most pitfalls come from direct source inspection plus environment probes, not from stale training assumptions. [VERIFIED: research trace]

**Research date:** 2026-04-14 [VERIFIED: task context]
**Valid until:** 2026-05-14 [VERIFIED: 30-day planning horizon for repo-local framework research]
