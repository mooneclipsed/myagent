"""Tests for dynamic skill registration helpers."""

from pathlib import Path

from src.runtime.skill_runtime import register_configured_skills
from src.config.schemas import SkillConfig
from src.tools import create_base_toolkit
from src.tools.native_tools import register_native_tools


EXAMPLE_SKILL_DIR = str(
    (Path(__file__).resolve().parents[1] / "skills" / "example_skill").resolve()
)


def test_register_configured_skills_registers_agentscope_skill():
    toolkit = create_base_toolkit(include_legacy_example_skill_support=False)
    register_native_tools(toolkit)
    registry = register_configured_skills(
        toolkit,
        [SkillConfig(skill_dir=EXAMPLE_SKILL_DIR)],
    )

    assert "example-skill" in registry.skills
    assert "example-skill" in toolkit.skills
    assert registry.skills["example-skill"].skill_dir == EXAMPLE_SKILL_DIR


def test_skill_registration_does_not_auto_register_structured_tools():
    toolkit = create_base_toolkit(include_legacy_example_skill_support=False)
    registry = register_configured_skills(
        toolkit,
        [SkillConfig(skill_dir=EXAMPLE_SKILL_DIR)],
    )

    assert registry.list_skill_summaries()[0].structured_tools == []
    assert "run_platform_report" not in toolkit.tools
    assert "summarize_platform_callable" not in toolkit.tools
