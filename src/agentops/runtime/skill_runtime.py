"""Runtime helpers for registering AgentScope skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agentscope.tool import Toolkit

from ..config.runtime_models import SkillConfig, SkillSummary


@dataclass
class RegisteredSkillRuntime:
    """Session-owned registered skill state."""

    name: str
    skill_dir: str


@dataclass
class SkillRuntimeRegistry:
    """Runtime registry for session-owned skills."""

    skills: dict[str, RegisteredSkillRuntime] = field(default_factory=dict)

    def list_skill_summaries(self) -> list[SkillSummary]:
        return [
            SkillSummary(
                name=skill.name,
                structured_tools=[],
            )
            for skill in self.skills.values()
        ]


def register_configured_skills(
    toolkit: Toolkit,
    skill_configs: list[SkillConfig],
) -> SkillRuntimeRegistry:
    """Register AgentScope skill catalog entries on a runtime-owned toolkit."""
    registry = SkillRuntimeRegistry()

    for skill_config in skill_configs:
        skill_dir = str(Path(skill_config.skill_dir).resolve())
        before_names = set(_toolkit_skills(toolkit))
        toolkit.tool_groups[0].skills_or_loaders.append(skill_dir)
        after_names = set(_toolkit_skills(toolkit))
        added_names = after_names - before_names
        name = next(iter(added_names)) if added_names else _skill_name(skill_dir)
        registry.skills[name] = RegisteredSkillRuntime(
            name=name,
            skill_dir=skill_dir,
        )
        _sync_legacy_skill_view(toolkit)

    return registry


def _find_registered_skill_name(toolkit: Toolkit, skill_dir: str) -> str:
    for name, skill in _toolkit_skills(toolkit).items():
        directory = skill.get("dir") if isinstance(skill, dict) else getattr(skill, "dir", None)
        if directory is not None and Path(directory).resolve() == Path(skill_dir):
            return name
    raise ValueError(f"Registered skill not found for directory '{skill_dir}'.")


def _toolkit_skills(toolkit: Toolkit) -> dict[str, dict[str, str]]:
    skills = {}
    for skill in toolkit.tool_groups[0].skills_or_loaders:
        skill_dir = str(Path(str(skill)).resolve())
        skills[_skill_name(skill_dir)] = {"dir": skill_dir}
    return skills


def _sync_legacy_skill_view(toolkit: Toolkit) -> None:
    if not hasattr(toolkit, "skills"):
        toolkit.skills = {}
    toolkit.skills.clear()
    toolkit.skills.update(_toolkit_skills(toolkit))


def _skill_name(skill_dir: str) -> str:
    skill_md = Path(skill_dir) / "SKILL.md"
    if not skill_md.exists():
        return Path(skill_dir).name
    in_frontmatter = False
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if line.strip() == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter and line.startswith("name:"):
            return line.removeprefix("name:").strip()
    return Path(skill_dir).name
