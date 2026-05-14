"""Application service for managed remote skill installation."""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..capabilities.models import (
    SkillConfig,
    SkillDownloadConfig,
    SkillDownloadSummary,
)
from ..integrations.skill_api_client import (
    DEFAULT_SKILLS_DIR,
    SkillApiClient,
    SkillDownloadError,
    SkillInstallResult,
    _resolve_base_url,
)

logger = logging.getLogger(__name__)


ManagedSkillKey = tuple[int, int]


@dataclass
class ManagedSkillState:
    """Persisted state for one installed remote skill version."""

    skill_id: int
    version_id: int
    skill_dir: str
    zip_path: str | None = None


@dataclass
class ManagedSkillSyncResult:
    """Result of syncing requested remote skills into local managed storage."""

    skills: list[SkillConfig] = field(default_factory=list)
    summaries: list[SkillDownloadSummary] = field(default_factory=list)
    managed_skills: dict[ManagedSkillKey, ManagedSkillState] = field(default_factory=dict)


Downloader = Callable[[str, ManagedSkillKey, Path, Path], SkillInstallResult]


def prepare_remote_skills(
    *,
    requested: list[SkillDownloadConfig],
    skills_download_url: str | None,
    skills_dir: str | Path = DEFAULT_SKILLS_DIR,
    downloader: Downloader | None = None,
) -> ManagedSkillSyncResult:
    """Prepare remote skill downloads for a runtime initialization or reload.

    Converts requested skill/version pairs into local SkillConfig entries by reinstalling
    each requested version. Individual download failures are reported in summaries
    without blocking other requested skills from being prepared.
    """
    result = ManagedSkillSyncResult()
    requested_keys = _deduplicate_skill_keys(requested)
    target_skills_dir = Path(skills_dir)
    managed_root = target_skills_dir / ".managed"
    download_root = target_skills_dir / ".downloads"

    if requested_keys:
        try:
            base_url = _resolve_base_url(skills_download_url)
        except SkillDownloadError as exc:
            for key in requested_keys:
                _append_failure(result, key, exc)
            return result
        for key in requested_keys:
            install = _install_managed_skill(
                base_url=base_url,
                key=key,
                managed_root=managed_root,
                download_root=download_root,
                downloader=downloader,
            )
            if isinstance(install, SkillDownloadSummary):
                result.summaries.append(install)
                continue
            skill_dir = _resolve_skill_dir(install.extracted_to)
            state = ManagedSkillState(
                skill_id=key[0],
                version_id=key[1],
                skill_dir=str(skill_dir),
                zip_path=str(install.zip_path),
            )
            result.managed_skills[key] = state
            result.skills.append(SkillConfig(skill_dir=state.skill_dir))
            result.summaries.append(
                SkillDownloadSummary(
                    skill_id=key[0],
                    version_id=key[1],
                    status="installed",
                    skill_dir=state.skill_dir,
                    zip_path=state.zip_path,
                ),
            )

    return result


def cleanup_managed_skills(states: list[ManagedSkillState]) -> None:
    """Delete managed skill directories that are no longer referenced by the active runtime."""
    for state in states:
        path = Path(state.skill_dir)
        try:
            if path.exists():
                shutil.rmtree(path)
        except Exception as exc:
            logger.warning(
                "Managed skill cleanup failed: skill_id=%s version_id=%s skill_dir=%s error=%s",
                state.skill_id,
                state.version_id,
                state.skill_dir,
                exc,
            )


def _install_managed_skill(
    *,
    base_url: str,
    key: ManagedSkillKey,
    managed_root: Path,
    download_root: Path,
    downloader: Downloader | None,
) -> SkillInstallResult | SkillDownloadSummary:
    skill_id, version_id = key
    skill_dir = managed_root / f"skill_{skill_id}_v{version_id}"
    try:
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        active_downloader = downloader or _download_with_client
        install = active_downloader(base_url, key, skill_dir, download_root)
        _validate_extracted_skill(skill_dir)
        return install
    except Exception as exc:
        if skill_dir.exists():
            shutil.rmtree(skill_dir, ignore_errors=True)
        logger.warning(
            "Managed skill install failed: skill_id=%s version_id=%s error=%s",
            skill_id,
            version_id,
            exc,
        )
        return SkillDownloadSummary(
            skill_id=skill_id,
            version_id=version_id,
            status="failed",
            skill_dir=str(skill_dir),
            error=str(exc),
        )


def _download_with_client(
    base_url: str,
    key: ManagedSkillKey,
    skill_dir: Path,
    download_root: Path,
) -> SkillInstallResult:
    skill_id, version_id = key
    with SkillApiClient(base_url) as client:
        return client.download_and_extract_skill_version(
            skill_id,
            version_id,
            skills_dir=skill_dir,
            download_dir=download_root,
        )


def _validate_extracted_skill(skill_dir: Path) -> None:
    if (skill_dir / "SKILL.md").is_file():
        return
    nested = [path for path in skill_dir.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()]
    if len(nested) == 1:
        return
    raise SkillDownloadError(f"Downloaded skill is missing SKILL.md under {skill_dir}")


def _resolve_skill_dir(extracted_to: Path) -> Path:
    extracted = Path(extracted_to)
    if (extracted / "SKILL.md").is_file():
        return extracted
    nested = [path for path in extracted.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()]
    if len(nested) == 1:
        return nested[0]
    return extracted


def _deduplicate_skill_keys(requested: list[SkillDownloadConfig]) -> list[ManagedSkillKey]:
    keys: list[ManagedSkillKey] = []
    seen: set[ManagedSkillKey] = set()
    for item in requested:
        key = (item.skill_id, item.version_id)
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def _append_failure(result: ManagedSkillSyncResult, key: ManagedSkillKey, exc: Exception) -> None:
    logger.warning(
        "Managed skill download configuration failed: skill_id=%s version_id=%s error=%s",
        key[0],
        key[1],
        exc,
    )
    result.summaries.append(
        SkillDownloadSummary(
            skill_id=key[0],
            version_id=key[1],
            status="failed",
            error=str(exc),
        ),
    )
