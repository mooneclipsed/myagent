"""Explicit framework adapter registry."""

from __future__ import annotations

from dataclasses import dataclass


class UnknownFrameworkError(ValueError):
    """Raised when an init request names an unknown framework."""


@dataclass(frozen=True)
class FrameworkDescriptor:
    """Description of a registered framework adapter."""

    name: str
    adapter_package: str


_FRAMEWORKS: dict[str, FrameworkDescriptor] = {
    "agentscope": FrameworkDescriptor(
        name="agentscope",
        adapter_package="agentops.frameworks.agentscope_v2",
    ),
}


def resolve_framework(framework: str) -> FrameworkDescriptor:
    """Resolve a public framework name to an adapter descriptor."""
    try:
        return _FRAMEWORKS[framework]
    except KeyError as exc:
        raise UnknownFrameworkError(f"Framework '{framework}' does not exist.") from exc


def list_frameworks() -> list[str]:
    """Return registered public framework names."""
    return sorted(_FRAMEWORKS)

