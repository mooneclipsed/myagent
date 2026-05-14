"""Runtime helpers for registering AgentScope skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agentscope.tool import Toolkit

from ..config.schemas import SkillConfig, SkillSummary


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
        before_names = set(toolkit.skills)
        toolkit.register_agent_skill(skill_dir=skill_dir)
        added_names = set(toolkit.skills) - before_names
        if added_names:
            name = next(iter(added_names))
        else:
            name = _find_registered_skill_name(toolkit, skill_dir)
        registry.skills[name] = RegisteredSkillRuntime(
            name=name,
            skill_dir=skill_dir,
        )

    return registry


def _find_registered_skill_name(toolkit: Toolkit, skill_dir: str) -> str:
    for name, skill in toolkit.skills.items():
        directory = skill.get("dir") if isinstance(skill, dict) else getattr(skill, "dir", None)
        if directory is not None and Path(directory).resolve() == Path(skill_dir):
            return name
    raise ValueError(f"Registered skill not found for directory '{skill_dir}'.")
