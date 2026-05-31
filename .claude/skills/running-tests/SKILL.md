---
name: running-tests
description: Run this project's pytest suite and pick the right test scope. Use when running tests, deciding which test files a change needs, checking coverage, or before committing. Covers test deps, single/multi-file runs, the scope-selection rules, the new-view-needs-tests rule, and the test-change-approval rule.
---

# Running tests (famille-busson)

> For a low-cost delegated run, hand this off to the **test-runner** subagent (sonnet) —
> it applies the same scope rules and returns a pass/fail verdict.

All commands run from the repo root.

## Commands
- **Install test deps (once):** `uv sync --group test`
- **Run all tests:** `uv run --group test pytest`
- **Run a single file:** `uv run --group test pytest annuaire/tests/test_views_auth.py`
- **Run multiple files:** `uv run --group test pytest annuaire/tests/test_views_auth.py annuaire/tests/test_views_profile.py`
- **HTML coverage report:** `uv run --group test pytest --cov-report=html` → open `htmlcov/index.html`

Tests live in `annuaire/tests/` and `publications/tests/`. Shared fixtures (accounts,
persons, chalets) are in `annuaire/tests/conftest.py`; `publications/tests/conftest.py`
re-uses them. CI runs automatically on push to `develop` and `main` via
`.github/workflows/tests.yml`.

## Test scope selection
Select the minimal relevant scope based on the changes made:
- **Single view/form change** → run only the corresponding test file(s) (e.g. `test_views_chalets.py` for chalet views)
- **Model change** → run the full suite (models underpin everything)
- **Settings / middleware / signals change** → run the full suite
- **Mass refactoring or cross-cutting change** → run the full suite
- **New feature confined to one area** → run that area's test file(s) plus `conftest.py`-dependent files if fixtures changed

When in doubt, prefer the full suite. Always state which files you are running and why.

> A partial run that passes all its assertions but only fails the `--cov-fail-under`
> coverage gate counts as **green** — don't escalate to the full suite just to clear it.

## Rules
- **Tests gate commits:** if tests were run and any failed, do not commit — report the
  failures instead. A commit may only happen after a fully green test run (or the user
  explicitly chose to commit without tests).
- **New view → new tests:** every new view (function or class-based) must be accompanied
  by a corresponding test block in the appropriate test file. A view is not complete
  until its tests are written and passing.
- **Test changes:** new tests can be written freely. Modifying or deleting existing tests
  requires presenting the change and waiting for user approval first.
