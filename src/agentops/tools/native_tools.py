"""Native file and shell tools for runtime-owned agents."""

from __future__ import annotations

import json
import os
import shutil

from agentscope.tool import (
    ToolResponse,
    Toolkit,
    execute_shell_command,
    view_text_file,
    write_text_file,
)


WINDOWS_SHELLS = ("powershell", "cmd")
POSIX_SHELLS = ("bash", "zsh")


def make_repo_file_reader() -> callable:
    """Create a repo-bounded file-reading tool wrapper."""

    async def read_file(file_path: str, ranges: list[int] | None = None) -> ToolResponse:
        return await view_text_file(file_path=file_path, ranges=ranges)

    read_file.__name__ = "read_file"
    read_file.__doc__ = "Read a local text file from the repository."
    return read_file


def make_repo_file_editor() -> callable:
    """Create a repo-bounded file-writing tool wrapper."""

    async def edit_file(
        file_path: str,
        content: str,
        ranges: list[int] | None = None,
    ) -> ToolResponse:
        return await write_text_file(file_path=file_path, content=content, ranges=ranges)

    edit_file.__name__ = "edit_file"
    edit_file.__doc__ = "Write or update a local text file in the repository."
    return edit_file


def make_shell_runner() -> callable:
    """Create a shell execution tool that uses zsh or bash explicitly."""

    async def run_local_shell(
        command: str,
        shell: str = "auto",
        cwd: str | None = None,
        timeout: int = 300,
    ) -> ToolResponse:
        workdir = cwd or os.getcwd()
        wrapped = _build_shell_command(command, shell, workdir)
        return await execute_shell_command(command=wrapped, timeout=timeout)

    run_local_shell.__name__ = "run_local_shell"
    run_local_shell.__doc__ = (
        "Run a local shell command using zsh or bash for repository-local workflows and script execution."
    )
    return run_local_shell


def _build_shell_command(command: str, shell: str, workdir: str) -> str:
    shell_name = _select_shell(shell)
    if shell_name is None:
        return command
    if os.name == "nt":
        return _build_windows_shell_command(command, shell_name, workdir)
    return f"cd {json.dumps(workdir)} && exec {shell_name} -lc {json.dumps(command)}"


def _select_shell(shell: str) -> str | None:
    requested_shell = shell.lower()
    available_shells = WINDOWS_SHELLS if os.name == "nt" else POSIX_SHELLS
    if requested_shell in available_shells and shutil.which(requested_shell):
        return requested_shell
    for candidate in available_shells:
        if shutil.which(candidate):
            return candidate
    return None


def _build_windows_shell_command(command: str, shell: str, workdir: str) -> str:
    if shell == "cmd":
        return f"cd /d {json.dumps(workdir)} && {command}"
    ps_script = f"Set-Location -LiteralPath {_quote_powershell_string(workdir)}; {command}"
    return f"powershell -NoProfile -ExecutionPolicy Bypass -Command {json.dumps(ps_script)}"


def _quote_powershell_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def register_native_tools(toolkit: Toolkit) -> None:
    """Register native file and shell capability tools for a runtime-owned toolkit."""
    toolkit.register_tool_function(make_repo_file_reader(), group_name="basic")
    toolkit.register_tool_function(make_repo_file_editor(), group_name="basic")
    toolkit.register_tool_function(make_shell_runner(), group_name="basic")
