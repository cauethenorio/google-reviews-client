# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-03)

**Core value:** Let potential users try the library instantly — no setup, no database, no data stored
**Current focus:** Phase 3 — Data Browsing

## Current Position

Phase: 3 of 4 (Data Browsing)
Plan: 2 of 2 in current phase
Status: Phase 03 complete
Last activity: 2026-04-04 — Plan 03-02 completed (data browsing test suite)

Progress: [███████░░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: ~5 min
- Total execution time: ~23 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 2 | ~16 min | ~8 min |
| 2 | 2 | ~4 min | ~2 min |
| 3 | 2 | ~6 min | ~3 min |

**Recent Trend:**
- Last 5 plans: 01-02 (806s), 02-01 (109s), 02-02 (85s), 03-01 (173s), 03-02 (205s)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: Flask + Fernet for stateless cookie encryption (cryptography package, not itsdangerous)
- Init: Store only access_token, refresh_token, expiry in cookie; reconstruct rest from env vars
- Init: SameSite=Lax required for OAuth callback (Strict breaks cross-site redirect)
- 02-01: PKCE code_verifier stored in Fernet-encrypted pending cookie with 5 min TTL
- 02-01: Error messages mapped in Jinja2 template with role=alert for accessibility
- 02-01: REDIRECT_URI env var optional, defaults to url_for for local dev
- 02-02: Mock auth.Flow (not full module path) since auth.py imports directly
- 02-02: Parse Set-Cookie header to extract encrypted cookie for test verification
- 03-01: Used _error_context() helper to map library exceptions to template-friendly dicts
- 03-01: Multiple API calls per route for accurate breadcrumb labels (acceptable for demo)
- 03-01: Conditional / route replaces separate /accounts endpoint
- 03-02: Use test_request_context for api.py tests instead of patching Flask proxies
- 03-02: Mock views.get_client at module level for clean route test isolation

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2: Verify `business.manage` scope string matches settings.py before building auth URL
- Phase 2: Measure actual cookie payload size after first real OAuth flow (target < 3800 bytes)

## Session Continuity

Last session: 2026-04-04
Stopped at: Completed 03-02-PLAN.md — Data browsing test suite
Resume file: .planning/flask-demo/phases/03-data-browsing/03-02-SUMMARY.md
