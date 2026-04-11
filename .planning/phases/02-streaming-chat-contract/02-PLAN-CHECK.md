---
gsd_state_version: 1.0
phase: 02-streaming-chat-contract
verifier: plan-checker
iteration: 1
status: issues_found_and_fixed
issues_count: 2 blocker, 2 warning, 2 info
fixes_applied: "Blocker 1 (D-06 test coverage) fixed: added test_runtime_failure_emits_sse_error to Plan 02 Task 1. Blocker 2 (D-06 handler documentation) fixed: added D-06 error handling documentation to Plan 01 Task 2. Warning 3 (weak lifecycle assertion) fixed: changed to require ALL THREE statuses (created AND in_progress AND completed)."
date: "2026-04-11"
---

# Plan Verification: Phase 02 - Streaming Chat Contract

## VERIFICATION PASSED

**Phase:** 02-streaming-chat-contract
**Plans verified:** 2
**Status:** Issues found (2 blockers, 2 warnings, 2 info)

---

## Goal-Backward Analysis

**Phase Goal:** Users can call a chat endpoint and receive streaming responses end-to-end.

**Success Criteria (must ALL be TRUE):**
1. User can open a streaming chat request and receive incremental SSE events until completion.
2. User can repeat the same request and observe the stream completes without server-side state drift.

**What must be TRUE for these criteria to hold:**
- A /process endpoint exists accepting POST with messages array (D-01, D-02)
- The endpoint produces typed SSE events with explicit lifecycle (D-03, D-04)
- Pre-stream validation errors return HTTP status codes (D-05)
- Mid-stream runtime failures emit SSE error events (D-06)
- pytest + smoke script verify all of the above (D-07)
- Repeated requests complete the lifecycle reliably (D-08)

---

## Dimension 1: Requirement Coverage

**PASS**

| Requirement | Plans | Tasks | Status |
|-------------|-------|-------|--------|
| CORE-01 (streaming SSE endpoint) | 01, 02 | 01-T1 (AgentApp + deps), 01-T2 (query handler), 02-T1 (contract tests), 02-T2 (smoke script) | COVERED |

CORE-01 is the only requirement mapped to Phase 2 per ROADMAP.md and REQUIREMENTS.md traceability table. Both plans claim CORE-01 and together address all facets: endpoint creation, streaming behavior, lifecycle events, error handling, and repeat stability.

---

## Dimension 2: Task Completeness

**PASS (with warnings)**

| Plan | Task | Type | Files | Action | Verify | Done | Status |
|------|------|------|-------|--------|--------|------|--------|
| 01 | 1 | auto | Yes | Yes | Yes | Yes | Valid |
| 01 | 2 | auto | Yes | Yes | Yes | Yes | Valid |
| 02 | 1 | auto(tdd) | Yes | Yes | Yes | Yes | Valid |
| 02 | 2 | auto | Yes | Yes | Yes | Yes | Valid |

All tasks have Files, Action, Verify, and Done elements. Actions are specific with code examples, file paths, and step-by-step instructions.

---

## Dimension 3: Dependency Correctness

**PASS**

| Plan | depends_on | Wave | Status |
|------|------------|------|--------|
| 01 | [] | 1 | Valid - no dependencies |
| 02 | ["02-01"] | 2 | Valid - must wait for Plan 01 |

No cycles. No missing references. Wave numbers consistent with dependencies. Plan 02 correctly depends on Plan 01 completing first (AgentApp must exist before tests can run).

---

## Dimension 4: Key Links

**PASS**

Plan 01 key links:
- `src/main.py` -> `AgentApp` via class instantiation -- Action step 3 provides exact code
- `src/agent/query.py` -> `src/main.py` via `@app.query` decorator -- Action step 2 provides exact code
- `src/main.py` -> `src/agent/` via `import src.agent` -- Action step 3 includes the import

