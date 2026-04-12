---
phase: 08-parity-demo-flows
plan: 02
subsystem: testing, docs
tags: [httpx, sse, demo-scripts, readme, session-resume]

# Dependency graph
requires:
  - phase: 04-capability-invocation-tracing
    provides: "Registered tools (get_weather, calculate), MCP server (get_time), and toolkit singleton"
  - phase: 06-json-session-persistence
    provides: "JSON session backend with save/load via session_id in request payload"
  - phase: 07-redis-session-persistence
    provides: "Redis session backend with SESSION_BACKEND env var toggle"
provides:
  - "4 runnable demo scripts (tool, skill, MCP, resume) in scripts/demos/"
  - "Shared _helpers.py with SSE parsing and service health check"
  - "Unified README.md getting-started guide (DEV-01)"
  - ".env.example with required configuration keys"
affects: [documentation, onboarding, demo-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Demo script pattern: check_service_running() pre-flight + send_chat() + assertion"
    - "SSE event parsing: parse all data lines, extract text from delta/content events"
    - "Session resume demo: two-request flow with shared session_id"

key-files:
  created:
    - scripts/demos/_helpers.py
    - scripts/demos/demo_tool.py
    - scripts/demos/demo_skill.py
    - scripts/demos/demo_mcp.py
    - scripts/demos/demo_resume.py
    - .env.example
  modified:
    - README.md

key-decisions:
  - "Used shared _helpers.py module for service health check, SSE parsing, and send_chat utility across all demos"
  - "Each demo script is standalone with pre-flight service check and built-in assertions (exit non-zero on failure)"
  - "README.md covers Quick Start, all 4 demo commands, session backends, test commands, and project structure"

patterns-established:
  - "Demo script pattern: standalone Python script with httpx, SSE parsing, assertion-based validation"
  - "Pre-flight service check pattern: check_service_running() at script entry with clear error message"
  - "SSE text extraction pattern: parse all data lines, extract from delta/content events, check completed status"

requirements-completed: [DEV-01, DEV-03]

# Metrics
duration: 6min
completed: 2026-04-12
---

# Phase 08 Plan 02: Demo Scripts & README Summary

**4 standalone demo scripts (tool, skill, MCP, resume) with shared SSE parsing helpers and unified README.md getting-started guide**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-12T08:04:42Z
- **Completed:** 2026-04-12T08:10:43Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created shared helpers module with service health check, SSE parsing, and send_chat utility
- Created 4 standalone demo scripts (tool, skill, MCP, resume) each with assertions and service pre-checks
- Rewrote README.md as complete getting-started guide with Quick Start, demo commands, session backend docs, and test instructions
- Created .env.example with required configuration keys

## Task Commits

Each task was committed atomically:

1. **Task 1: Create shared helpers and demo scripts for tool, skill, MCP capabilities** - `f73ba90` (feat)
2. **Task 2: Create resume demo script and update README.md as unified getting-started guide** - `f06bc26` (feat)

## Files Created/Modified
- `scripts/demos/_helpers.py` - Shared utilities: check_service_running, parse_sse_events, extract_text_from_events, send_chat
- `scripts/demos/demo_tool.py` - Tool call demo triggering get_weather via chat endpoint
- `scripts/demos/demo_skill.py` - Skill injection demo verifying platform context in agent response
- `scripts/demos/demo_mcp.py` - MCP tool call demo triggering get_time via chat endpoint
- `scripts/demos/demo_resume.py` - Session resume demo with two-request flow and context recall verification
- `README.md` - Unified getting-started guide (Quick Start, demos, session backends, tests, project structure)
- `.env.example` - Environment configuration template with required keys

## Decisions Made
- Used shared `_helpers.py` module for common utilities instead of duplicating SSE parsing and health check logic across scripts
- Each demo uses `check_service_running()` pre-flight check with clear error message per Pitfall 1 from RESEARCH.md
- `send_chat()` helper combines HTTP POST, SSE parsing, completed-status check, and text extraction into single call
- README uses concise practical format per D-09 with Quick Start, individual demo commands, session backend table, and test commands

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required beyond what README.md documents.

## Next Phase Readiness
- All 4 demo scripts ready for end-to-end validation with a running service
- README.md provides complete onboarding path for new users
- Demo scripts depend on Plan 01 output (skill registration in src/tools/__init__.py) for demo_skill.py to work correctly

## Self-Check: PASSED

All 8 created/modified files verified present. Both task commits verified in git log.

---
*Phase: 08-parity-demo-flows*
*Completed: 2026-04-12*
