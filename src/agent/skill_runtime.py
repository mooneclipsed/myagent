"""Session-scoped dynamic skill runtime helpers."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse, Toolkit, execute_shell_command, view_text_file

from src.core.config import SkillConfig, SkillScriptConfig, SkillSummary


@dataclass
class SkillManifest:
    """Parsed skill bundle metadata from SKILL.md."""

    name: str
    description: str
    skill_dir: str
    skill_md_path: str
    body: str
    scripts: list[SkillScriptConfig] = field(default_factory=list)


@dataclass
class RegisteredSkillRuntime:
    """Session-owned registered skill state."""

    name: str
    skill_dir: str
    skill_md_path: str
    body: str
    group_name: str
    activation_mode: str
    structured_tools: list[str] = field(default_factory=list)
    activated: bool = False


@dataclass
class SkillRuntimeRegistry:
    """Runtime registry for session-owned skills."""

    skills: dict[str, RegisteredSkillRuntime] = field(default_factory=dict)

    def list_skill_summaries(self) -> list[SkillSummary]:
        return [
            SkillSummary(
                name=skill.name,
                activation_mode=skill.activation_mode,
                structured_tools=skill.structured_tools,
            )
            for skill in self.skills.values()
        ]


def load_skill_manifest(skill_dir: str) -> SkillManifest:
    """Load skill metadata and body from a skill directory."""
    skill_md_path = Path(skill_dir) / "SKILL.md"
    if not skill_md_path.is_file():
        raise ValueError(f"Skill directory '{skill_dir}' is missing SKILL.md")

    with skill_md_path.open("r", encoding="utf-8") as handle:
        post = frontmatter.load(handle)

    name = post.get("name")
    description = post.get("description")
    if not name or not description:
        raise ValueError(
            f"Skill '{skill_dir}' must declare name and description in SKILL.md frontmatter.",
        )

    scripts = [SkillScriptConfig.model_validate(item) for item in post.get("scripts", [])]
    return SkillManifest(
        name=str(name),
        description=str(description),
        skill_dir=str(Path(skill_dir).resolve()),
        skill_md_path=str(skill_md_path.resolve()),
        body=post.content.strip(),
        scripts=scripts,
    )


def build_skill_group_name(skill_name: str) -> str:
    """Build a deterministic tool-group name for a skill."""
    return f"skill__{skill_name.replace('-', '_')}"


def make_repo_file_reader() -> callable:
    """Create a repo-bounded file-reading tool wrapper."""

    async def read_local_text_file(file_path: str, ranges: list[int] | None = None) -> ToolResponse:
        return await view_text_file(file_path=file_path, ranges=ranges)

    read_local_text_file.__name__ = "read_local_text_file"
    read_local_text_file.__doc__ = (
        "Read a local text file from the repository to inspect skill instructions or related resources."
    )
    return read_local_text_file


def make_shell_runner() -> callable:
    """Create a shell execution tool that uses zsh or bash explicitly."""

    async def run_local_shell(
        command: str,
        shell: str = "zsh",
        cwd: str | None = None,
        timeout: int = 300,
    ) -> ToolResponse:
        chosen_shell = shell if shell in {"zsh", "bash"} else "zsh"
        workdir = cwd or os.getcwd()
        wrapped = (
            f"cd {json.dumps(workdir)} && exec {chosen_shell} -lc {json.dumps(command)}"
        )
        return await execute_shell_command(command=wrapped, timeout=timeout)

    run_local_shell.__name__ = "run_local_shell"
    run_local_shell.__doc__ = (
        "Run a local shell command using zsh or bash for repository-local workflows and script execution."
    )
    return run_local_shell


def make_python_callable_runner(script: SkillScriptConfig):
    """Wrap a declared python callable as a structured skill tool."""
    module_name, func_name = (script.target or "").split(":", 1)
    module = importlib.import_module(module_name)
    target = getattr(module, func_name)

    def _tool(**kwargs):
        result = target(**kwargs)
        if isinstance(result, ToolResponse):
            return result
        return ToolResponse(content=[TextBlock(type="text", text=str(result))])

    _tool.__name__ = script.name
    _tool.__doc__ = script.description
    return _tool


def make_python_file_runner(skill_dir: str, script: SkillScriptConfig):
    """Wrap a declared python file as a structured skill tool."""
    script_path = Path(skill_dir) / (script.entrypoint or "")

    def _tool(**kwargs):
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(kwargs) if kwargs else "",
            capture_output=True,
            text=True,
            check=True,
            cwd=skill_dir,
        )
        return ToolResponse(
            content=[TextBlock(type="text", text=completed.stdout.strip())],
        )

    _tool.__name__ = script.name
    _tool.__doc__ = script.description
    return _tool


def make_skill_runner(skill_dir: str, script: SkillScriptConfig):
    """Build the structured runner for a declared skill script."""
    if script.kind == "python_callable":
        return make_python_callable_runner(script)
    if script.kind == "python_file":
        return make_python_file_runner(skill_dir, script)
    raise ValueError(f"Unsupported skill script kind: {script.kind}")


def list_available_skills_factory(registry: SkillRuntimeRegistry):
    """Create a tool listing skills available to the session."""

    def list_available_skills() -> ToolResponse:
        lines = []
        for skill in registry.skills.values():
            state = "active" if skill.activated else "inactive"
            tools = ", ".join(skill.structured_tools) if skill.structured_tools else "none"
            lines.append(f"{skill.name} [{state}] structured_tools={tools}")
        text = "\n".join(lines) if lines else "No dynamic skills are registered for this session."
        return ToolResponse(content=[TextBlock(type="text", text=text)])

    list_available_skills.__name__ = "list_available_skills"
    list_available_skills.__doc__ = "List the dynamic skills available to the current session."
    return list_available_skills


def activate_skill_factory(toolkit: Toolkit, registry: SkillRuntimeRegistry):
    """Create a tool that activates one registered skill and reveals its guidance."""

    def activate_skill(skill_name: str) -> ToolResponse:
        if skill_name not in registry.skills:
            return ToolResponse(
                content=[TextBlock(type="text", text=f"Unknown skill: {skill_name}")],
            )

        skill = registry.skills[skill_name]
        desired_state = {
            name: group.active
            for name, group in toolkit.groups.items()
            if name != "basic"
        }
        desired_state[skill.group_name] = True
        activation_response = toolkit.reset_equipped_tools(**desired_state)
        skill.activated = True
        tool_list = ", ".join(skill.structured_tools) if skill.structured_tools else "none"
        activation_text = (
            f"Skill '{skill.name}' activated.\n"
            f"Read this file before executing the skill:\n- {skill.skill_md_path}\n"
            f"Structured tools now available: {tool_list}\n\n"
            f"Skill instructions:\n{skill.body}"
        )
        return ToolResponse(
            content=[
                TextBlock(type="text", text=activation_text),
                *activation_response.content,
            ],
        )

    activate_skill.__name__ = "activate_skill"
    activate_skill.__doc__ = "Activate a dynamic skill for the current session and reveal its instructions."
    return activate_skill


def register_local_runtime_tools(toolkit: Toolkit) -> None:
    """Register local file and shell capability tools for the session runtime."""
    toolkit.register_tool_function(make_repo_file_reader(), group_name="basic")
    toolkit.register_tool_function(make_shell_runner(), group_name="basic")


def _existing_skill_dir(toolkit: Toolkit, skill_name: str) -> str | None:
    existing = toolkit.skills.get(skill_name)
    if existing is None:
        return None
    if isinstance(existing, dict):
        return existing.get("dir")
    return getattr(existing, "dir", None)


def register_configured_skills(
    toolkit: Toolkit,
    skill_configs: list[SkillConfig],
) -> SkillRuntimeRegistry:
    """Register skill catalog entries and structured tools on a session-owned toolkit."""
    registry = SkillRuntimeRegistry()

    for skill_config in skill_configs:
        manifest = load_skill_manifest(skill_config.skill_dir)
        existing_dir = _existing_skill_dir(toolkit, manifest.name)
        if existing_dir is None:
            toolkit.register_agent_skill(skill_dir=manifest.skill_dir)
        elif Path(existing_dir).resolve() != Path(manifest.skill_dir).resolve():
            raise ValueError(
                f"Skill name conflict for '{manifest.name}' between {existing_dir} and {manifest.skill_dir}.",
            )
        group_name = build_skill_group_name(manifest.name)
        toolkit.create_tool_group(
            group_name,
            description=manifest.description,
            active=skill_config.activation_mode == "eager",
        )

        structured_tools: list[str] = []
        for script in manifest.scripts:
            if not skill_config.expose_structured_tools or not script.structured_tool:
                continue
            runner = make_skill_runner(manifest.skill_dir, script)
            toolkit.register_tool_function(
                tool_func=runner,
                group_name=group_name,
                func_name=script.name,
                func_description=script.description,
                json_schema={
                    "type": "function",
                    "function": {
                        "name": script.name,
                        "description": script.description,
                        "parameters": script.parameters,
                    },
                },
                namesake_strategy="raise",
            )
            structured_tools.append(script.name)

        registry.skills[manifest.name] = RegisteredSkillRuntime(
            name=manifest.name,
            skill_dir=manifest.skill_dir,
            skill_md_path=manifest.skill_md_path,
            body=manifest.body,
            group_name=group_name,
            activation_mode=skill_config.activation_mode,
            structured_tools=structured_tools,
            activated=skill_config.activation_mode == "eager",
        )

    toolkit.register_tool_function(list_available_skills_factory(registry), group_name="basic")
    toolkit.register_tool_function(
        activate_skill_factory(toolkit, registry),
        group_name="basic",
    )
    return registry
