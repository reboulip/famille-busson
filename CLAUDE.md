# Project Context: Famille Busson

> Procedures live in skills (auto-loaded when relevant), not here:
> **running-tests** (test commands + scope rules), **dev-commands** (server / migrate /
> shell / uv / populate_dev_data + credentials), **issue-workflow** (GitHub issue →
> develop), **release-workflow** (develop → main). This file holds only the always-on
> facts and gotchas.

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
- **New view → new tests:** every new view needs a test block (see the `running-tests` skill).
- **Tests gate commits:** a commit may only happen after a fully green test run, or when the user explicitly chose to commit without tests.
- **End-of-task ritual:** at the end of a task with changes, offer the A/B/C choice
  (run tests + commit / run tests + report / commit without tests), stating which test
  files apply. Never commit or run tests without that explicit choice. Detailed test
  scope rules live in the `running-tests` skill.
- **Migrations:** gitignored and never committed — run `makemigrations`/`migrate` locally
  after model changes (details in `dev-commands`).
