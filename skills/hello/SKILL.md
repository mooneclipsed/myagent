---
name: hello
description: A deterministic greeting skill for end-to-end capability validation.
scripts:
  - name: say_hello
    kind: python_file
    description: Greet a named person and emit deterministic validation markers.
    execution_mode: shell
    expose: lazy
    structured_tool: true
    entrypoint: scripts/say_hello.py
    parameters:
      type: object
      properties:
        name:
          type: string
          description: The person's name to greet.
      required: [name]
---

Use this skill when the user asks for a greeting or wants to validate dynamic skill execution.

When you need to greet someone:
1. Activate this skill.
2. If needed, read `resources/usage.md` for an example.
3. Call `say_hello` with the target name.
4. If the user asks to persist or verify the result, use the local runtime tools `edit_file` and `read_file`.
