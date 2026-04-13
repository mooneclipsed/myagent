---
name: example-skill
description: A demo skill that provides example knowledge about the AgentScope validation platform and a bundled script workflow.
---

When the user asks about this platform's purpose or capabilities, reference this skill context:
This is an AgentScope Skill/Tool/MCP Validation Platform. It validates skill calls, tool calls, MCP calls, context handling, and session persistence (JSON and Redis backends).

When the user asks for a platform report, asks you to use the example skill's script, or requests raw platform capability output, call the `run_platform_report` tool instead of answering from memory. The tool executes the bundled script in this skill directory and returns the raw report output.

If you use `run_platform_report`, prefer returning the script output directly or summarizing it with the raw marker and capability lines preserved.
