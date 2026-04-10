# Phase 1: Environment & Workflow Baseline - Research

**Researched:** 2026-04-10 [VERIFIED: system date]
**Domain:** Python environment configuration, reproducible `uv` workflow, and git milestone traceability for FastAPI runtime bootstrap [VERIFIED: .planning/ROADMAP.md]
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Environment configuration contract
- **D-01:** Phase 1 guarantees a minimal env contract with exactly these variables: `MODEL_PROVIDER`, `MODEL_NAME`, `MODEL_API_KEY`, and `MODEL_BASE_URL`. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
- **D-02:** Use `.env` directly and do not add `.env.example` in this phase. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
- **D-03:** Missing required env variables must fail fast at startup with a clear error. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
- **D-04:** Load env config once at startup into typed settings; do not reload `.env` per request. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
- **D-05:** All four minimal variables are required in Phase 1, including `MODEL_BASE_URL`. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]

### Claude's Discretion
- Exact settings implementation details (e.g., settings class layout and validation wiring). [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
- Exact startup error message wording, as long as missing keys are explicit. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-04 | User can configure model/provider via `.env` without code changes. [VERIFIED: .planning/REQUIREMENTS.md] | Typed settings + `.env` loading pattern, required-key fail-fast startup, and explicit env contract mapping in this document. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] |
| CORE-05 | Project is managed with `uv` for dependency and execution workflows. [VERIFIED: .planning/REQUIREMENTS.md] | Baseline command contract (`uv sync`, `uv run ...`) and environment audit of local `uv` availability/version. [CITED: https://docs.astral.sh/uv/reference/cli/] [VERIFIED: local command output] |
| DEV-02 | User can track progress through git commits tied to project milestones. [VERIFIED: .planning/REQUIREMENTS.md] | Phase-aligned commit convention and milestone traceability checks using git history. [VERIFIED: .planning/ROADMAP.md] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Core runtime must rely on `agentscope-runtime`. [VERIFIED: CLAUDE.md]
- Chat API must be FastAPI with streaming responses. [VERIFIED: CLAUDE.md]
- Keep server near-stateless; avoid in-memory coupling. [VERIFIED: CLAUDE.md]
- Resume model must support both JSON-file and Redis backends (later phases still constrain architecture now). [VERIFIED: CLAUDE.md]
- Model/provider config must come from `.env`. [VERIFIED: CLAUDE.md]
- Use `uv` for dependency and execution workflow. [VERIFIED: CLAUDE.md]
- Track progress with git commits/checkpoints. [VERIFIED: CLAUDE.md]
- No project skills are currently defined in `.claude/skills/` or `.agents/skills/`. [VERIFIED: directory checks]

## Summary

Phase 1 planning should lock an execution baseline around three coupled contracts: env contract correctness, `uv` reproducibility, and git checkpoint observability. The user already locked the env contract and failure behavior, so planning should focus on implementation sequencing and verification gates instead of technology selection. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]

Local machine audit shows `uv` and `git` are available, but Python is `3.7.13`; this is below project’s recommended Python `3.11`, so the plan must include a Python version step before runtime validation or treat it as a blocking dependency. [VERIFIED: local command output] [VERIFIED: CLAUDE.md]

Documentation sources could not be fully scraped via WebFetch in this session due domain verification/network policy errors, so API-level claims from external docs are cited with MEDIUM confidence unless directly validated by local command output or repository constraints. [VERIFIED: WebFetch tool errors]

