# Phase 1: Environment & Workflow Baseline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 01-environment-workflow-baseline
**Areas discussed:** Env config contract

---

## Env config contract

### Q1 — Which `.env` variables should Phase 1 guarantee?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal vars | Support `MODEL_PROVIDER`, `MODEL_NAME`, `MODEL_API_KEY`, optional `MODEL_BASE_URL`. Keep scope lean. | ✓ |
| Extended vars | Add variables like temperature, max tokens, timeout, and streaming mode. | |
| You decide | Leave variable set decisions to implementation. | |

**User's choice:** Minimal vars
**Notes:** Follow-up clarification later locked `MODEL_BASE_URL` as required rather than optional.

---

### Q2 — `.env.example` in Phase 1?

| Option | Description | Selected |
|--------|-------------|----------|
| `.env.example` | Add sample env file with required keys and comments. | |
| No sample file | Keep only `.env`; no `.env.example` in this phase. | ✓ |
| You decide | Let implementation decide. | |

**User's choice:** Use `.env` only
**Notes:** User provided free-text clarification first: "i have .env", then confirmed explicit lock: use `.env` only.

---

### Q3 — Missing required env vars behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| Fail fast startup | Validate at startup and stop service with clear missing-var message. | ✓ |
| Validate on first use | Defer validation until first model-dependent request. | |
| You decide | Let implementation decide. | |

**User's choice:** Fail fast startup
**Notes:** Locks startup-time validation behavior.

---

### Q4 — How should `.env` be applied at runtime?

| Option | Description | Selected |
|--------|-------------|----------|
| Startup-loaded settings | Load once at startup into typed settings and reuse per request. | ✓ |
| Per-request reload | Re-read `.env` on each request to pick up live changes. | |
| You decide | Let implementation decide. | |

**User's choice:** Startup-loaded settings
**Notes:** Supports near-stateless runtime while avoiding per-request config reload overhead.

---

### Q5 — Requiredness of minimal vars?

| Option | Description | Selected |
|--------|-------------|----------|
| All required | Require all minimal vars and fail startup if any are missing. | ✓ |
| Base URL optional | Keep `MODEL_BASE_URL` optional; others required. | |
| You decide | Let implementation decide. | |

**User's choice:** All required
**Notes:** Final contract requires `MODEL_BASE_URL` too.

---

## Claude's Discretion

- Exact settings object structure and startup validation implementation details.

## Deferred Ideas

None.
