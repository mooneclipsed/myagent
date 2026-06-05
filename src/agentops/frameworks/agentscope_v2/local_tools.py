"""AgentScope v2 local tool bridge."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentscope.permission import PermissionBehavior, PermissionDecision
from agentscope.tool import FunctionTool

from agentops.tools.examples import (
    calculate,
    get_weather,
    run_platform_report,
    summarize_platform_callable,
)


LOCAL_TOOL_REGISTRY: dict[str, Callable[..., object]] = {
    "get_weather": get_weather,
    "calculate": calculate,
    "run_platform_report": run_platform_report,
    "summarize_platform_callable": summarize_platform_callable,
}


class LocalFunctionTool(FunctionTool):
    """Auto-allowed deterministic project-local function tool."""

    async def check_permissions(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> PermissionDecision:
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message=f"Project local tool '{self.name}' is allowed.",
        )


def build_local_function_tool(name: str) -> LocalFunctionTool:
    """Build an AgentScope v2 function tool for a registered local callable."""
    try:
        func = LOCAL_TOOL_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown local function tool: {name}") from exc
    return LocalFunctionTool(func, name=name, is_read_only=True)