**Primary recommendation:** Plan Phase 1 as a strict bootstrap flow: (1) Python/uv baseline check, (2) typed `.env` settings fail-fast on startup, (3) `uv` run path verification, (4) phase-tagged commit checkpoints. [VERIFIED: .planning/ROADMAP.md]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11 target [VERIFIED: CLAUDE.md] | Runtime baseline for project code [VERIFIED: CLAUDE.md] | Project explicitly recommends 3.11 for compatibility/stability. [VERIFIED: CLAUDE.md] |
| `uv` | 0.11.6 latest on PyPI (2026-04-09) [VERIFIED: PyPI JSON query] | Dependency sync and command execution workflow [CITED: https://docs.astral.sh/uv/reference/cli/] | Required by project constraints and Phase 1 success criteria. [VERIFIED: CLAUDE.md] [VERIFIED: .planning/ROADMAP.md] |
| `pydantic-settings` | 2.13.1 (2026-02-19) [VERIFIED: PyPI JSON query] | Typed settings from `.env` [CITED: https://docs.pydantic.dev/latest/concepts/pydantic_settings/] | Direct fit for locked typed startup config + required env key validation. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] |
| FastAPI | 0.135.3 (2026-04-01) [VERIFIED: PyPI JSON query] | App lifecycle/startup hook for fail-fast config validation [CITED: https://fastapi.tiangolo.com/advanced/events/] | Project constraint requires FastAPI runtime baseline. [VERIFIED: CLAUDE.md] |
| `agentscope-runtime` | 1.1.3 (2026-03-31) [VERIFIED: PyPI JSON query] | Primary runtime under evaluation [VERIFIED: CLAUDE.md] | Locked project dependency, must remain first-class in setup. [VERIFIED: CLAUDE.md] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | 2.12.5 (2025-11-26) [VERIFIED: PyPI JSON query] | Field typing/validation backbone for settings models [CITED: https://docs.pydantic.dev/latest/] | Use for required env validation and explicit startup errors. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] |
| `python-dotenv` | 1.2.2 (2026-03-01) [VERIFIED: PyPI JSON query] | Optional `.env` loading utility if needed by non-pydantic code paths [ASSUMED] | Use only if a non-settings code path requires it; avoid duplicate loaders. [ASSUMED] |
| `ruff` | 0.15.10 (2026-04-09) [VERIFIED: PyPI JSON query] | Fast lint/format in reproducible workflow [VERIFIED: CLAUDE.md] | Use if Phase 1 adds baseline quality gates. [ASSUMED] |
| `pytest` | 9.0.3 (2026-04-07) [VERIFIED: PyPI JSON query] | Startup/config regression tests [VERIFIED: CLAUDE.md] | Use once test scaffolding exists (currently absent). [VERIFIED: file scan]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pydantic-settings` | Manual `os.getenv` mapping | Manual parsing increases missing-key and type-coercion error surface; avoid hand-rolled env validation. [ASSUMED] |
| `uv` workflow | ad-hoc `pip` + direct `python` commands | Less reproducible team/runtime parity; contradicts project tooling constraint. [VERIFIED: CLAUDE.md] |

**Installation:**
```bash
uv sync
```
[CITED: https://docs.astral.sh/uv/reference/cli/]

**Version verification:** Python ecosystem package versions were validated with live PyPI JSON API in this session (latest version + release timestamp): `fastapi`, `pydantic-settings`, `pydantic`, `uvicorn`, `agentscope-runtime`, `uv`, `ruff`, `pytest`, `python-dotenv`, `redis`. [VERIFIED: PyPI JSON query]

## Architecture Patterns

### Recommended Project Structure
```text
src/
├── app/                 # FastAPI app creation and lifecycle wiring [ASSUMED]
├── core/settings.py     # Typed settings model and singleton loader [ASSUMED]
├── core/startup.py      # Startup validation/error surfacing [ASSUMED]
└── main.py              # `uv run` entrypoint for service [ASSUMED]
```

### Pattern 1: Typed Settings Singleton at Startup
**What:** Build one typed settings object from `.env` during startup and inject/use it for request handling; no per-request reload. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
**When to use:** Always for Phase 1 because D-04 locks startup-only loading. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/ [CITED]
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    MODEL_PROVIDER: str
    MODEL_NAME: str
    MODEL_API_KEY: str
    MODEL_BASE_URL: str

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

### Pattern 2: Lifespan-Based Fail-Fast Validation
**What:** Trigger settings load during app startup/lifespan so missing env vars fail before serving traffic. [CITED: https://fastapi.tiangolo.com/advanced/events/] [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
**When to use:** Always in this phase to satisfy D-03. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/events/ [CITED]
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = get_settings()  # fail fast if required env keys are missing
    yield

app = FastAPI(lifespan=lifespan)
```

### Pattern 3: Phase-Aligned Commit Checkpoints
**What:** Use explicit phase commit messages for milestone visibility in git history. [VERIFIED: .planning/ROADMAP.md] [VERIFIED: .planning/REQUIREMENTS.md]
**When to use:** At each meaningful baseline checkpoint in Phase 1 (env contract wired, uv workflow runnable, docs updated). [ASSUMED]
**Example:**
```bash
git log --oneline --decorate -n 20
```
[ASSUMED]

### Anti-Patterns to Avoid
- **Reloading `.env` in request handlers:** Violates locked D-04 and introduces config drift across requests. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
- **Treating required model vars as optional defaults:** Violates D-05 and can mask startup misconfiguration. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
- **Using non-`uv` startup commands as primary docs path:** Conflicts with CORE-05 and project tooling constraint. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: CLAUDE.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env schema + required-key checks | Custom env parser/validator | `pydantic-settings` model | Handles coercion/validation/error reporting consistently with less edge-case code. [ASSUMED] |
| Dependency sync workflow | Custom bootstrap shell scripts for package resolution | `uv sync` + lockfile flow | Standard, reproducible dependency resolution for Python projects. [CITED: https://docs.astral.sh/uv/guides/projects/] |
| Milestone tracker | Custom progress DB/dashboard in Phase 1 | Git commit history + roadmap phase references | Requirement explicitly asks for git milestone traceability, not custom tracking infra. [VERIFIED: .planning/REQUIREMENTS.md] |

**Key insight:** Hand-rolled config/workflow primitives create invisible variance that directly undermines this project’s repeatable call-chain validation goal. [VERIFIED: .planning/PROJECT.md]

## Common Pitfalls

### Pitfall 1: Optionalizing Required Env Fields
**What goes wrong:** Service starts with fallback/empty values and fails later during model calls. [ASSUMED]
**Why it happens:** Fields are defined with defaults instead of required types in settings model. [ASSUMED]
**How to avoid:** Keep all four phase-required keys mandatory and force startup validation. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
**Warning signs:** Startup succeeds even when one of the four required vars is removed from `.env`. [ASSUMED]

### Pitfall 2: Runtime Config Reload per Request
**What goes wrong:** Behavior diverges between requests and complicates debugging/reproducibility. [ASSUMED]
**Why it happens:** Settings object instantiated inside route handlers. [ASSUMED]
**How to avoid:** Cache settings singleton initialized during startup. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]
**Warning signs:** Request latency spikes or inconsistent provider selection without deploy/restart. [ASSUMED]

### Pitfall 3: Toolchain Drift Hidden by Local Machine State
**What goes wrong:** Commands work on one machine but fail for others. [ASSUMED]
**Why it happens:** No version baseline check before `uv` run flow. [ASSUMED]
**How to avoid:** Add explicit preflight check for Python major/minor and `uv` version in Phase 1 plan. [VERIFIED: local command output]
**Warning signs:** Local Python is <3.11 while project expects 3.11 baseline. [VERIFIED: local command output] [VERIFIED: CLAUDE.md]

## Code Examples

Verified/referenced patterns from official docs and locked project constraints:

### Required `.env` Contract
```dotenv
MODEL_PROVIDER=<provider>
MODEL_NAME=<model>
MODEL_API_KEY=<secret>
MODEL_BASE_URL=<endpoint>
```
[VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md]

### Reproducible Workflow Commands
```bash
uv sync
uv run <service entry command>
```
[CITED: https://docs.astral.sh/uv/reference/cli/]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FastAPI startup/shutdown event decorators as primary pattern | Lifespan-based startup/shutdown flow in docs | Current docs era (validated via official events page in this session) [CITED: https://fastapi.tiangolo.com/advanced/events/] | Better alignment for centralized startup checks like env validation. [ASSUMED] |
| Ad-hoc pip command chains | `uv`-centered sync/run workflows | Current `uv` docs and ecosystem trend [CITED: https://docs.astral.sh/uv/guides/projects/] | Higher reproducibility and cleaner execution contract. [ASSUMED] |

**Deprecated/outdated:**
- Using startup event patterns without evaluating lifespan guidance is now a weaker default for new FastAPI bootstrap design. [CITED: https://fastapi.tiangolo.com/advanced/events/]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `python-dotenv` is needed as a supporting dependency for non-settings code paths. | Standard Stack | Unnecessary dependency or duplicated env loading path. |
| A2 | Recommended project structure (`src/app`, `core/settings.py`, etc.) matches desired repo shape. | Architecture Patterns | Planner may produce tasks that need path adjustments. |
| A3 | Phase-aligned commit points should be set at env wiring, uv workflow runnability, and docs checkpoints. | Architecture Patterns | Commit granularity might not match user preference. |
| A4 | Listed pitfalls and warning signs represent the most likely Phase 1 failure modes. | Common Pitfalls | Plan may miss a real blocker and under-specify validation. |
| A5 | Lifespan pattern provides a practical advantage for centralized startup env checks. | State of the Art | Could over-constrain implementation if team prefers event handlers. |

## Open Questions (RESOLVED)

1. **Should Phase 1 enforce Python 3.11 as hard gate or soft warning? — RESOLVED**
   - Resolution: Treat Python 3.11+ as a **hard gate for phase verification execution**. Planning can proceed, but verification commands are considered non-compliant until runtime uses 3.11+. [VERIFIED: CLAUDE.md] [VERIFIED: local command output]
   - Plan impact: Keep explicit preflight/version expectation in phase verification workflow and do not mark phase complete if runtime remains below 3.11. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-01-PLAN.md]

2. **What exact service entry command should be standardized under `uv run`? — RESOLVED**
   - Resolution: Standardize Phase 1 automation around concrete commands already encoded in the plan: `uv sync` and `uv run pytest tests/test_settings.py tests/test_startup.py -q -x` as the mandatory reproducible baseline; runtime startup wiring is validated via startup-focused tests in this phase. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-01-PLAN.md]
   - Plan impact: No replan required; the existing plan already defines and verifies the canonical `uv` command contract for CORE-05 while implementing `src/main.py` lifecycle wiring for startup behavior. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-01-PLAN.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | CORE-05 baseline runtime/tooling compatibility | ✗ (version below target) [VERIFIED: local command output] | 3.7.13 [VERIFIED: local command output] | Install/use Python 3.11 before phase validation. [ASSUMED] |
| `uv` | CORE-05 dependency and execution workflow | ✓ [VERIFIED: local command output] | 0.11.2 (local) [VERIFIED: local command output] | Upgrade to latest documented baseline 0.11.6 for parity. [VERIFIED: PyPI JSON query] |
| git | DEV-02 milestone traceability | ✓ [VERIFIED: local command output] | 2.32.0 [VERIFIED: local command output] | None required. |

**Missing dependencies with no fallback:**
- Python 3.11+ is not currently available; phase runtime validation should be blocked until upgraded. [VERIFIED: local command output] [VERIFIED: CLAUDE.md]

**Missing dependencies with fallback:**
- None identified for this phase baseline. [ASSUMED]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (recommended in project stack), not yet scaffolded in repo. [VERIFIED: CLAUDE.md] [VERIFIED: file scan] |
| Config file | none — Wave 0 gap. [VERIFIED: file scan] |
| Quick run command | `uv run pytest -q -x` [ASSUMED] |
| Full suite command | `uv run pytest -q` [ASSUMED] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-04 | Required env vars loaded from `.env` and missing keys fail fast at startup. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] | unit/integration | `uv run pytest tests/test_settings.py::test_required_env_keys_fail_fast -q -x` [ASSUMED] | ❌ Wave 0 |
| CORE-05 | Dependencies and service execution run through `uv` workflow. [VERIFIED: .planning/REQUIREMENTS.md] | smoke | `uv sync && uv run <entry command>` [ASSUMED] | ❌ Wave 0 |
| DEV-02 | Milestone progress visible in git history with phase-aligned commits. [VERIFIED: .planning/REQUIREMENTS.md] | manual + scriptable check | `git log --oneline --decorate` [ASSUMED] | ✅ (git history exists) [VERIFIED: git history snapshot] |

### Sampling Rate
- **Per task commit:** `uv run pytest -q -x` once tests exist. [ASSUMED]
- **Per wave merge:** `uv run pytest -q` once tests exist. [ASSUMED]
- **Phase gate:** Full suite green + manual git traceability check before `/gsd-verify-work`. [ASSUMED]

### Wave 0 Gaps
- [ ] `tests/test_settings.py` — covers required env contract and fail-fast behavior (CORE-04). [ASSUMED]
- [ ] `pytest` configuration file (`pyproject.toml` test settings or `pytest.ini`) — establish baseline test invocation. [ASSUMED]
- [ ] Canonical service entrypoint and command mapping for `uv run` smoke check (CORE-05). [VERIFIED: file scan]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Phase 1 scope) [VERIFIED: .planning/ROADMAP.md] | N/A in this phase. |
| V3 Session Management | no (Phase 1 scope) [VERIFIED: .planning/ROADMAP.md] | N/A in this phase. |
| V4 Access Control | no (Phase 1 scope) [VERIFIED: .planning/ROADMAP.md] | N/A in this phase. |
| V5 Input Validation | yes (env config validation) [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] | Typed required settings via `pydantic-settings`. [CITED: https://docs.pydantic.dev/latest/concepts/pydantic_settings/] |
| V6 Cryptography | yes (secret handling baseline) [ASSUMED] | Keep API keys in `.env`, avoid logging/secrets in commits. [VERIFIED: CLAUDE.md] [ASSUMED] |

### Known Threat Patterns for Python/FastAPI env bootstrap

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leakage through committed `.env` values | Information Disclosure | Ensure `.env` stays ignored and never logged; validate with git status before commits. [VERIFIED: repository has `.gitignore`] [ASSUMED] |
| Misconfiguration fallback to unsafe defaults | Tampering | Enforce required env vars and fail startup if absent. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] |
| Runtime config drift from per-request reload | Repudiation/Tampering | Single startup load + immutable/shared settings object. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] |

## Sources

### Primary (HIGH confidence)
- Local project directives and decisions: `CLAUDE.md`, `.planning/phases/01-environment-workflow-baseline/01-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` (read directly in session). [VERIFIED: local files]
- PyPI JSON API live checks for versions/release timestamps: `https://pypi.org/pypi/{package}/json` for `fastapi`, `pydantic-settings`, `pydantic`, `uvicorn`, `agentscope-runtime`, `uv`, `ruff`, `pytest`, `python-dotenv`, `redis`. [VERIFIED: command output]
- Local tool availability audit: `python3 --version`, `uv --version`, `git --version`, `node --version`. [VERIFIED: command output]

### Secondary (MEDIUM confidence)
- FastAPI official docs (events/lifespan): https://fastapi.tiangolo.com/advanced/events/
- uv official docs (CLI reference, project guide): https://docs.astral.sh/uv/reference/cli/ and https://docs.astral.sh/uv/guides/projects/
- Pydantic settings official docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

### Tertiary (LOW confidence)
- None retained as authoritative claims; all external non-official sources were excluded from recommendations. [VERIFIED: research notes]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - package versions and project constraints were directly verified in-session. [VERIFIED: PyPI JSON query] [VERIFIED: local files]
- Architecture: MEDIUM - direction is strongly constrained by locked decisions, but some implementation structure remains assumed pending codebase scaffolding. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] [ASSUMED]
- Pitfalls: MEDIUM - core pitfalls align with locked decisions, but failure modes are partly based on practice patterns rather than repo incidents. [VERIFIED: .planning/phases/01-environment-workflow-baseline/01-CONTEXT.md] [ASSUMED]

**Research date:** 2026-04-10 [VERIFIED: system date]
**Valid until:** 2026-05-10 (30 days; stack is moderately fast-moving). [ASSUMED]

## RESEARCH COMPLETE
