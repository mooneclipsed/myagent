"""Smoke tests for bundled official example skills."""

from pathlib import Path

from src.agent.session_runtime import get_session_runtime

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
        "session_id": "bootstrap-official-skills-001",
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

    response = client.post("/sessions/bootstrap", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["name"] for item in body["skills"]] == SELECTED_SKILLS
    assert all(item["activation_mode"] == "lazy" for item in body["skills"])
    assert all(item["structured_tools"] == [] for item in body["skills"])

    runtime = get_session_runtime("bootstrap-official-skills-001")
    assert runtime is not None
    assert set(runtime.skill_registry.skills) == set(SELECTED_SKILLS)
    assert "list_available_skills" in runtime.toolkit.tools
    assert "activate_skill" in runtime.toolkit.tools
    assert "read_file" in runtime.toolkit.tools
    assert "edit_file" in runtime.toolkit.tools
    assert "run_local_shell" in runtime.toolkit.tools

    shutdown = client.post("/sessions/bootstrap-official-skills-001/shutdown")
    assert shutdown.status_code == 200, shutdown.text
