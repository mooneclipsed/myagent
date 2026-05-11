from pathlib import Path
from zipfile import ZipFile

import pytest
import requests

from src.integrations.skill_api_client import (
    SkillApiClient,
    SkillDownloadError,
    download_and_extract_skill_version,
    extract_skill_zip,
)


class FakeSession:
    def __init__(self, response: requests.Response):
        self.response = response
        self.requests = []
        self.closed = False

    def get(self, url: str, timeout: float):
        self.requests.append((url, timeout))
        return self.response

    def close(self):
        self.closed = True


def make_response(
    status_code: int,
    *,
    content: bytes = b"",
    headers: dict[str, str] | None = None,
) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = content
    response.headers.update(headers or {})
    response.url = "http://skills.example/api/v1/skills/1/versions/3/download"
    return response


def test_download_skill_version_writes_zip(tmp_path):
    response = make_response(
        200,
        content=b"zip-bytes",
        headers={
            "content-type": "application/zip",
            "content-disposition": "attachment; filename=skill_1_v3.zip",
        },
    )
    session = FakeSession(response)
    client = SkillApiClient("http://skills.example/", client=session)

    result = client.download_skill_version(1, 3, tmp_path)

    assert session.requests == [
        ("http://skills.example/api/v1/skills/1/versions/3/download", 60)
    ]
    assert result.skill_id == 1
    assert result.version_id == 3
    assert result.path == Path(tmp_path) / "skill_1_v3.zip"
    assert result.path.read_bytes() == b"zip-bytes"
    assert result.content_type == "application/zip"
    assert result.content_disposition == "attachment; filename=skill_1_v3.zip"


def test_download_skill_version_raises_business_404(tmp_path):
    response = make_response(404, content=b'{"detail": "Version not found for this skill"}')
    client = SkillApiClient("http://skills.example", client=FakeSession(response))

    with pytest.raises(SkillDownloadError, match="Version not found for this skill"):
        client.download_skill_version(1, 3, tmp_path)


def test_download_skill_version_rejects_non_zip(tmp_path):
    response = make_response(200, content=b"{}", headers={"content-type": "application/json"})
    client = SkillApiClient("http://skills.example", client=FakeSession(response))

    with pytest.raises(SkillDownloadError, match="Unexpected content type"):
        client.download_skill_version(1, 3, tmp_path)


def test_extract_skill_zip_into_skills_dir(tmp_path):
    zip_path = tmp_path / "skill.zip"
    skills_dir = tmp_path / "skills"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("hello/SKILL.md", "---\nname: hello\n---\n")
        archive.writestr("hello/scripts/run.py", "print('ok')\n")

    extracted_to = extract_skill_zip(zip_path, skills_dir)

    assert extracted_to == skills_dir
    assert (skills_dir / "hello" / "SKILL.md").read_text() == "---\nname: hello\n---\n"
    assert (skills_dir / "hello" / "scripts" / "run.py").read_text() == "print('ok')\n"


def test_download_and_extract_skill_version(tmp_path):
    zip_path = tmp_path / "source.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("remote_skill/SKILL.md", "---\nname: remote-skill\n---\n")

    response = make_response(
        200,
        content=zip_path.read_bytes(),
        headers={"content-type": "application/zip"},
    )
    skills_dir = tmp_path / "skills"
    client = SkillApiClient("http://skills.example", client=FakeSession(response))

    result = client.download_and_extract_skill_version(1, 3, skills_dir=skills_dir)

    assert result.zip_path == skills_dir / ".downloads" / "skill_1_v3.zip"
    assert result.extracted_to == skills_dir
    assert result.zip_path.is_file()
    assert (skills_dir / "remote_skill" / "SKILL.md").is_file()


def test_download_and_extract_skill_version_function(tmp_path, monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, base_url: str, timeout: float):
            captured["base_url"] = base_url
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def download_and_extract_skill_version(
            self,
            skill_id: int,
            version_id: int,
            *,
            skills_dir: str | Path,
            download_dir: str | Path | None,
        ):
            captured["args"] = (skill_id, version_id, skills_dir, download_dir)
            return "installed"

    monkeypatch.setattr("src.integrations.skill_api_client.SkillApiClient", FakeClient)

    result = download_and_extract_skill_version(
        1,
        3,
        base_url="http://skills.example",
        skills_dir=tmp_path / "skills",
        download_dir=tmp_path / "downloads",
        timeout=12,
    )

    assert result == "installed"
    assert captured == {
        "base_url": "http://skills.example",
        "timeout": 12,
        "args": (1, 3, tmp_path / "skills", tmp_path / "downloads"),
    }


def test_download_and_extract_skill_version_reads_base_url_from_env(tmp_path, monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, base_url: str, timeout: float):
            captured["base_url"] = base_url
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def download_and_extract_skill_version(
            self,
            skill_id: int,
            version_id: int,
            *,
            skills_dir: str | Path,
            download_dir: str | Path | None,
        ):
            captured["args"] = (skill_id, version_id, skills_dir, download_dir)
            return "installed"

    monkeypatch.setenv("SKILLS_DOWNLOAD_URL", "http://env-skills.example")
    monkeypatch.setattr("src.integrations.skill_api_client.SkillApiClient", FakeClient)

    result = download_and_extract_skill_version(1, 3, skills_dir=tmp_path / "skills")

    assert result == "installed"
    assert captured["base_url"] == "http://env-skills.example"


def test_download_and_extract_skill_version_requires_base_url(monkeypatch):
    monkeypatch.delenv("SKILLS_DOWNLOAD_URL", raising=False)

    with pytest.raises(SkillDownloadError, match="SKILLS_DOWNLOAD_URL is not configured"):
        download_and_extract_skill_version(1, 3)
