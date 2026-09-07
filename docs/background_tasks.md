# Background task queue

famille-busson runs recurring and (starting with a later item) on-demand background
work through [django-q2](https://django-q2.readthedocs.io/), backed by the same Valkey
instance the shared cache uses (see [`deployment.md`'s "Shared cache"
section](deployment.md#shared-cache)) — cache on db 0, this queue's broker on db 1.

## Why

Before this, `send_birthday_reminders` and `extract_document_content` ran on the VPS's
crontab, set up by hand outside CI/CD, with cron's own output going nowhere on failure.
A job runner gives them: schedules and recent run history visible in the Django admin,
retries on transient failure, and one place (`docker logs` on the `worker` container)
to check instead of a crontab nobody remembers configuring.

## Architecture

- **`cache` container** (Valkey) — broker for both the Django cache and this queue.
- **`worker` container** — runs `python manage.py qcluster`, the same image as `web`,
  same `media`/`documents_data` volume mounts (a job that touches either of those must
  see the same files `web` does). `RUN_STARTUP_TASKS=0` so it never runs
  migrate/collectstatic/schedule-sync itself — only `web` does, once per deploy.
- **`sync_scheduled_tasks`** management command — idempotently registers this
  project's `Schedule` rows (`annuaire.management.commands.sync_scheduled_tasks`), run
  automatically by `web` on every startup via `docker-entrypoint.sh`. Safe to run
  repeatedly: existing schedules are matched by name and updated in place, never
  duplicated, and a schedule's `next_run` is only set the first time it's created —
  a routine deploy never pushes an already-ticking schedule's next occurrence back out.
- **Task modules** — `annuaire/tasks.py` and `documents/tasks.py`, one per app. Each
  function is plain and importable (django-q2 calls it by dotted path from a
  `Schedule` row); the management commands remain the source of truth for the actual
  logic and stay hand-runnable (see `deployment.md`'s "Scheduled tasks" section) —
  tasks call the same extracted callable a command calls, never the other way around.

## Current scheduled jobs

| Job | Schedule | Task | Notes |
|---|---|---|---|
| Birthday reminders | Daily, 07:00 UTC | `annuaire.tasks.send_daily_birthday_reminders` | Guarded by a same-day cache lock, so a `catch_up` run or an overlap with the old crontab entry during a deploy can never send the same day's reminders twice. |
| Document extraction | Every 15 minutes | `documents.tasks.process_pending_document_files` | Naturally idempotent — only ever processes rows still `extraction_status="pending"`. |

## Local development

`Q_CLUSTER["sync"]` defaults to `DEBUG`'s value, and `conftest.py` forces it to `True`
for the whole test suite — a task enqueued via `django_q.tasks.async_task()` then runs
inline, in the same process, instead of needing a real worker or broker. To run a real
worker locally (e.g. to test `qcluster` itself): `uv run python manage.py qcluster`,
with a Valkey instance reachable at `QUEUE_URL` (or `Q_SYNC=False` unset, which is the
default outside `DEBUG`).

## Monitoring

There's no dedicated dashboard yet beyond the Django admin's `django_q` models
(`Schedule`, `Task`, `Failure`) and `docker logs` on the `worker` container — structured
error monitoring is a later item.
