---
name: dev-commands
description: Common Django dev commands for famille-busson — run server, makemigrations/migrate, shell, manage uv deps, and populate_dev_data (dev fixtures + test credentials). Use when starting the server, resetting the dev DB, adding a dependency, or needing dev/test login credentials.
---

# Dev commands (famille-busson)

> For routine non-destructive commands, delegate to the **dev-runner** subagent (haiku).

All commands run from the repo root.

- **Run server:** `uv run python manage.py runserver`
- **Migrate:** `uv run python manage.py makemigrations` / `uv run python manage.py migrate`
- **Shell:** `uv run python manage.py shell`
- **Add dependency:** `uv add <package>` (never `pip install`)
- **Install deps:** `uv sync`

## Populate dev data
`uv run python manage.py populate_dev_data`

- Wipes existing data from all app models and recreates a deterministic fixture (seeded).
  Pass `--no-clear` to append, or `--seed <N>` to change the seed.
- **Test credentials:**
  - **Superuser:** `admin@example.com` / `admin`
  - **Staff (non-superuser):** `staff@example.com` / `staff`
  - **Regular user:** any of the 20 generated accounts, e.g.
    `paul.bernard.0@example.com` / `dev` (password is `dev` for all regular users)
- Full dev DB reset: `rm db.sqlite3 && uv run python manage.py migrate && uv run python manage.py populate_dev_data`
- Always ask for user approval before performing a destructive action like wiping the DB.

## Migrations & gitignored paths
- `migrations/` is in `.gitignore` and is **never committed**. After cloning or pulling
  model changes, always run `makemigrations` then `migrate`. Never assume migrations
  exist in the repo.
- Also gitignored: `db.sqlite3`, `.env`, `/static/`, `/media/`.
