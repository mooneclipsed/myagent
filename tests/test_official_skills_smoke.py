"""Smoke tests for bundled official example skills."""

from pathlib import Path

from src.runtime.session_runtime import get_runtime_profile

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
        "runtime_id": "bootstrap-official-skills-001",
        "skills": [
            {
                "skill_dir": str((base / name).resolve()),
                "activation_mode": "lazy",
                "expose_structured_tools": True,
            }
            for name in SELECTED_SKILLS
        ],
        "mcp_servers": [],
    }

    response = client.post("/runtimes/bootstrap", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["name"] for item in body["skills"]] == SELECTED_SKILLS
    assert all(item["activation_mode"] == "lazy" for item in body["skills"])
    assert all(item["structured_tools"] == [] for item in body["skills"])

    runtime = get_runtime_profile("bootstrap-official-skills-001")
    assert runtime is not None
    assert set(runtime.skill_registry.skills) == set(SELECTED_SKILLS)
    assert "list_available_skills" in runtime.toolkit.tools
    assert "activate_skill" in runtime.toolkit.tools
    assert "read_file" in runtime.toolkit.tools
    assert "edit_file" in runtime.toolkit.tools
    assert "run_local_shell" in runtime.toolkit.tools

    shutdown = client.post("/runtimes/bootstrap-official-skills-001/shutdown")
    assert shutdown.status_code == 200, shutdown.text
