"""Smoke tests for bundled official example skills."""

from pathlib import Path

from agentops.application.runtime_service import get_active_runtime_profile

SELECTED_SKILLS = [
    "doc-coauthoring",
    "docx",
    "pdf",
    "xlsx",
    "frontend-design",
    "theme-factory",
    "webapp-testing",
]


def test_bootstrap_selected_official_skills(client):
    base = Path(__file__).resolve().parents[1] / "skills"
    payload = {
        "skills": [
            {
                "skill_dir": str((base / name).resolve()),
            }
            for name in SELECTED_SKILLS
        ],
        "mcp_servers": [],
    }

    response = client.post("/runtimes/init", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["name"] for item in body["skills"]] == SELECTED_SKILLS
    assert all(item["structured_tools"] == [] for item in body["skills"])

    runtime = get_active_runtime_profile()
    assert runtime is not None
    assert set(runtime.skill_registry.skills) == set(SELECTED_SKILLS)
    assert "read_file" in runtime.toolkit.tools
    assert "edit_file" in runtime.toolkit.tools
    assert "run_local_shell" in runtime.toolkit.tools