Plan 02 key links:
- `tests/test_chat_stream.py` -> `src/main.py` via `TestClient(app)` -- Action provides fixture code
- `tests/test_chat_stream.py` -> `/process` via POST request -- Tests POST to `/process`
- `scripts/verify_phase2.sh` -> `tests/` via pytest invocation -- Script includes `uv run pytest`

All key links have corresponding wiring in task actions.

---

## Dimension 5: Scope Sanity

| Plan | Tasks | Files | Assessment |
|------|-------|-------|------------|
| 01 | 2 | 6 | OK (2 tasks, within target) |
| 02 | 2 | 3 | OK (2 tasks, within target) |

Both plans are within the 2-3 tasks target. No scope concerns.

---

## Dimension 6: Verification Derivation

**PASS**

Plan 01 must_haves truths (user-observable):
- "The service boots successfully with AgentApp replacing bare FastAPI" -- user-observable
- "The /process endpoint is registered and responds to POST requests" -- user-observable
- "The existing startup validation (settings fail-fast) still works" -- user-observable
- "SSE streaming lifecycle events appear in response" -- user-observable

Plan 02 must_haves truths (user-observable):
- "POST /process with valid messages returns SSE stream with correct content type" -- user-observable
- "SSE stream contains the full lifecycle" -- user-observable
- "POST /process with invalid input returns HTTP error" -- user-observable
- "Repeated identical requests each complete full SSE lifecycle" -- user-observable

All truths are user-observable, not implementation-focused. Artifacts map to truths. Key links cover critical wiring.

---

## Dimension 7: Context Compliance

### Locked Decisions Coverage

| Decision | Plan | Task(s) | Covered |
|----------|------|---------|---------|
| D-01 (messages array) | 01 | T2 (handler accepts `msgs` from request body `input` field) | YES |
| D-01 (messages array) | 02 | T1 (payload fixture uses `input` array format) | YES |
| D-02 (minimal contract) | 01 | T1 (removes unnecessary pins, keeps minimal deps) | YES |
| D-03 (typed SSE events) | 01 | T2 (AgentApp produces typed events with object/status fields) | YES |
| D-03 (typed SSE events) | 02 | T1 (tests parse `status` field values) | YES |
| D-04 (explicit lifecycle) | 01 | T2 (created/in_progress/completed lifecycle via AgentApp) | YES |
| D-04 (explicit lifecycle) | 02 | T1 (test_stream_lifecycle_events verifies lifecycle pattern) | YES |
| D-05 (pre-stream HTTP errors) | 02 | T1 (test_invalid_input_returns_http_error verifies 422) | YES |
| D-06 (runtime SSE errors) | 01 | T2 (mentioned in task rationale) | PARTIAL |
| D-07 (pytest + smoke script) | 02 | T1 (pytest tests), T2 (smoke script) | YES |
| D-08 (repeat stability) | 02 | T1 (test_repeated_requests_stable) | YES |

### Scope Reduction Check

No scope reduction language detected. Plans do not use "v1", "simplified", "static for now", "placeholder", or similar reduction patterns. Decisions are delivered as stated.

### Deferred Ideas Check

Plans do NOT include any of the following deferred items:
- Request-scoped agent configuration payloads (Phase 3)
- Skill/tool/MCP invocation trace events (Phase 4)
- Multi-turn context continuity (Phase 5)
- JSON/Redis session persistence (Phases 6-8)

**PASS** on deferred scope exclusion.

---

## Dimension 7b: Scope Reduction Detection

No scope reduction detected. Plans reference D-XX decisions and deliver them at face value without introducing versioning ("v1/v2") or reduction qualifiers.

**PASS**

---

## Dimension 8: Nyquist Compliance

**SKIPPED** -- No VALIDATION.md exists for this phase. The RESEARCH.md contains a "Validation Architecture" section, but the VALIDATION.md prerequisite file does not exist. Per the process, Dimension 8 checks require VALIDATION.md as a gate condition.

Note: This is not flagged as a failure because the Nyquist validation workflow appears to be optional based on config.json settings, and the phase has RESEARCH.md with validation architecture but no separate VALIDATION.md artifact. The testing approach is embedded directly in the plan tasks.

