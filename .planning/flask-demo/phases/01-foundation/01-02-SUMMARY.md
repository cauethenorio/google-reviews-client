---
phase: 01-foundation
plan: 02
subsystem: flask-example
tags: [pytest, testing, fernet, cookies, views, env-vars]
dependency_graph:
  requires: [create_app, encrypt_tokens, decrypt_tokens, views_bp]
  provides: [test_suite, conftest_fixtures]
  affects: [flask-example/tests]
tech_stack:
  added: [pytest]
  patterns: [pytest-fixtures, monkeypatch-env-vars, test-client]
key_files:
  created:
    - flask-example/tests/__init__.py
    - flask-example/tests/conftest.py
    - flask-example/tests/test_app.py
    - flask-example/tests/test_cookies.py
    - flask-example/tests/test_views.py
  modified:
    - pyproject.toml
decisions:
  - Added flask-example/tests/* to ruff per-file-ignores in root pyproject.toml to suppress S101/S105/ARG/D rules in demo test files
metrics:
  duration: 806s
  completed: 2026-04-04T03:37:46Z
---

# Phase 01 Plan 02: Flask Demo Test Suite Summary

15-test pytest suite covering env var validation, Fernet cookie round-trip and failure modes, and index route response.

## What Was Built

- **flask-example/tests/conftest.py**: Shared fixtures -- `env_vars` (monkeypatches all 3 required env vars), `app` (creates app with TESTING=True), `client` (Flask test client).
- **flask-example/tests/test_app.py**: 6 tests for INFRA-01 -- app creation success with Fernet and config values, 3 missing env var cases each raising RuntimeError with var name, error message contains "not set", Fernet key determinism (encrypt with one app, decrypt with another).
- **flask-example/tests/test_cookies.py**: 7 tests for INFRA-02 -- encrypt/decrypt round-trip, encrypt returns string, invalid data returns None, tampered data returns None, wrong key returns None, TOKEN_COOKIE_NAME constant, COOKIE_MAX_AGE constant.
- **flask-example/tests/test_views.py**: 2 tests for INFRA-03 -- GET / returns 200 with "app is running", page contains "Google Reviews Demo".
- **pyproject.toml**: Added `flask-example/tests/*` per-file-ignores for ruff (S101, S105, ARG001, ARG002, D, etc.).

## Test Results

```
15 passed in 0.02s
```

| File | Tests | Coverage |
|------|-------|----------|
| test_app.py | 6 | INFRA-01: env var validation |
| test_cookies.py | 7 | INFRA-02: cookie encryption |
| test_views.py | 2 | INFRA-03: index route |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 7157741 | Test fixtures (conftest.py) and app factory tests (test_app.py) |
| 2 | ad75105 | Cookie encryption tests (test_cookies.py) and view tests (test_views.py) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added flask-example/tests/* ruff per-file-ignores**
- **Found during:** Task 1 (pre-commit hook)
- **Issue:** Root pyproject.toml ruff config only had `tests/*` in per-file-ignores, which doesn't match `flask-example/tests/*`. Tests triggered S101 (assert), S105 (hardcoded password), ARG001/ARG002 (unused fixture args), D104 (missing docstring).
- **Fix:** Added `flask-example/tests/*` entry to `[tool.ruff.lint.per-file-ignores]` in root pyproject.toml with same ignore set plus ARG002.
- **Files modified:** pyproject.toml
- **Commit:** 7157741

## Known Stubs

None -- all test files are complete and testing real implementations.

## Self-Check: PASSED

All 5 created files verified on disk. Both commits (7157741, ad75105) verified in git log.
