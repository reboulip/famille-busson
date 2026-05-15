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
- **Model Name:** `Compte`
- **Settings:** `AUTH_USER_MODEL = 'annuaire.Compte'`
- **Inheritance:** Inherits from AbstractBaseUser

> *Note to AI: Always use `get_user_model()` or refer to `annuaire.Personne` for ForeignKeys. Never suggest using the default `django.contrib.auth.models.User`.*

## 3. Project Structure
- **Root Directory:** `famille_busson`
- **Main App (Settings):** `famille_busson`
- **Functional Apps:**
    - `annuaire`: Manages users (Personne)

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
Target frontend is **Bootstrap 5**. Crispy Forms is currently wired to `crispy_bootstrap4` (pending migration — see ROADMAP). When writing new templates, use Bootstrap 5 classes. Do not introduce Bootstrap 4-only patterns (`form-row`, `custom-select`, etc.).

**No REST API:** `djangorestframework` and `dj-rest-auth` are installed but not configured. All views render Django templates. Do not generate serializers or API views unless explicitly asked.

## 8. Common Commands Reference
- **Run Server:** `python manage.py runserver` (from `famille_busson/`)
- **Migrate:** `python manage.py makemigrations` / `python manage.py migrate`
- **Shell:** `python manage.py shell`
- **Add dependency:** `uv add <package>`
- **Install deps:** `uv sync`

## 9. Git workflow
- **Branches:** `develop` for active development, `main` for stable releases. Always work on `develop`.
- **Migrations are gitignored:** `migrations/` is in `.gitignore` and is never committed. After cloning or pulling model changes, always run `python manage.py makemigrations` then `python manage.py migrate`. Never assume migrations exist in the repo.
- **Also gitignored:** `db.sqlite3`, `.env`, `famille_busson/static/`, `famille_busson/media/`.

## 10. Instructions for Claude
1. **Always verify migrations:** Before suggesting a model change, remind me of the impact on the Custom User Model.
2. **Be Concise:** Provide code snippets first, followed by brief explanations.
3. **Check Imports:** Ensure `from django.conf import settings` is used when referencing the User model in ForeignKeys.
