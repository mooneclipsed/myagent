---
name: hello
description: A deterministic greeting skill for end-to-end capability validation.
---

Use this skill when the user asks for a greeting or wants to validate dynamic skill execution.

When you need to greet someone:
1. Read `resources/usage.md` for the script usage example if needed.
2. Run `scripts/say_hello.py` with the target name as JSON input using the native shell tool.
3. Return the script output directly, including the greeting, timestamp, and marker file path.
4. If the user asks to persist or verify the result, use the native tools `edit_file` and `read_file`.
