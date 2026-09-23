# Background task queue

Some work runs in the background, outside web requests. There are two kinds:

- **scheduled jobs**, which run at fixed times (for example, every day at 07:00);
- **on-demand tasks**, which run right after something happens (for example, a new
  blog post).

Both use [django-q2](https://django-q2.readthedocs.io/). The queue is stored in the
same Valkey server as the cache (see [Shared cache](deployment.md#shared-cache)).

## Why

These jobs used to run from a crontab on the server. The crontab was set up by hand,
and failures were invisible. With a job queue:

- you can see the schedules and recent runs in the Django admin;
- a job that fails is tried again;
- all logs are in one place: `docker logs` on the `worker` container.

## Architecture

- **`cache` container** (Valkey) — stores the queue.
- **`worker` container** — runs the jobs (`manage.py qcluster`). It uses the same image
  and the same file folders as `web`. It does not run migrations or other startup tasks.
- **`sync_scheduled_tasks`** — a command that creates or updates the list of scheduled
  jobs. The `web` container runs it at each start. You can run it again safely: it never
  creates duplicates and never delays a job that is already scheduled.
- **Task code** — in each app's `tasks.py`. Each scheduled job also has a management
  command, so you can run it by hand (see [Scheduled tasks](deployment.md#scheduled-tasks)).
  The job and the command call the same code.

## Current scheduled jobs

| Job | When | Notes |
|---|---|---|
| Birthday reminders | Every day, 07:00 UTC | A lock makes sure the reminders are never sent twice on the same day. |
| Document text extraction | Every 15 minutes | Only processes documents not yet processed. |
| Photo thumbnails | Every 15 minutes | Safety net for photos uploaded while the worker was down. Normally, thumbnails are made right after upload (see below). |
| Search index rebuild | Every day, 03:00 UTC | Safety net. The index is normally updated on each save (see below). |
| Event reminders | Every day, 08:00 UTC | Emails about events that start within 2 days. Each event is reminded only once. People who answered "non" to the event get no reminder. |
| Trash purge | Every day, 05:00 UTC | Deletes for good the items that have been in the trash for more than 30 days (`TRASH_RETENTION_DAYS`). See [`corbeille.md`](corbeille.md). |

## On-demand tasks

These tasks start as soon as something happens, not at a fixed time.

| Trigger | What the task does |
|---|---|
| A new blog post | Emails each subscriber. There is one task per subscriber, so if one email fails, only that one is tried again. |
| A new event | Emails each subscriber who can see the event. For an event restricted to some groups, only members of those groups get an email. |
| A new photo | Makes a thumbnail and a web-size version, and reads the photo's date and orientation. |
| A person, post, document, album or photo is saved or deleted | Updates the search index for that item. |

These tasks start only after the change is fully saved in the database. This is
important: for example, an event's groups are saved just after the event itself. If the
task started too early, it would see no groups and email everyone.

A task receives only simple values (an id, an email address). It reads the rest from
the database when it runs, so its data is always up to date.

## Local development

In development and in tests, tasks run immediately, in the same process. You do not
need a worker or Valkey. To test a real worker locally, run
`uv run python manage.py qcluster`, with a Valkey server at `QUEUE_URL`.

## Monitoring

- In the Django admin: the `django_q` section shows the schedules, the recent tasks and
  the failures.
- `docker logs` on the `worker` container.
