from pathlib import Path

from agentops.application.skill_install_service import (
    ManagedSkillState,
    cleanup_managed_skills,
    prepare_remote_skills,
)
from agentops.capabilities.models import SkillDownloadConfig
from agentops.integrations.skill_api_client import SkillDownloadError, SkillInstallResult


def test_prepare_remote_skills_reinstalls_requested_skills(tmp_path):
    refreshed_dir = tmp_path / "skills" / ".managed" / "skill_1_v1"
    refreshed_dir.mkdir(parents=True)
    (refreshed_dir / "SKILL.md").write_text("user edited", encoding="utf-8")
    installed_keys = []

    def downloader(base_url, key, skill_dir, download_root):
        assert base_url == "http://skills.example"
        assert not skill_dir.exists()
        skill_id, version_id = key
        installed_keys.append(key)
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: remote-new\n---\n", encoding="utf-8")
        zip_path = download_root / f"skill_{skill_id}_v{version_id}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(b"zip")
        return SkillInstallResult(
            skill_id=skill_id,
            version_id=version_id,
            zip_path=zip_path,
            extracted_to=skill_dir,
            content_type="application/zip",
            content_disposition=None,
        )

    result = prepare_remote_skills(
        requested=[
            SkillDownloadConfig(skill_id=1, version_id=1),
            SkillDownloadConfig(skill_id=3, version_id=2),
        ],
        skills_download_url="http://skills.example",
        skills_dir=tmp_path / "skills",
        downloader=downloader,
    )

    assert installed_keys == [(1, 1), (3, 2)]
    assert (refreshed_dir / "SKILL.md").read_text(encoding="utf-8") == "---\nname: remote-new\n---\n"
    assert [summary.status for summary in result.summaries] == ["installed", "installed"]
    assert set(result.managed_skills) == {(1, 1), (3, 2)}
    assert [Path(skill.skill_dir).name for skill in result.skills] == ["skill_1_v1", "skill_3_v2"]


def test_prepare_remote_skills_keeps_request_order_after_deduplication(tmp_path):
    installed_keys = []

    def downloader(base_url, key, skill_dir, download_root):
        skill_id, version_id = key
        installed_keys.append(key)
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: remote\n---\n", encoding="utf-8")
        return SkillInstallResult(
            skill_id=skill_id,
            version_id=version_id,
            zip_path=download_root / f"skill_{skill_id}_v{version_id}.zip",
            extracted_to=skill_dir,
            content_type="application/zip",
            content_disposition=None,
        )

    prepare_remote_skills(
        requested=[
            SkillDownloadConfig(skill_id=3, version_id=2),
            SkillDownloadConfig(skill_id=1, version_id=1),
            SkillDownloadConfig(skill_id=3, version_id=2),
        ],
        skills_download_url="http://skills.example",
        skills_dir=tmp_path / "skills",
        downloader=downloader,
    )

    assert installed_keys == [(3, 2), (1, 1)]


def test_prepare_remote_skills_continues_after_install_failure(tmp_path, caplog):
    def downloader(base_url, key, skill_dir, download_root):
        skill_id, version_id = key
        if skill_id == 1:
            raise SkillDownloadError("download failed")
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: remote\n---\n", encoding="utf-8")
        return SkillInstallResult(
            skill_id=skill_id,
            version_id=version_id,
            zip_path=download_root / f"skill_{skill_id}_v{version_id}.zip",
            extracted_to=skill_dir,
            content_type="application/zip",
            content_disposition=None,
        )

    result = prepare_remote_skills(
        requested=[
            SkillDownloadConfig(skill_id=1, version_id=1),
            SkillDownloadConfig(skill_id=2, version_id=1),
        ],
        skills_download_url="http://skills.example",
        skills_dir=tmp_path / "skills",
        downloader=downloader,
    )

    assert [(item.skill_id, item.status) for item in result.summaries] == [
        (1, "failed"),
        (2, "installed"),
    ]
    assert list(result.managed_skills) == [(2, 1)]
    assert "Managed skill install failed" in caplog.text


def test_prepare_remote_skills_reports_missing_download_url_without_stopping_all_items(tmp_path):
    result = prepare_remote_skills(
        requested=[
            SkillDownloadConfig(skill_id=1, version_id=1),
            SkillDownloadConfig(skill_id=2, version_id=1),
        ],
        skills_download_url=None,
        skills_dir=tmp_path / "skills",
    )

    assert [(item.skill_id, item.status) for item in result.summaries] == [
        (1, "failed"),
        (2, "failed"),
    ]
    assert result.skills == []


def test_cleanup_managed_skills_deletes_directory(tmp_path):
    skill_dir = tmp_path / "skills" / ".managed" / "skill_1_v1"
    skill_dir.mkdir(parents=True)

    cleanup_managed_skills([
        ManagedSkillState(skill_id=1, version_id=1, skill_dir=str(skill_dir)),
    ])

    assert not skill_dir.exists()
