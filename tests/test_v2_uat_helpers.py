"""Tests for v2 UAT request helpers."""

from tests.uat._helpers import _v2_runtime_payload


def test_uat_helper_converts_legacy_bootstrap_payload_to_v2_capabilities() -> None:
    payload = _v2_runtime_payload(
        "session-1",
        {
            "tools": [{"name": "read_file"}],
            "mcp_servers": [
                {
                    "name": "time",
                    "type": "stdio",
                    "command": "python",
                    "args": ["server.py"],
                }
            ],
            "skills": [{"skill_dir": "/repo/skills/hello"}],
        },
    )

    assert payload == {
        "runtime_id": "session-1",
        "framework": "agentscope",
        "capabilities": [
            {"type": "tool", "name": "read_file", "config": {"tool_name": "read"}},
            {
                "type": "mcp",
                "name": "time",
                "config": {
                    "transport": "stdio",
                    "command": "python",
                    "args": ["server.py"],
                    "env": {},
                    "cwd": None,
                    "url": None,
                    "headers": {},
                    "timeout": 30,
                },
            },
            {"type": "skill", "name": "hello", "config": {"path": "/repo/skills/hello"}},
        ],
    }


def test_uat_helper_maps_project_local_tools_to_v2_function_tools() -> None:
    payload = _v2_runtime_payload(
        "session-1",
        {
            "tools": [{"name": "get_weather"}, {"name": "calculate"}],
        },
    )

    assert payload["capabilities"] == [
        {"type": "tool", "name": "get_weather", "config": {"tool_name": "local:get_weather"}},
        {"type": "tool", "name": "calculate", "config": {"tool_name": "local:calculate"}},
    ]
