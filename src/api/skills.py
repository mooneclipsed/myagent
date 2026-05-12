"""HTTP endpoints for remote skill installation."""

from fastapi import HTTPException
from agentscope_runtime.engine import AgentApp
from pydantic import BaseModel, ConfigDict

from ..integrations.skill_api_client import SkillDownloadError, download_and_extract_skill_version


class SkillInstallResponse(BaseModel):
    """Response returned after installing a remote skill version."""

    model_config = ConfigDict(extra="forbid")

    skill_id: int
    version_id: int
    status: str = "installed"
    zip_path: str
    extracted_to: str


def register_skill_routes(app: AgentApp) -> None:
    """Register skill download and install endpoints on the AgentApp."""

    @app.post(
        "/api/v1/skills/{skill_id}/versions/{version_id}/install",
        response_model=SkillInstallResponse,
        tags=["skill-api"],
    )
    async def install_skill_version(skill_id: int, version_id: int) -> SkillInstallResponse:
        if skill_id <= 0:
            raise HTTPException(status_code=422, detail="skill_id must be a positive integer")
        if version_id <= 0:
            raise HTTPException(status_code=422, detail="version_id must be a positive integer")

        try:
            result = download_and_extract_skill_version(skill_id, version_id)
        except SkillDownloadError as exc:
            detail = str(exc)
            status_code = 404 if detail in {
                "Version not found",
                "Version not found for this skill",
                "Skill version files not found",
                "Skill version not found",
            } else 502
            raise HTTPException(status_code=status_code, detail=detail) from exc

        return SkillInstallResponse(
            skill_id=result.skill_id,
            version_id=result.version_id,
            zip_path=str(result.zip_path),
            extracted_to=str(result.extracted_to),
        )
