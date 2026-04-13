"""Example tool functions for end-to-end capability verification.

Per D-03: Simple, deterministic tools callable through streaming chat
without external dependencies. All functions return ToolResponse with
TextBlock content (Pitfall 1 from RESEARCH.md).
"""

from pathlib import Path
import subprocess
import sys

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse


_SKILL_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "skills" / "example_skill" / "platform_report.py"
)


def get_weather(city: str) -> ToolResponse:
    """Get the current weather for a city.

    Args:
        city (str): The name of the city to get weather for.

    Returns:
        ToolResponse: The weather information for the specified city.
    """
    # Deterministic mock — no external API calls
    return ToolResponse(
        content=[TextBlock(type="text", text=f"The weather in {city} is sunny, 22C.")],
    )


def calculate(operation: str, a: float, b: float) -> ToolResponse:
    """Perform a basic arithmetic calculation.

    Args:
        operation (str): The operation to perform. One of: add, subtract, multiply, divide.
        a (float): The first operand.
        b (float): The second operand.

    Returns:
        ToolResponse: The result of the calculation.
    """
    # Deterministic — no external dependencies
    ops = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else "Error: division by zero",
    }
    if operation not in ops:
        result = f"Error: unknown operation '{operation}'"
    else:
        result = f"{ops[operation](a, b)}"
    return ToolResponse(content=[TextBlock(type="text", text=result)])


def run_platform_report() -> ToolResponse:
    """Run the bundled example skill script and return its raw report output.

    Returns:
        ToolResponse: Raw stdout emitted by the example skill script.
    """
    completed = subprocess.run(
        [sys.executable, str(_SKILL_SCRIPT_PATH)],
        capture_output=True,
        text=True,
        check=True,
    )
    return ToolResponse(
        content=[TextBlock(type="text", text=completed.stdout.strip())],
    )
