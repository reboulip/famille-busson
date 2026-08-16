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
Three signals are registered in `annuaire/signals.py` via `AnnuaireConfig.ready()`:
1. **`Account` post-save:** when a new `Account` is created, finds a `Person` with the same email and links them via the `OneToOneField` (`Person.account`). Creating an `Account` manually in tests must account for this.
2. **`Relation` post-save:** automatically creates or updates the inverse `Relation` (parent ↔ enfant, conjoint ↔ conjoint). **Never create inverse `Relation` objects manually.**
3. **`Relation` post-delete:** automatically deletes the matching inverse `Relation` too. Deleting a `Relation` directly (e.g. `Relation.objects.filter(...).delete()`), not just through `DeleteRelationView`, removes both sides.

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
- **Migrations:** committed to git — run `makemigrations` after model changes and include
  the generated file(s) in your commit (details in `dev-commands`). Required for
  production: the Docker image is built from a fresh `git checkout`, so an uncommitted
  migration never reaches the deployed Postgres database. Run `migrate` locally too, to
  apply it to your dev SQLite DB.

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
- **Full test suite runtime:** ~1490s (~25 min) for 214 tests (measured 2026-08-15,
  no-cov) — **abnormally slow for this test count; likely a real bug (hanging
  connection, sleep, or network call in a fixture/test), not just test-count growth.**
  Re-measure after investigating rather than accepting this as the new normal.
  `/test-select` uses this figure for its cheap-suite escape hatch — well past the
  ~120s threshold, so it will always compute a scoped subset here rather than just
  running everything.
- No linter/formatter is configured yet (no ruff/black/flake8 in `pyproject.toml`) —
  follow PEP 8 by hand per section 4 until one is added.

## 10. Releases
famille-busson is a continuously-deployed web app, not a published package — there's no
PyPI/npm artifact, so versioning exists purely to mark **what shipped and when**, not to
gate a build/publish step.

- **Scheme:** SemVer (`vX.Y.Z`), tracked in `pyproject.toml`'s `version` field.
- **Bump convention (part of `release-workflow`, done on `develop` before opening the
  develop → main PR):** any `feat:` commit shipping → **minor**; else any `fix:` → **patch**;
  `chore:`/`docs:`/`refactor:`/`test:` only → ask the user whether it's release-worthy.
  Commit message: `chore: bump version to X.Y.Z`.
- **Tag + GitHub Release are automatic:** `.github/workflows/release.yml` triggers on
  every push to `main`. It reads `pyproject.toml`'s `version`; if `v<version>` isn't
  already tagged, it tags the merge commit and creates a GitHub Release with
  auto-generated notes. It never commits back to `main` (only pushes a tag), so it needs
  no exception to `main`'s branch-protection rules (PR + green `test` check) — the
  default `GITHUB_TOKEN` with `contents: write` is enough. If a push to `main` carries no
  version bump (shouldn't happen via `release-workflow`, but possible via a hand-pushed
  hotfix), the workflow silently no-ops rather than re-tagging.
- **Hotfixes** bump the patch version on the `hotfix/*` branch itself, so the PR into
  `main` still carries a version change for the workflow to tag (see `release-workflow`'s
  Hotfix variant).
- No build/publish step, no changelog file — the GitHub Release's auto-generated notes
  (grouped by merged PRs since the last tag) are the changelog.

## 11. Documentation
- **`docs/`** holds project documentation. `docs/README.md` indexes it.
- **`docs/data_model.md`** — ER diagram + field tables for `annuaire`/`publications`
  models. **Auto-generated, never edit by hand** — regenerate with
  `uv run python manage.py generate_data_model_docs` (see `dev-commands`) after any
  `models.py` change. Generator: `annuaire/management/commands/generate_data_model_docs.py`.
- **`ROADMAP.md`** tracks pending work only. Shipped items move to
  **`docs/ROADMAP_ARCHIVE.md`** at develop → main release time (see `release-workflow`).
