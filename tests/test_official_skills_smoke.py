"""Smoke tests for bundled official example skills."""

import asyncio
from pathlib import Path

from agentops.api.schemas import RuntimeInitRequest
from agentops.api.v2 import V2RuntimeApiService
from agentops.config.settings import Settings

SELECTED_SKILLS = [
    "doc-coauthoring",
    "docx",
    "pdf",
    "xlsx",
    "frontend-design",
    "theme-factory",
    "webapp-testing",
]


def test_bootstrap_selected_official_skills() -> None:
    base = Path(__file__).resolve().parents[1] / "skills"
    service = V2RuntimeApiService(settings=Settings(
        model_name="test-model",
        model_api_key="test-key",
        model_base_url="http://localhost:9999/v1",
    ))
    request = RuntimeInitRequest(
        runtime_id="official-skills",
        capabilities=[
            {
                "type": "skill",
                "name": name,
                "config": {"path": str((base / name).resolve())},
            }
            for name in SELECTED_SKILLS
        ],
    )

    response = asyncio.run(service.initialize(request))

    assert [item.name for item in response.capabilities] == SELECTED_SKILLS
    resources = service.builder.get_resources("official-skills")
    assert resources is not None
    loaders = resources.toolkit.tool_groups[0].skills_or_loaders
    assert {Path(loader.directory).name for loader in loaders} == set(SELECTED_SKILLS)
    asyncio.run(service.close())
