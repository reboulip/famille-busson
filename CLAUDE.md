# Project Context: [PROJECT_NAME]

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

> *Note to AI: Always use `get_user_model()` or `settings.AUTH_USER_MODEL` in ForeignKeys. Never reference `django.contrib.auth.models.User`. Access the profile from a user instance via `user.profile`.*

## 3. Project Structure
- **Root Directory:** `famille_busson`
- **Main App (Settings):** `famille_busson`
- **Functional Apps:**
    - `annuaire`: Manages users (`Person`), family relations (`Relation`), chalets (`Chalet`), and presences (`PresencePSV`)

## 4. Coding Standards & Preferences
- **Views:** Class-Based Views preferred. Ownership checks go in `get_object()`, raising `PermissionDenied`.
- **Forms:** ModelForms prefixed `Form*`, inline formsets `FormSet*`, auth-related forms `Custom*`.
- **Templates:** Located inside each app's `templates/<app>/` folder.
- **Naming Convention:** snake_case for variables/functions, PascalCase for classes.
- **Style:** Follow PEP 8, use Type Hinting.
- **Language:** Code in English; all user-facing text and model `verbose_name` in French, but names of classes, methods, variables, and comments must all be in English
- **Package manager:** Use `uv` — `uv add <pkg>` to add dependencies, `uv sync` to install. Never suggest `pip install`.

## 5. Current State of Development
- **Database Status:** Freshly reset. Migrations are clean.
- **Completed Features:**
    - Custom User Model `Personne` implemented.
- **In Progress:**

## 6. Signals — auto-sync logic (do not bypass)
Two signals are registered in `annuaire/signals.py` via `AnnuaireConfig.ready()`:
1. **`Compte` post-save:** when a new `Compte` is created, finds a `Personne` with the same email and links them via the `OneToOneField`. Creating a `Compte` manually in tests must account for this.
2. **`Relation` post-save:** automatically creates or updates the inverse `Relation` (parent ↔ enfant, conjoint ↔ conjoint). **Never create inverse `Relation` objects manually.**

## 7. Frontend — Bootstrap 5 / Crispy Forms
Frontend is **Bootstrap 5**. Crispy Forms uses `crispy_bootstrap5` (`CRISPY_TEMPLATE_PACK = 'bootstrap5'`). Use Bootstrap 5 classes in all templates. Do not introduce Bootstrap 4-only patterns (`form-row`, `custom-select`, etc.).

**No REST API:** `djangorestframework` and `dj-rest-auth` are installed but not configured. All views render Django templates. Do not generate serializers or API views unless explicitly asked.

## 8. Common Commands Reference
- **Run Server:** `uv run python manage.py runserver` (from `famille_busson/`)
- **Migrate:** `uv run python manage.py makemigrations` / `uv run python manage.py migrate`
- **Shell:** `uv run python manage.py shell`
- **Add dependency:** `uv add <package>`
- **Install deps:** `uv sync`

## 9. Tests
- **Install test deps (once):** `uv sync --group test` (from repo root)
- **Run all tests:** `uv run --group test pytest` (from repo root)
- **Run a single file:** `uv run --group test pytest famille_busson/annuaire/tests/test_views_auth.py`
- **Run multiple files:** `uv run --group test pytest famille_busson/annuaire/tests/test_views_auth.py famille_busson/annuaire/tests/test_views_profile.py`
- **HTML coverage report:** `uv run --group test pytest --cov-report=html` → open `htmlcov/index.html`

Tests live in `famille_busson/annuaire/tests/`. Shared fixtures (accounts, persons, chalets) are in `conftest.py`. CI runs automatically on push to `develop` and `main` via `.github/workflows/tests.yml`.

**Test scope selection:** When running tests, select the minimal relevant scope based on the changes made:
- **Single view/form change** → run only the corresponding test file(s) (e.g. `test_views_chalets.py` for chalet views)
- **Model change** → run the full suite (models underpin everything)
- **Settings / middleware / signals change** → run the full suite
- **Mass refactoring or cross-cutting change** → run the full suite
- **New feature confined to one area** → run that area's test file(s) plus `conftest.py`-dependent files if fixtures changed
When in doubt, prefer the full suite. Always state which files you are running and why.

## 10. Git workflow
- **Branches:** `develop` for active development, `main` for stable releases. Always work on `develop`.
- **Migrations are gitignored:** `migrations/` is in `.gitignore` and is never committed. After cloning or pulling model changes, always run `python manage.py makemigrations` then `python manage.py migrate`. Never assume migrations exist in the repo.
- **Also gitignored:** `db.sqlite3`, `.env`, `famille_busson/static/`, `famille_busson/media/`.

## 11. Instructions for Claude
1. **Always verify migrations:** Before suggesting a model change, remind me of the impact on the Custom User Model.
2. **Be Concise:** Provide code snippets first, followed by brief explanations.
3. **Check Imports:** Ensure `from django.conf import settings` is used when referencing the User model in ForeignKeys.
4. **End-of-task ritual:** At the end of every task, propose the appropriate options depending on whether tests have already been run during the task:
   - **If tests were NOT run during the task**, offer all three and state which test files would be run:
     - **A)** Run relevant tests and commit if they all pass
     - **B)** Run relevant tests and report results (no commit)
     - **C)** Commit immediately without running tests
   - **If tests were already run and are green**, only offer:
     - **A)** Commit (tests already passed)
     - **B)** Don't commit yet
   Never commit or run tests without this explicit choice. Always apply the scope selection rule from section 9 to decide which files to run.
5. **Tests gate commits:** If tests were run and any failed, do not commit — report the failures instead. A commit may only happen after a fully green test run (or the user explicitly chose to commit without tests).
6. **Test changes:** New tests can be written freely. Modifying or deleting existing tests requires presenting the change and waiting for user approval first.
7. **New view → new tests:** Every new view (function or class-based) must be accompanied by a corresponding test block in the appropriate test file. Do not consider a view complete until its tests are written and passing.