---

## Dimension 9: Cross-Plan Data Contracts

**PASS**

No conflicting data transformations detected. Plan 01 produces SSE events from the AgentApp/agentscope-runtime pipeline. Plan 02 consumes those SSE events in tests via TestClient. The data flows in one direction (01 produces, 02 verifies) with no transformation conflicts.

---

## Dimension 10: CLAUDE.md Compliance

**PASS**

CLAUDE.md directives checked:
- "Use uv for project/dependency management" -- Both plans use `uv sync`, `uv run pytest`, `uv run python`
- "FastAPI with streaming responses" -- Plan 01 replaces bare FastAPI with AgentApp (FastAPI subclass) which provides streaming
- "State Model: near-stateless" -- Handler creates fresh agent per request, InMemoryMemory is request-scoped
- "Environment: config from .env" -- Settings continue to use get_settings() from .env
- "Versioning: git commits" -- Verification scripts check git traceability
- "Chinese conversation" -- Not relevant for plan structure
- "GSD Workflow Enforcement" -- Plans are within GSD workflow, properly structured

---

## Dimension 11: Research Resolution

**ISSUE FOUND**

The RESEARCH.md contains `## Open Questions` section (lines 433-448) with 3 questions:
1. "agentscope-runtime version: 1.1.3 vs 1.1.4?" -- Has recommendation but no RESOLVED marker
2. "Can we avoid the heavy dependency footprint?" -- Has recommendation but no RESOLVED marker
3. "Does the existing app_lifespan work with AgentApp?" -- Has recommendation but no RESOLVED marker

The section heading does NOT have `(RESOLVED)` suffix. Individual questions lack inline resolution markers.

However, the questions all have clear recommendations that the plans follow (pin 1.1.3, accept full deps, use existing lifespan). The research is functionally resolved in the plans even though the section header lacks the formal marker.

**Severity: WARNING** -- The RESEARCH.md Open Questions section is not formally marked as resolved, but the plans do address each question through their implementation choices. The planner should update the section heading to `## Open Questions (RESOLVED)` and add inline RESOLVED markers.

---

## Issues Found

### Blockers (must fix)

**1. [context_compliance] D-06 (runtime failures as SSE error events) has no dedicated task or test**

Plan 01 Task 2 mentions D-06 in its action rationale: "Per D-01, D-03, D-04, and D-06 (runtime failures as SSE errors)". However:
- No task action explicitly implements SSE error event emission for runtime failures
- No test in Plan 02 verifies that mid-stream runtime failures produce SSE error events before termination
- The `@app.query` decorator from agentscope-runtime likely handles this automatically, but there is no test confirming it

This means if the framework does NOT emit SSE error events for runtime failures (e.g., model API timeout mid-stream), the success criteria "stream completes without server-side state drift" could fail silently -- the stream might just terminate without a proper error event.

```yaml
issue:
  plan: "02-02"
  dimension: context_compliance
  severity: blocker
  description: "D-06 (runtime failures emit SSE error events then terminate cleanly) has no test coverage. No task verifies that mid-stream failures produce SSE error events."
  task: 1
  fix_hint: "Add a test case: mock stream_printing_messages to raise an exception after yielding one chunk, then verify the SSE response contains an error event (not just abrupt termination). If agentscope-runtime handles this automatically, the test confirms it; if not, the test reveals a gap."
```

**2. [context_compliance] D-06 success criteria gap -- no task addresses what happens when the model API fails mid-stream**

Connected to blocker 1 but at the plan structure level. Plan 01's success criteria mention "The query handler creates a fresh agent per request" but say nothing about error resilience. Plan 02's success criteria claim "D-06: error handling path exists (SSE errors if runtime fails mid-stream)" but no task implements or tests this path.

