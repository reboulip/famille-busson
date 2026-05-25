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
- **Run Server:** `uv run python manage.py runserver` (from repo root)
- **Migrate:** `uv run python manage.py makemigrations` / `uv run python manage.py migrate`
- **Shell:** `uv run python manage.py shell`
- **Add dependency:** `uv add <package>`
- **Install deps:** `uv sync`
- **Populate dev data:** `uv run python manage.py populate_dev_data`
  - Wipes existing data from all app models and recreates a deterministic fixture (seeded). Pass `--no-clear` to append, or `--seed <N>` to change the seed.
  - Test credentials:
    - **Superuser:** `admin@example.com` / `admin`
    - **Staff (non-superuser):** `staff@example.com` / `staff`
    - **Regular user:** any of the 20 generated accounts, e.g. `paul.bernard.0@example.com` / `dev` (password is `dev` for all regular users)
  - Use this after `rm db.sqlite3 && uv run python manage.py migrate` to fully reset a dev DB.

## 9. Tests
- **Install test deps (once):** `uv sync --group test` (from repo root)
- **Run all tests:** `uv run --group test pytest` (from repo root)
- **Run a single file:** `uv run --group test pytest annuaire/tests/test_views_auth.py`
- **Run multiple files:** `uv run --group test pytest annuaire/tests/test_views_auth.py annuaire/tests/test_views_profile.py`
- **HTML coverage report:** `uv run --group test pytest --cov-report=html` → open `htmlcov/index.html`

Tests live in `annuaire/tests/` and `publications/tests/`. Shared fixtures (accounts, persons, chalets) are in `annuaire/tests/conftest.py`; `publications/tests/conftest.py` re-uses them. CI runs automatically on push to `develop` and `main` via `.github/workflows/tests.yml`.

**Test scope selection:** When running tests, select the minimal relevant scope based on the changes made:
- **Single view/form change** → run only the corresponding test file(s) (e.g. `test_views_chalets.py` for chalet views)
- **Model change** → run the full suite (models underpin everything)
- **Settings / middleware / signals change** → run the full suite
- **Mass refactoring or cross-cutting change** → run the full suite
- **New feature confined to one area** → run that area's test file(s) plus `conftest.py`-dependent files if fixtures changed
When in doubt, prefer the full suite. Always state which files you are running and why.

## 10. Git workflow

### Branch model
| Branch | Role | Direct push? |
|--------|------|-------------|
| `main` | Stable releases | Never — PR only, one commit per issue |
| `develop` | Integration branch | Yes (via squash-merge of issue branches, no PR) |
| `<type>/issue-<N>/<summary>` | One issue = one branch | Yes (your own branch) |

### Issue-driven workflow (issue → develop)
When asked to work on a GitHub issue:
1. Fetch the issue details: `gh issue view <number>`
2. **If the issue is ambiguous, contradictory, or missing acceptance criteria, ask the user clarifying questions before writing any code.** Cover scope ("does this also cover X?"), UX choices that aren't obvious from the description, and edge cases the issue doesn't mention. It is far cheaper to ask up-front than to ship the wrong thing and revert. Skip this step only when the issue is genuinely self-explanatory.
3. Infer the branch `<type>` from the issue description (see types below).
4. Create the branch from up-to-date `develop` (hotfixes from `main`):
   ```
   git checkout develop && git pull origin develop
   git checkout -b <type>/issue-<number>/<short-summary>
   ```
5. Implement, run the relevant tests (per §9 scope rule), commit on the branch.
6. If tests are green, **squash-merge directly into `develop`** locally — no PR:
   ```
   git checkout develop && git pull origin develop
   git merge --squash <type>/issue-<number>/<short-summary>
   git commit -m "<type>: <summary> (#<issue-number>)"
   git push origin develop
   git branch -D <type>/issue-<number>/<short-summary>      # local cleanup
   git push origin --delete <type>/issue-<number>/<short-summary>   # remote cleanup (if pushed)
   ```
7. **Immediately after the merge to develop**, post a French resolution comment on the GH issue. Merging is your assertion that the issue is fixed, so this comment is the proof-of-work the user reads before testing on `develop`. Always end the comment with `*Message généré par Claude.*` so the user can tell at a glance who wrote it.
   ```
   gh issue comment <issue-number> --body "**Résolu sur \`develop\`** (commit <develop-sha>).

   <2-4 short bullets: what was changed, in which file/area>

   <1 sentence on WHY this resolves the issue — link the change back to the problem statement>

   *Message généré par Claude.*"
   ```
   Do not close the issue here — closing happens in the release workflow once the commit ships to `main`.
