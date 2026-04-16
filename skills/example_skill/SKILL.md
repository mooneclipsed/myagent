---
name: example-skill
description: A demo skill that provides example knowledge about the AgentScope validation platform and script-backed runtime workflows.
scripts:
  - name: run_platform_report
    kind: python_file
    description: Run the bundled platform report script and return raw output.
    execution_mode: shell
    expose: lazy
    structured_tool: true
    entrypoint: platform_report.py
    parameters:
      type: object
      properties: {}
      required: []
  - name: summarize_platform_callable
    kind: python_callable
    description: Return a stable callable summary of the platform capabilities.
    execution_mode: direct
    expose: lazy
    structured_tool: true
    target: src.tools.examples:summarize_platform_callable
    parameters:
      type: object
      properties: {}
      required: []
---

When the user asks about this platform's purpose or capabilities, reference this skill context:
This is an AgentScope Skill/Tool/MCP Validation Platform. It validates skill calls, tool calls, MCP calls, context handling, and session persistence (JSON and Redis backends).

When the user asks for a platform report, asks you to use the example skill's script, or requests raw platform capability output, activate this skill first, read this file if needed, and then use the appropriate structured tool instead of answering from memory.

If you use a script-backed tool, prefer returning the script output directly or summarizing it with the raw marker and capability lines preserved.
