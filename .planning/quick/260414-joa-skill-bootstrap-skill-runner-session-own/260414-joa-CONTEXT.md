# Quick Task 260414-joa: 实现动态 skill bootstrap 与 skill runner：session-owned toolkit、skill catalog、按需激活、SKILL.md 渐进式披露、本地文件读取/终端执行能力，以及脚本型 skill（python_callable 与 python_file）执行通道。 - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Task Boundary

Implement dynamic skill bootstrap on top of the current session runtime architecture. The implementation must support session-owned skill registration, skill discovery, gradual skill activation, local file-reading and terminal-execution capabilities for the agent, and script-backed skills using `python_callable` and `python_file` execution modes. The focus is skill runtime behavior; MCP support already implemented remains in place and should coexist with the new skill flow.

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<specifics>
## Specific Ideas

- Reuse the current `session-owned toolkit` pattern already implemented for MCP in `src/agent/session_runtime.py`.
- Add a dedicated `skill_runtime` helper/module instead of overloading the MCP runtime logic with skill parsing and activation concerns.
- Treat `register_agent_skill(...)` as catalog/prompt support and add a separate execution channel for skill-backed scripts.
- Keep both execution paths available:
  - generic local tools (read files / execute shell commands)
  - structured skill script tools for stable, testable skill workflows
- Extend the existing `example_skill` into the first dynamic skill bundle that declares script metadata in `SKILL.md` and proves both activation and script execution behavior.

</specifics>

<canonical_refs>
## Canonical References

- `CLAUDE.md` — project constraints, GSD workflow requirement, and document/language rules.
- `.planning/PROJECT.md` — platform goals, near-statelessness guidance, and session-oriented validation goals.
- `src/agent/session_runtime.py` — the current session runtime owner model that new skill capabilities must integrate with.
- `src/tools/__init__.py` — current base toolkit creation and default tool/skill registration pattern.
- `skills/example_skill/SKILL.md` — current skill format baseline to evolve toward script-aware metadata.

</canonical_refs>
