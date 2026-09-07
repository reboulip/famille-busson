# Background task queue

famille-busson runs both recurring (scheduled) and on-demand background work through
[django-q2](https://django-q2.readthedocs.io/), backed by the same Valkey instance the
shared cache uses (see [`deployment.md`'s "Shared cache"
section](deployment.md#shared-cache)) — cache on db 0, this queue's broker on db 1.
On-demand work enqueues a task directly (e.g. `publications/signals.py`, on every new
blog post) rather than waiting for a `Schedule` row's next tick — see "On-demand tasks"
below.

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
  `Schedule` row). Neither a task function nor its management command owns the actual
  logic itself — both call the same extracted callable
  (`annuaire.birthdays.send_birthday_reminders`,
  `documents.tasks.process_pending_document_files`); the management commands are thin
  wrappers around it too, kept hand-runnable for ad-hoc use (see `deployment.md`'s
  "Scheduled tasks" section).

## Current scheduled jobs

| Job | Schedule | Task | Notes |
|---|---|---|---|
| Birthday reminders | Daily, 07:00 UTC | `annuaire.tasks.send_daily_birthday_reminders` | Guarded by a same-day cache lock, so a `catch_up` run or an overlap with the old crontab entry during a deploy can never send the same day's reminders twice. |
| Document extraction | Every 15 minutes | `documents.tasks.process_pending_document_files` | Naturally idempotent — only ever processes rows still `extraction_status="pending"`. |

## On-demand tasks

Enqueued directly from a signal or view, rather than a `Schedule`, whenever the work
should happen as soon as possible after an event rather than on a fixed tick.

| Trigger | Task | Notes |
|---|---|---|
| A new `BlogPost` is saved | `publications.tasks.send_blog_post_notification(post_pk, recipient_email)` | Enqueued once per subscriber from `publications/signals.py`'s `post_save` receiver, inside `transaction.on_commit` so the enqueue waits for the post (and its M2M authors) to actually be committed. The task re-queries the post fresh and calls `annuaire.email_utils.send_one_email`, which raises on failure so django-q2 retries that one recipient — a provider hiccup no longer silently drops the whole batch, and one recipient's failure never affects another's. A deleted post is logged and skipped, not retried (retrying can't make it exist again). |

Enqueue by plain values (a PK, an email string), never a built message or model
instance — the task re-queries current state itself, so nothing enqueued can go stale or
fail to serialize between enqueue and execution.

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