```yaml
issue:
  plan: "02-01"
  dimension: context_compliance
  severity: blocker
  description: "Plan 01 success criteria claim D-06 coverage but no task implements runtime failure handling. The handler code does not include try/except or error event logic."
  task: 2
  fix_hint: "Either: (a) confirm that agentscope-runtime's @app.query decorator automatically catches exceptions from the async generator and emits SSE error events, and document this in the task action, or (b) add explicit error handling in the query handler that catches exceptions and yields error messages."
```

### Warnings (should fix)

**3. [verification_derivation] Test 2 (lifecycle events) assertion may be too weak**

The test description says: "Assert that the collected events contain at least one event with status 'created' or 'in_progress'. Assert that at least one event has status 'completed'." The word "or" in "created OR in_progress" means the test could pass without ever seeing a "created" event. For D-04 (explicit lifecycle with start, delta, complete), the test should verify that all three lifecycle phases appear: created AND in_progress AND completed.

```yaml
issue:
  plan: "02-02"
  dimension: verification_derivation
  severity: warning
  description: "test_stream_lifecycle_events assertion uses 'created' OR 'in_progress' which could pass without a 'created' event, weakening D-04 verification."
  task: 1
  fix_hint: "Change assertion to require both 'created' AND 'in_progress' AND 'completed' statuses in the collected events, to fully verify the explicit lifecycle per D-04."
```

**4. [research_resolution] RESEARCH.md Open Questions section not formally resolved**

```yaml
issue:
  plan: null
  dimension: research_resolution
  severity: warning
  description: "RESEARCH.md has '## Open Questions' without '(RESOLVED)' suffix and no inline RESOLVED markers on the 3 listed questions."
  fix_hint: "Update section header to '## Open Questions (RESOLVED)' and add RESOLVED markers inline: e.g., 'RESOLVED: Pin to 1.1.3 from PyPI', 'RESOLVED: Accept full dependency tree', 'RESOLVED: Existing lifespan works per docs'."
```

### Info (suggestions)

**5. [scope_sanity] Plan 01 Task 1 modifies 5 files with a complex dependency resolution step**

Plan 01 Task 1 modifies pyproject.toml, uv.lock, src/main.py, src/app/lifespan.py, and scripts/run_service.sh. The `uv sync` step introduces agentscope-runtime with a heavy transitive dependency tree. If dependency resolution fails, the entire task is blocked. Consider splitting the dependency update from the code changes if the transitive deps cause issues during execution.

```yaml
issue:
  plan: "02-01"
  dimension: scope_sanity
  severity: info
  description: "Plan 01 Task 1 handles both dependency resolution AND code changes. The agentscope-runtime dependency brings heavy transitive deps that may cause resolution issues."
  task: 1
  fix_hint: "Not required to split now, but during execution, if uv sync fails, isolate the dependency resolution step before attempting code changes."
```

**6. [task_completeness] Plan 02 Task 1 TDD label but behavior section uses non-standard TDD task format**

The task is marked `tdd="true"` but the frontmatter type is `auto`, not `tdd`. The TDD task type should have `<behavior>` and `<implementation>` sections per the dimension specification. The task has `<behavior>` but no `<implementation>` element -- the implementation is inside `<action>` instead. This is a structural inconsistency but the content is sufficient for execution.

```yaml
issue:
  plan: "02-02"
  dimension: task_completeness
  severity: info
  description: "Task 1 has type='auto' with tdd='true' attribute and <behavior> element, but the TDD format expects type='tdd' with <implementation> rather than <action>."
  task: 1
  fix_hint: "Either change type to 'tdd' and rename <action> to <implementation>, or remove tdd='true' attribute and keep as standard auto task with <action>."
```

---

## Structured Issues (YAML)

