# Project Context: Famille Busson

> Procedures live in skills, not here. Three are project-specific and live in
> `.claude/skills/`: **dev-commands** (server / migrate / shell / uv /
> populate_dev_data + credentials), **issue-workflow** (GitHub issue → develop) and
> **release-workflow** (develop → main — famille-busson has no versioned/tagged
> release, so the generic `/release` skill doesn't fit; this stays project-local).
> **`/test-select`** is the one **global** skill in play here — installed in
> `~/.claude/skills/`, shared across every project on this machine, not a
> famille-busson-specific file — and it replaces the former project-local
> `running-tests` skill by reading this file (branch model, test command, toolchain)
> instead of hardcoding it. This file holds only the always-on facts and gotchas.

## 1. Tech Stack
- **Framework:** Django 6.0
- **Language:** Python 3.13
- **Database:** SQLite (Development) / PostgreSQL (Production)
- **Frontend:** Bootstrap 5
- **Environment:** uv

## 2. Critical Configuration (Custom User)
**IMPORTANT:** This project uses a Custom User Model.
- **App:** `annuaire`
- **Model Name:** `Account`
- **Settings:** `AUTH_USER_MODEL = 'annuaire.Account'`
- **Inheritance:** Inherits from `AbstractBaseUser` + `PermissionsMixin`
- **Profile model:** `Person` — linked via `Person.account = OneToOneField(Account, related_name='profile')`

> *Note to AI: Always use `get_user_model()` or `settings.AUTH_USER_MODEL` in ForeignKeys
> (`from django.conf import settings`). Never reference `django.contrib.auth.models.User`.
> Access the profile from a user instance via `user.profile`.*

## 3. Project Structure
- **Root / settings app:** `famille_busson`
- **Functional Apps:**
    - `annuaire`: users (`Account`), profiles (`Person`), family relations (`Relation`),
      chalets (`Chalet`), and presences (`PresencePSV`)
    - `publications`: blog posts (`BlogPost`), comments (`Comment`), attachments (`Attachment`)

## 4. Coding Standards & Preferences
- **Views:** Class-Based Views preferred. Ownership checks go in `get_object()`, raising `PermissionDenied`.
- **Forms:** ModelForms prefixed `Form*`, inline formsets `FormSet*`, auth-related forms `Custom*`.
- **Templates:** Located inside each app's `templates/<app>/` folder.
- **Naming Convention:** snake_case for variables/functions, PascalCase for classes.
- **Style:** Follow PEP 8, use Type Hinting.
- **Language:** Code in English; all user-facing text and model `verbose_name` in French, but names of classes, methods, variables, and comments must all be in English.
- **Package manager:** Use `uv` — `uv add <pkg>` to add dependencies, `uv sync` to install. Never suggest `pip install`.

## 5. Signals — auto-sync logic (do not bypass)
Two signals are registered in `annuaire/signals.py` via `AnnuaireConfig.ready()`:
1. **`Account` post-save:** when a new `Account` is created, finds a `Person` with the same email and links them via the `OneToOneField` (`Person.account`). Creating an `Account` manually in tests must account for this.
2. **`Relation` post-save:** automatically creates or updates the inverse `Relation` (parent ↔ enfant, conjoint ↔ conjoint). **Never create inverse `Relation` objects manually.**

## 6. Frontend — Bootstrap 5 / Crispy Forms
Frontend is **Bootstrap 5**. Crispy Forms uses `crispy_bootstrap5` (`CRISPY_TEMPLATE_PACK = 'bootstrap5'`). Use Bootstrap 5 classes in all templates. Do not introduce Bootstrap 4-only patterns (`form-row`, `custom-select`, etc.).

**No REST API:** `djangorestframework` and `dj-rest-auth` are installed but not configured. All views render Django templates. Do not generate serializers or API views unless explicitly asked.

## 7. Working agreements
- **Be concise:** code snippets first, brief explanations after.
- **New view → new tests:** every new view needs a test block (see `/test-select`).
- **Tests gate commits:** a commit may only happen after a fully green test run, or when the user explicitly chose to commit without tests.
- **End-of-task ritual:** at the end of a task with changes, offer the A/B/C choice
  (run tests + commit / run tests + report / commit without tests), stating which test
  files apply. Never commit or run tests without that explicit choice. Detailed test
  scope rules live in `/test-select`.
- **Migrations:** gitignored and never committed — run `makemigrations`/`migrate` locally
  after model changes (details in `dev-commands`).

## 8. Branch Model
| Branch | Role | How to merge in |
|--------|------|-----------------|
| `main` | Protected — stable releases only | PR from `develop` or `hotfix/*` only. Never push directly. No squash. |
| `develop` | Integration branch | Direct push allowed. Receives squash-merges from issue branches. |
| `<type>/issue-<N>/<summary>` | One GitHub issue = one branch | Sub-branch of `develop`. Squash-merge into `develop` when green (see `issue-workflow`). |
| `hotfix/<name>` | Urgent fix on top of `main` | Branch from `main`. PR back to `main` (no squash). Then merge `main` → `develop`. |

### Merge rules
- **Issue branch → `develop`:** local squash-merge (`git merge --squash`), one commit per
  issue, no PR required. Commit message: `<type>: <summary> (#<issue-number>)`.
- **`develop` → `main`:** PR only, **no squash** — `develop`'s history (already one
  squash-commit per issue) is preserved as-is on `main`. See `release-workflow`.
- **Hotfix → `main`:** PR only, no squash. Immediately after merging, merge `main` back
  into `develop` so the hotfix isn't lost on the next release.
- Never push directly to `main`.

### Hard rules (all git work, run directly in the main session)
- Never force-push (`--force`, `-f`).
- Never skip hooks (`--no-verify`).
- Never amend a published commit.
- Never commit without being asked to (outside an approved issue/release flow).

## 9. Toolchain
- **Test command:** `uv run --group test pytest` (see `/test-select` and `dev-commands`).
- **Full test suite runtime:** ~<TBD>s for <TBD> tests (measure and fill in — grows as
  the app grows; re-measure occasionally). `/test-select` uses this figure to decide
  whether to just run the full suite instead of computing a scoped subset.
- No linter/formatter is configured yet (no ruff/black/flake8 in `pyproject.toml`) —
  follow PEP 8 by hand per section 4 until one is added.
