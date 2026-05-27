"""HTTP client helpers for remote skill APIs."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import quote
import zipfile

import requests

DEFAULT_SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
SKILLS_DOWNLOAD_URL = "SKILLS_DOWNLOAD_URL"


class SkillDownloadError(RuntimeError):
    """Raised when a remote skill version cannot be downloaded."""


@dataclass(frozen=True)
class SkillDownloadResult:
    """Local artifact created from a remote skill version download."""

    skill_id: int
    version_id: int
    path: Path
    content_type: str | None
    content_disposition: str | None


@dataclass(frozen=True)
class SkillInstallResult:
    """Local artifacts created from a remote skill version install."""

    zip_path: Path
    extracted_to: Path


class SkillApiClient:
    """Small wrapper around the remote skill service."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 300,
        client: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client
        if self._client is not None:
            self._client.trust_env = False
        self._owns_client = client is None

    def __enter__(self) -> "SkillApiClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    @property
    def client(self) -> requests.Session:
        if self._client is None:
            self._client = requests.Session()
            self._client.trust_env = False
        return self._client

    def download_skill_version(
        self,
        skill_id: int,
        version_id: int,
        output_dir: str | Path,
    ) -> SkillDownloadResult:
        """Download a skill version ZIP file into output_dir."""
        if skill_id <= 0:
            raise ValueError("skill_id must be a positive integer")
        if version_id <= 0:
            raise ValueError("version_id must be a positive integer")

        url = (
            f"{self.base_url}/api/v1/skills/{quote(str(skill_id))}"
            f"/versions/{quote(str(version_id))}/download"
        )
        try:
            response = self.client.get(url, timeout=self.timeout, verify=False)
        except requests.RequestException as exc:
            message = _format_download_error(
                skill_id=skill_id,
                version_id=version_id,
                url=url,
                reason="request failed",
                detail=str(exc),
            )
            raise SkillDownloadError(message) from exc

        if response.status_code == 404:
            detail = _extract_error_detail(response)
            message = _format_download_error(
                skill_id=skill_id,
                version_id=version_id,
                url=url,
                reason="skill version not found",
                status_code=response.status_code,
                detail=detail or "Skill version not found",
            )
            raise SkillDownloadError(message)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = _extract_error_detail(response)
            message = _format_download_error(
                skill_id=skill_id,
                version_id=version_id,
                url=url,
                reason="remote service returned an error",
                status_code=response.status_code,
                detail=detail or str(exc),
            )
            raise SkillDownloadError(message) from exc

        content_type = response.headers.get("content-type")
        if content_type and "application/zip" not in content_type.lower():
            message = _format_download_error(
                skill_id=skill_id,
                version_id=version_id,
                url=url,
                reason="unexpected response content type",
                status_code=response.status_code,
                detail=f"Expected application/zip, got {content_type}",
            )
            raise SkillDownloadError(message)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        zip_path = output_path / f"skill_{skill_id}_v{version_id}.zip"
        zip_path.write_bytes(response.content)

        return SkillDownloadResult(
            skill_id=skill_id,
            version_id=version_id,
            path=zip_path,
            content_type=content_type,
            content_disposition=response.headers.get("content-disposition"),
        )

    def download_and_extract_skill_version(
        self,
        skill_id: int,
        version_id: int,
        *,
        skills_dir: str | Path = DEFAULT_SKILLS_DIR,
        download_dir: str | Path | None = None,
    ) -> SkillInstallResult:
        """Download a skill version ZIP and extract it into skills_dir."""
        target_skills_dir = Path(skills_dir)
        archive_dir = Path(download_dir) if download_dir is not None else target_skills_dir / ".downloads"
        download = self.download_skill_version(skill_id, version_id, archive_dir)
        extracted_to = extract_skill_zip(download.path, target_skills_dir)
        return SkillInstallResult(
            zip_path=download.path,
            extracted_to=extracted_to,
        )


def extract_skill_zip(
    zip_path: str | Path,
    skills_dir: str | Path = DEFAULT_SKILLS_DIR,
) -> Path:
    """Extract a skill ZIP archive into the local skills directory."""
    target_skills_dir = Path(skills_dir).resolve()
    target_skills_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            destination = (target_skills_dir / member.filename).resolve()
            if destination != target_skills_dir and target_skills_dir not in destination.parents:
                raise SkillDownloadError(f"Unsafe skill archive path: {member.filename}")
        archive.extractall(target_skills_dir)
    return target_skills_dir


def download_and_extract_skill_version(
    skill_id: int,
    version_id: int,
    *,
    base_url: str | None = None,
    skills_dir: str | Path = DEFAULT_SKILLS_DIR,
    download_dir: str | Path | None = None,
    timeout: float = 60,
) -> SkillInstallResult:
    """Convenience function for installing a remote skill version into ./skills."""
    with SkillApiClient(_require_base_url(base_url), timeout=timeout) as client:
        return client.download_and_extract_skill_version(
            skill_id,
            version_id,
            skills_dir=skills_dir,
            download_dir=download_dir,
        )


def _require_base_url(base_url: str | None = None) -> str:
    resolved = base_url or os.getenv(SKILLS_DOWNLOAD_URL)
    if not resolved:
        raise SkillDownloadError(f"{SKILLS_DOWNLOAD_URL} is not configured")
    return resolved


def _extract_error_detail(response: requests.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        text = response.text.strip()
        return text or None

    if isinstance(body, dict):
        detail = body.get("detail") or body.get("message") or body.get("error")
        if isinstance(detail, str):
            return detail
    return None


def _format_download_error(
    *,
    skill_id: int,
    version_id: int,
    url: str,
    reason: str,
    status_code: int | None = None,
    detail: str | None = None,
) -> str:
    message = (
        f"Skill version download failed: skill_id={skill_id} "
        f"version_id={version_id} reason={reason}"
    )
    if status_code is not None:
        message += f" status_code={status_code}"
    message += f" url={url}"
    if detail:
        message += f" detail={detail}"
    message += (
        ". Check skills_download_url, skill_id/version_id, and the remote skill "
        "service file storage."
    )
    return message
