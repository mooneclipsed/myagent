"""Native file and shell tools for runtime-owned agents."""

from __future__ import annotations

import json
import os
import shutil

from agentscope.message import TextBlock
from agentscope.tool import (
    Bash,
    FunctionTool,
    Read,
    ToolResponse,
    Toolkit,
    Write,
)


WINDOWS_SHELLS = ("powershell", "cmd")
POSIX_SHELLS = ("bash", "zsh")


def make_repo_file_reader() -> callable:
    """Create a repo-bounded file-reading tool wrapper."""

    async def read_file(file_path: str, ranges: list[int] | None = None) -> ToolResponse:
        path = _absolute_path(file_path)
        offset, limit = _line_window(ranges)
        chunk = await Read()(file_path=path, offset=offset, limit=limit)
        return _response_from_content(f"The content of {file_path}:\n{_chunk_text(chunk)}")

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
        del ranges
        chunk = await Write()(file_path=_absolute_path(file_path), content=content)
        return _response_from_content(_chunk_text(chunk))

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
        chunks = []
        async for chunk in Bash()(command=wrapped, timeout=timeout * 1000):
            chunks.append(chunk)
        text = "\n".join(_chunk_text(chunk) for chunk in chunks)
        return _response_from_content(f"<returncode>0</returncode>\n{text}")

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
    toolkit.tool_groups[0].tools.extend(
        [
            FunctionTool(make_repo_file_reader(), name="read_file"),
            FunctionTool(make_repo_file_editor(), name="edit_file"),
            FunctionTool(make_shell_runner(), name="run_local_shell"),
        ]
    )


def _absolute_path(file_path: str) -> str:
    if os.path.isabs(file_path):
        return file_path
    return os.path.abspath(file_path)


def _line_window(ranges: list[int] | None) -> tuple[int, int]:
    if not ranges:
        return 1, 2000
    if len(ranges) == 1:
        return ranges[0], 1
    start, end = ranges[0], ranges[1]
    return start, max(end - start + 1, 1)


def _chunk_text(chunk) -> str:
    return "".join(getattr(block, "text", "") for block in chunk.content)


def _response_from_content(text: str) -> ToolResponse:
    return ToolResponse(content=[TextBlock(type="text", text=text)])
