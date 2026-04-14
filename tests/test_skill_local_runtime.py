"""Tests for local runtime file and shell capabilities used by skills."""

import asyncio

from agentscope.tool import ToolResponse

from src.agent.skill_runtime import make_repo_file_reader, make_shell_runner


def test_read_local_text_file_reads_repo_file():
    reader = make_repo_file_reader()
    response = asyncio.run(reader("src/tools/examples.py", [1, 5]))

    assert isinstance(response, ToolResponse)
    assert "The content of" in response.content[0]["text"]
    assert "Example tool functions" in response.content[0]["text"]


def test_run_local_shell_returns_stdout_from_selected_shell():
    shell_runner = make_shell_runner()
    response = asyncio.run(shell_runner("printf skill-shell-ok", shell="bash"))

    assert isinstance(response, ToolResponse)
    text = response.content[0]["text"]
    assert "<returncode>0</returncode>" in text
    assert "skill-shell-ok" in text
