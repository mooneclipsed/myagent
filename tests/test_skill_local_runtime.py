"""Tests for local runtime file and shell capabilities used by skills."""

import asyncio
from pathlib import Path

from agentscope.tool import ToolResponse

from src.agent.skill_runtime import make_repo_file_editor, make_repo_file_reader, make_shell_runner


def test_read_file_reads_repo_file():
    reader = make_repo_file_reader()
    response = asyncio.run(reader("src/tools/examples.py", [1, 5]))

    assert isinstance(response, ToolResponse)
    assert "The content of" in response.content[0]["text"]
    assert "Example tool functions" in response.content[0]["text"]


def test_edit_file_writes_repo_file(tmp_path):
    editor = make_repo_file_editor()
    target = Path(tmp_path) / "runtime-edit-test.log"
    response = asyncio.run(editor(str(target), "hello from edit_file"))

    assert isinstance(response, ToolResponse)
    assert target.read_text(encoding="utf-8") == "hello from edit_file"


def test_run_local_shell_returns_stdout_from_selected_shell():
    shell_runner = make_shell_runner()
    response = asyncio.run(shell_runner("printf skill-shell-ok", shell="bash"))

    assert isinstance(response, ToolResponse)
    text = response.content[0]["text"]
    assert "<returncode>0</returncode>" in text
    assert "skill-shell-ok" in text
