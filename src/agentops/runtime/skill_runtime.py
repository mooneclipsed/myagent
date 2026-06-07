"""Runtime helpers for registering AgentScope skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
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
        _append_skill_path(toolkit, skill_dir)
        name = _load_skill_name(skill_dir)
        registry.skills[name] = RegisteredSkillRuntime(
            name=name,
            skill_dir=skill_dir,
        )

    return registry


def _append_skill_path(toolkit: Toolkit, skill_dir: str) -> None:
    if not toolkit.tool_groups:
        toolkit.tool_groups.append(Toolkit(skills_or_loaders=[skill_dir]).tool_groups[0])
        return
    toolkit.tool_groups[0].skills_or_loaders.extend(
        Toolkit(skills_or_loaders=[skill_dir]).tool_groups[0].skills_or_loaders
    )


def _load_skill_name(skill_dir: str) -> str:
    skill_doc = Path(skill_dir) / "SKILL.md"
    if not skill_doc.exists():
        return Path(skill_dir).name
    metadata = frontmatter.load(skill_doc).metadata
    return str(metadata.get("name") or Path(skill_dir).name)
