from pathlib import Path
from unittest.mock import patch

from src.integrations.skill_api_client import SkillDownloadError, SkillInstallResult


def test_install_skill_version_endpoint(client):
    result = SkillInstallResult(
        skill_id=1,
        version_id=3,
        zip_path=Path("skills/.downloads/skill_1_v3.zip"),
        extracted_to=Path("skills"),
        content_type="application/zip",
        content_disposition="attachment; filename=skill_1_v3.zip",
    )

    with patch("src.api.skills.download_and_extract_skill_version", return_value=result) as install:
        response = client.post("/api/v1/skills/1/versions/3/install")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "skill_id": 1,
        "version_id": 3,
        "status": "installed",
        "zip_path": "skills/.downloads/skill_1_v3.zip",
        "extracted_to": "skills",
    }
    install.assert_called_once_with(1, 3)


def test_install_skill_version_endpoint_maps_remote_404(client):
    with patch(
        "src.api.skills.download_and_extract_skill_version",
        side_effect=SkillDownloadError("Version not found for this skill"),
    ):
        response = client.post("/api/v1/skills/1/versions/3/install")

    assert response.status_code == 404
    assert response.json()["detail"] == "Version not found for this skill"


def test_install_skill_version_endpoint_maps_download_failure(client):
    with patch(
        "src.api.skills.download_and_extract_skill_version",
        side_effect=SkillDownloadError("SKILLS_DOWNLOAD_URL is not configured"),
    ):
        response = client.post("/api/v1/skills/1/versions/3/install")

    assert response.status_code == 502
    assert response.json()["detail"] == "SKILLS_DOWNLOAD_URL is not configured"


def test_install_skill_version_endpoint_rejects_invalid_ids(client):
    response = client.post("/api/v1/skills/0/versions/3/install")

    assert response.status_code == 422
    assert response.json()["detail"] == "skill_id must be a positive integer"
