"""Application service for managed remote skill installation."""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..capabilities.schemas import (
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
    state: dict[ManagedSkillKey, ManagedSkillState] = field(default_factory=dict)
    remove_after_runtime_swap: list[ManagedSkillState] = field(default_factory=list)


Downloader = Callable[[str, ManagedSkillKey, Path, Path], SkillInstallResult]


def prepare_remote_skills(
    *,
    requested: list[SkillDownloadConfig],
    skills_download_url: str | None,
    previous_state: dict[ManagedSkillKey, ManagedSkillState] | None = None,
    skills_dir: str | Path = DEFAULT_SKILLS_DIR,
    downloader: Downloader | None = None,
) -> ManagedSkillSyncResult:
    """Prepare remote skill downloads for a runtime initialization or reload.

    Converts requested skill/version pairs into local SkillConfig entries by reusing
    already-installed managed skills, downloading missing versions, and marking
    unrequested previous versions for cleanup after a successful runtime swap.
    Individual download failures are reported in summaries without blocking other
    requested skills from being prepared.
    """
    previous = previous_state or {}
    requested_keys = _filter_duplicate_skill_keys(requested)
    requested_set = set(requested_keys)
    previous_set = set(previous)

    keep = requested_set & previous_set
    add = requested_set - previous_set
    remove = previous_set - requested_set

    result = ManagedSkillSyncResult()
    target_skills_dir = Path(skills_dir)
    managed_root = target_skills_dir / ".managed"
    download_root = target_skills_dir / ".downloads"

    for key in requested_keys:
        if key in keep:
            state = previous[key]
            result.state[key] = state
            result.skills.append(SkillConfig(skill_dir=state.skill_dir))
            result.summaries.append(
                SkillDownloadSummary(
                    skill_id=key[0],
                    version_id=key[1],
                    status="kept",
                    skill_dir=state.skill_dir,
                    zip_path=state.zip_path,
                ),
            )

    if add:
        try:
            base_url = _resolve_base_url(skills_download_url)
        except SkillDownloadError as exc:
            for key in sorted(add, key=_sort_key):
                _append_failure(result, key, exc)
            add = set()
        for key in sorted(add, key=_sort_key):
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
            result.state[key] = state
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

    for key in sorted(remove, key=_sort_key):
        result.remove_after_runtime_swap.append(previous[key])
        result.summaries.append(
            SkillDownloadSummary(
                skill_id=key[0],
                version_id=key[1],
                status="removed",
                skill_dir=previous[key].skill_dir,
                zip_path=previous[key].zip_path,
            ),
        )

    return result


def cleanup_removed_managed_skills(states: list[ManagedSkillState]) -> None:
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


def _filter_duplicate_skill_keys(requested: list[SkillDownloadConfig]) -> list[ManagedSkillKey]:
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


def _sort_key(key: ManagedSkillKey) -> tuple[int, int]:
    return key
