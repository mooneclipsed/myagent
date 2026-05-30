"""Terminal branding shown when the application starts."""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PACKAGE_NAME = "myagent"
UNKNOWN_VERSION = "unknown"

LOGO = r"""
    ___                    __  ____          
   /   | ____ ____  ____  / /_/ __ \____  _____
  / /| |/ __ `/ _ \/ __ \/ __/ / / / __ \/ ___/
 / ___ / /_/ /  __/ / / / /_/ /_/ / /_/ (__  ) 
/_/  |_\__, /\___/_/ /_/\__/\____/ .___/____/  
      /____/                    /_/            
"""


def get_app_version() -> str:
    """Return the installed application version."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return _read_pyproject_version()


def build_startup_banner() -> str:
    """Return the startup banner printed by the server process."""
    return f"{LOGO}\nAgentOps\n{PACKAGE_NAME} v{get_app_version()}"


def _read_pyproject_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject_path.exists():
        return UNKNOWN_VERSION

    with pyproject_path.open("rb") as pyproject_file:
        project_config = tomllib.load(pyproject_file)

    version_value = project_config.get("project", {}).get("version")
    if not isinstance(version_value, str):
        return UNKNOWN_VERSION
    return version_value