```yaml
issues:
  - plan: "02-02"
    dimension: context_compliance
    severity: blocker
    description: "D-06 (runtime failures emit SSE error events then terminate cleanly) has no test coverage. No task verifies that mid-stream failures produce SSE error events before termination."
    task: 1
    fix_hint: "Add test case: mock stream_printing_messages to raise exception after first chunk, verify SSE response contains error event, not abrupt termination."

  - plan: "02-01"
    dimension: context_compliance
    severity: blocker
    description: "Plan 01 success criteria claim D-06 coverage but no task implements or documents runtime failure handling. The query handler has no explicit error handling."
    task: 2
    fix_hint: "Either confirm agentscope-runtime @app.query auto-handles exceptions (document in task action) or add try/except in handler that yields error messages before terminating."

  - plan: "02-02"
    dimension: verification_derivation
    severity: warning
    description: "test_stream_lifecycle_events uses 'created' OR 'in_progress' assertion, could pass without 'created' event, weakening D-04 verification."
    task: 1
    fix_hint: "Require all three statuses: 'created' AND 'in_progress' AND 'completed' in lifecycle test."

  - plan: null
    dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions section lacks (RESOLVED) suffix and inline markers."
    fix_hint: "Update header to '## Open Questions (RESOLVED)' and add inline RESOLVED markers."

  - plan: "02-01"
    dimension: scope_sanity
    severity: info
    description: "Task 1 bundles dependency resolution (heavy transitive deps) with code changes. Resolution failure blocks entire task."
    task: 1
    fix_hint: "Monitor during execution; if uv sync fails, isolate as separate step."

  - plan: "02-02"
    dimension: task_completeness
    severity: info
    description: "Task 1 has type='auto' with tdd='true' and <behavior> element, inconsistent with expected TDD task format."
    task: 1
    fix_hint: "Align task type declaration with content format."
```

---

## Verification Questions Answered

**Q1: Will executing both plans satisfy BOTH success criteria?**

Partially. Success Criterion 1 (streaming SSE events until completion) is well-covered. Success Criterion 2 (repeat without state drift) is covered by test_repeated_requests_stable. However, D-06 (runtime failures as SSE errors) is claimed but untested -- if a model API call fails mid-stream, the plans do not verify that the SSE stream terminates cleanly with an error event rather than hanging or crashing. This is a gap that could cause the stream to fail silently.

**Q2: Is every locked decision (D-01 through D-08) addressed?**

D-01 through D-05, D-07, D-08: YES, all addressed with implementing tasks.
D-06: PARTIAL. Mentioned in rationale but no task implements explicit handling and no test verifies the behavior. This is the blocker.

**Q3: Are there gaps where success criteria could fail despite all tasks completing?**

Yes. If the agentscope-runtime `@app.query` decorator does NOT automatically catch exceptions from the async generator and emit SSE error events, then mid-stream failures (model timeout, API error) would result in abrupt stream termination without error signaling. This would violate D-06 and could cause client-side hangs.

**Q4: Are dependencies between plans correct?**

Yes. Plan 02 depends on Plan 01. No cycles. Wave assignment consistent.

**Q5: Are there missing tasks that should exist?**

A D-06 error-path test task is missing. One test should verify that when the streaming handler raises an exception mid-stream, the response contains an SSE error event rather than an abrupt close.

**Q6: Is the verification approach sufficient?**

Almost sufficient. The 4-test approach covers the happy path and repeat stability well. The lifecycle test should be tightened (all 3 statuses required). The missing error-path test (D-06) is the primary gap.

---

## Recommendation

2 blocker(s) require revision. Both relate to D-06 coverage -- the locked decision that runtime failures should emit SSE error events then terminate cleanly. The plans claim this is handled but provide neither implementation nor verification.

**Fix path for planner:**
1. In Plan 01 Task 2: Add explicit documentation or implementation confirming that `@app.query` handles exceptions from the async generator and emits SSE error events. If the framework does this automatically, document it. If not, add try/except.
2. In Plan 02 Task 1: Add a 5th test case `test_runtime_failure_emits_sse_error` that mocks `stream_printing_messages` to raise an exception after yielding one chunk, then verifies the SSE response contains an error status event.
3. (Optional) Tighten Test 2 lifecycle assertions to require all three statuses.

Returning to planner with feedback.
