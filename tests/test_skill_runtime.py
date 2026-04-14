"""Tests for dynamic skill runtime helpers and activation flow."""

from pathlib import Path

from agentscope.tool import Toolkit, ToolResponse

from src.agent.skill_runtime import (
    activate_skill_factory,
    build_skill_group_name,
    load_skill_manifest,
    make_python_file_runner,
    register_configured_skills,
    register_local_runtime_tools,
)
from src.core.config import SkillConfig
from src.tools import create_base_toolkit


EXAMPLE_SKILL_DIR = str(
    (Path(__file__).resolve().parents[1] / "skills" / "example_skill").resolve()
)


def test_load_skill_manifest_reads_scripts_from_frontmatter():
    manifest = load_skill_manifest(EXAMPLE_SKILL_DIR)

    assert manifest.name == "example-skill"
    assert len(manifest.scripts) == 2
    assert {script.name for script in manifest.scripts} == {
        "run_platform_report",
        "summarize_platform_callable",
    }


def test_register_configured_skills_creates_lazy_group_and_catalog_tools():
    toolkit = create_base_toolkit(include_legacy_example_skill_support=False)
    register_local_runtime_tools(toolkit)
    registry = register_configured_skills(
        toolkit,
        [SkillConfig(skill_dir=EXAMPLE_SKILL_DIR, activation_mode="lazy")],
    )

    group_name = build_skill_group_name("example-skill")
    assert group_name in toolkit.groups
    assert toolkit.groups[group_name].active is False
    assert "list_available_skills" in toolkit.tools
    assert "activate_skill" in toolkit.tools
    assert "run_platform_report" in toolkit.tools
    assert "summarize_platform_callable" in toolkit.tools
    assert "example-skill" in registry.skills


def test_activate_skill_preserves_existing_groups_and_marks_skill_active():
    toolkit = Toolkit()
    toolkit.create_tool_group("local_shell", description="shell", active=True)
    registry = register_configured_skills(
        toolkit,
        [SkillConfig(skill_dir=EXAMPLE_SKILL_DIR, activation_mode="lazy")],
    )

    activate_skill = activate_skill_factory(toolkit, registry)
    response = activate_skill("example-skill")

    assert isinstance(response, ToolResponse)
    assert registry.skills["example-skill"].activated is True
    assert toolkit.groups[build_skill_group_name("example-skill")].active is True
    assert toolkit.groups["local_shell"].active is True
    assert "Structured tools now available" in response.content[0]["text"]


def test_python_file_runner_uses_declared_script_and_returns_output():
    manifest = load_skill_manifest(EXAMPLE_SKILL_DIR)
    script = next(item for item in manifest.scripts if item.kind == "python_file")
    runner = make_python_file_runner(manifest.skill_dir, script)

    response = runner()

    assert isinstance(response, ToolResponse)
    assert "EXAMPLE_SKILL_SCRIPT_OK" in response.content[0]["text"]


def test_python_callable_runner_returns_tool_response():
    toolkit = create_base_toolkit(include_legacy_example_skill_support=False)
    registry = register_configured_skills(
        toolkit,
        [SkillConfig(skill_dir=EXAMPLE_SKILL_DIR, activation_mode="eager")],
    )

    callable_tool = toolkit.tools["summarize_platform_callable"].original_func
    response = callable_tool()

    assert isinstance(response, ToolResponse)
    assert "mode=session-owned-skill-runtime" in response.content[0]["text"]