8. If tests fail, fix on the branch and re-run. Never merge a red branch into `develop`.
9. Working in parallel on multiple issues is fine — rebase each issue branch onto `develop` as often as needed to stay current:
   ```
   git checkout <type>/issue-<N>/<summary>
   git fetch origin && git rebase origin/develop
   ```

### Release workflow (develop → main)
Triggered explicitly by the user ("ouvre la PR vers main", "release time", etc.). Never start this on your own.

**Goal: each shipped issue is one commit on `main`** (one `fix:` / `feat:` / etc. per issue, with the issue number in the subject). This makes `git log main` a clean release history that aligns 1-to-1 with closed issues.

**Why not a direct `develop → main` PR?** `main` was originally built from squash-merges, so develop's history contains many individual commits whose content was already shipped to main as squashes. A direct `develop → main` rebase-and-merge replays those old commits (conflicts/duplicates) and a squash collapses every shipped issue into one indistinguishable blob. Cherry-picking the relevant commits onto a release branch sidesteps both problems.

**Steps:**
1. Identify the develop commits to ship (typically the new issue commits since the last release, plus any chore/docs commits the user has explicitly approved for `main`).
2. Create a release branch from up-to-date `main`:
   ```
   git checkout main && git pull origin main
   git checkout -b release/<short-summary>
   ```
   The short summary can be the issue numbers (e.g. `release/issues-3-4-5-6`) or a thematic name.
3. Cherry-pick the chosen develop commits in chronological order (oldest first). After each `git cherry-pick <sha>`, immediately `git commit --amend -m "<clean-message>"` to drop any trailing PR-number suffix added by GitHub squash-merges. The final per-issue commit message must be `<type>: <summary> (#<issue-number>)`.
4. Push the release branch: `git push -u origin release/<short-summary>`.
5. Open the PR to main:
   ```
   gh pr create --base main --head release/<short-summary> --title "release: <short summary>" --body "<table of shipped issues>"
   ```
6. Wait for CI to go green (poll with `gh pr checks <N> --watch --interval 15`, no manual prompts to the user). Repo does not allow auto-merge, so polling is required.
7. **Rebase-merge** (NOT squash): `gh pr merge <N> --rebase`. This replays each cherry-picked commit onto main individually, preserving the 1-commit-per-issue mapping. The repo must allow rebase merges (`allow_rebase_merge=true` — already enabled).
8. Fetch and inspect the new commits on `main`: `git fetch origin && git log origin/main --oneline -<N>`. Capture the SHA of each issue's commit.
9. Close each shipped issue with a French comment that links to its specific main SHA:
   ```
   gh issue close <issue-number> --comment "Livré sur \`main\` en [<sha>](https://github.com/reboulip/famille-busson/commit/<sha>) — \`<commit-message>\`."
   ```
10. Local cleanup: `git checkout main && git pull origin main`, then delete the local release branch and prune the remote (GitHub auto-deletes the remote branch on merge).

**End result:** `main` gains exactly one commit per shipped issue. Each closed issue carries a permalink to its commit. The release branch is ephemeral and gone after merge.

### Branch naming convention
`<type>/issue-<number>/<short-summary>` e.g. `feat/issue-12/person-avatar-upload`

| Type | When to use |
|------|-------------|
| `feat` | New feature or user-visible capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behaviour change |
| `chore` | Dependency update, tooling, CI, config |
| `docs` | Documentation only |
| `test` | Tests only |

### Merge strategy
- Issue → develop: local squash-merge (no PR) — one issue = one commit on `develop`.
- develop → main: cherry-pick the new issue commits onto a `release/<summary>` branch off `main`, open a PR to `main`, **rebase-merge** so each commit lands on `main` individually. Never squash this PR (would collapse multiple issues into one commit) and never rebase-merge straight from `develop` (would replay pre-release commits that are already squashed on `main`).
- Commit message format on both sides: `<type>: <summary> (#<issue-number>)`

### Migrations are gitignored
`migrations/` is in `.gitignore` and is never committed. After cloning or pulling model changes, always run `python manage.py makemigrations` then `python manage.py migrate`. Never assume migrations exist in the repo.

### Also gitignored
`db.sqlite3`, `.env`, `/static/`, `/media/`.

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
8. **GitHub issue workflow:** When asked to work on a GitHub issue, follow §10 exactly. Fetch with `gh issue view <number>`, create the appropriately-named branch from up-to-date `develop` (or `main` for hotfixes), implement, run the relevant tests. If tests pass, squash-merge the branch into `develop` locally and push (no PR). Never push directly to `main`. The user reviews `develop` and triggers the release-to-main PR explicitly.
