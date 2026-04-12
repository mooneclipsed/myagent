# AgentScope Skill/Tool/MCP Validation Platform

A FastAPI-based agent testing shell for validating skill calls, tool calls, MCP calls, and session persistence with `agentscope-runtime`.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- An OpenAI-compatible API key (configured via `.env`)

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your API configuration:
# MODEL_PROVIDER=openai
# MODEL_NAME=gpt-4o
# MODEL_API_KEY=your-api-key
# MODEL_BASE_URL=https://api.openai.com/v1
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Start the service

```bash
bash scripts/run_service.sh
```

The service runs at `http://127.0.0.1:8000`.

## Running Demos

Each demo script exercises a specific capability class. All scripts exit with code 0 on success and non-zero on failure.

**Prerequisite:** Start the service before running demos.

### Tool Call Demo

```bash
uv run scripts/demos/demo_tool.py
```

Triggers the `get_weather` tool and verifies the response contains weather data.

### Skill Demo

```bash
uv run scripts/demos/demo_skill.py
```

Verifies the agent uses skill-injected context about the platform in its response.

### MCP Demo

```bash
uv run scripts/demos/demo_mcp.py
```

Triggers the `get_time` MCP tool and verifies the response contains time information.

### Session Resume Demo

```bash
uv run scripts/demos/demo_resume.py
```

Sends a message, then resumes the session and verifies the agent remembers prior context.

### Run All Demos

```bash
uv run scripts/demos/demo_tool.py && \
uv run scripts/demos/demo_skill.py && \
uv run scripts/demos/demo_mcp.py && \
uv run scripts/demos/demo_resume.py && \
echo "All demos passed!"
```

## Session Backends

The platform supports two session persistence backends:

| Backend | Config | Description |
|---------|--------|-------------|
| JSON (default) | `SESSION_BACKEND=json` | Stores sessions as files in `./sessions/` |
| Redis | `SESSION_BACKEND=redis` | Stores sessions in Redis with `agentops:` key prefix |

Set `SESSION_BACKEND` in `.env` to switch backends. Redis requires additional config:

```
SESSION_BACKEND=redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## Running Tests

```bash
# All tests
uv run pytest tests/ -x -v

# Parity test (RES-05: JSON/Redis consistency)
uv run pytest tests/test_parity.py -x -v

# Session tests
uv run pytest tests/test_session.py -x -v

# Streaming tests
uv run pytest tests/test_chat_stream.py -x -v
```

## Project Structure

```
src/
  main.py              # AgentApp entry point
  app/lifespan.py      # Startup validation + MCP lifecycle
  agent/
    query.py           # Streaming query handler (@app.query)
    session.py         # Session backend factory (JSON/Redis)
  core/
    settings.py        # Pydantic settings from .env
    config.py          # Agent config resolution
  tools/
    __init__.py        # Toolkit with registered tools + skill
    examples.py        # get_weather, calculate tools
  mcp/
    server.py          # Local MCP server (get_time tool)
scripts/
  run_service.sh       # Service starter
  demos/               # Runnable demo scripts
  verify_phase*.sh     # Phase verification scripts
skills/
  example_skill/       # Agent skill (SKILL.md)
tests/                 # Test suite
```

## License

Personal R&D project.
