"""Tests for local runtime file and shell capabilities used by skills."""

import asyncio
from pathlib import Path

from agentscope.tool import ToolResponse

from agentops.tools.native_tools import (
    _build_shell_command,
    make_repo_file_editor,
    make_repo_file_reader,
    make_shell_runner,
)


def test_read_file_reads_repo_file():
    reader = make_repo_file_reader()
    response = asyncio.run(reader("src/agentops/tools/examples.py", [1, 5]))

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


def test_build_shell_command_prefers_bash_on_posix(monkeypatch):
    monkeypatch.setattr("agentops.tools.native_tools.os.name", "posix")
    monkeypatch.setattr(
        "agentops.tools.native_tools.shutil.which",
        lambda shell: "/bin/bash" if shell == "bash" else None,
    )

    command = _build_shell_command("printf ok", "auto", "/tmp/project")

    assert command == 'cd "/tmp/project" && exec bash -lc "printf ok"'


def test_build_shell_command_allows_zsh_on_posix(monkeypatch):
    monkeypatch.setattr("agentops.tools.native_tools.os.name", "posix")
    monkeypatch.setattr(
        "agentops.tools.native_tools.shutil.which",
        lambda shell: "/bin/zsh" if shell == "zsh" else None,
    )

    command = _build_shell_command("printf ok", "zsh", "/tmp/project")

    assert command == 'cd "/tmp/project" && exec zsh -lc "printf ok"'


def test_build_shell_command_uses_powershell_on_windows(monkeypatch):
    monkeypatch.setattr("agentops.tools.native_tools.os.name", "nt")
    monkeypatch.setattr(
        "agentops.tools.native_tools.shutil.which",
        lambda shell: "powershell.exe" if shell == "powershell" else None,
    )

    command = _build_shell_command("Write-Output ok", "auto", "C:\\repo")

    assert command == (
        'powershell -NoProfile -ExecutionPolicy Bypass -Command '
        '"Set-Location -LiteralPath \'C:\\\\repo\'; Write-Output ok"'
    )


def test_build_shell_command_falls_back_to_raw_command(monkeypatch):
    monkeypatch.setattr("agentops.tools.native_tools.os.name", "posix")
    monkeypatch.setattr("agentops.tools.native_tools.shutil.which", lambda shell: None)

    command = _build_shell_command("printf ok", "auto", "/tmp/project")

    assert command == "printf ok"
