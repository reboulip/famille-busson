# Observability

How to find out something is wrong without reading `docker logs` first, and how to
read the logs once you do.

## Structured logging

`LOG_FORMAT` selects the output shape, independent of `DEBUG`:

- `console` (default under `DEBUG`) — plain, human-readable lines, for a dev terminal.
- `json` (default outside `DEBUG`) — one JSON object per line, for `docker logs` /
  a log aggregator to parse.

A root (`""`) logger was added in `famille_busson/settings.py`'s `LOGGING` — previously
only `django`/`django.request` were configured, so any `logging.getLogger(__name__)`
call elsewhere (e.g. `annuaire/file_cleanup.py`) fell through to Python's unformatted
`lastResort` handler. Every logger now reaches a handler either way.

**JSON record schema** (`annuaire/log_formatters.py`'s `JsonFormatter`), fixed keys:

| Key | Always present? | Meaning |
|---|---|---|
| `timestamp` | yes | ISO-8601 UTC, millisecond precision, `Z` suffix. |
| `level` | yes | `INFO`, `WARNING`, `ERROR`, etc. |
| `logger` | yes | The logger's name (`"django"`, or a module's `__name__`). |
| `message` | yes | The formatted log message. |
| `module` | yes | The Python module the log call came from. |
| `line` | yes | Line number of the log call. |
| `request_id` | if available | See below. |
| `exception` | on `logger.exception(...)`/`exc_info=True` | Rendered traceback string. |

Anything else passed via `logger.info(..., extra={...})` merges in at the top level,
alongside these. A fixed key set (rather than free-form) is what keeps a log search
over JSON output stable as the codebase grows.

## Request correlation

`annuaire.middleware.RequestIdMiddleware` tags every request with an id (an inbound
`X-Request-ID` header if the reverse proxy already sets one, otherwise a generated
one), echoes it back in the response's `X-Request-ID` header, and makes it available
to every log line emitted while handling that request via a `contextvars`-backed log
filter — no call site needs to pass `request_id` by hand. This is what lets every log
line emitted synchronously while handling one request (a view, a signal fired during
it) be grepped together by `request_id` when something goes wrong.

In production, the `contextvars` value doesn't cross into the [background
queue](background_tasks.md): a task a signal enqueues runs in a separate `worker`
process, which never shares the request's `contextvars` context, so its own log lines
won't carry the enqueuing request's id unless it's explicitly passed along as a task
argument — none of the current tasks do. (Under `Q_CLUSTER["sync"]`, dev/tests' mode,
the task runs inline on the same call stack and happens to inherit the id there —
don't rely on that holding in production.)

## Error monitoring (Sentry)

Guarded entirely on `SENTRY_DSN` being set — empty (the default) means `sentry_sdk`
is never initialized, so dev/CI/tests are completely unaffected regardless.

- **`send_default_pii=False`, always.** This site holds personal data on identifiable
  EU residents (see Phase 14 in `ROADMAP.md`). A `before_send` hook additionally drops
  `request.cookies` wholesale and any `extra`/`contexts` value filed under a key
  literally named `email` (case-insensitive), from any source.
- **Errors only** — `traces_sample_rate=0.0` and `profiles_sample_rate=0.0`.
  Performance/profiling monitoring is explicitly out of scope; a family site has no
  need for it and it would burn a free-tier event quota for no benefit.
- **`release`** is `settings.APP_VERSION` (already read from `pyproject.toml`) and
  **`environment`** is `SENTRY_ENVIRONMENT` (defaulting to `"development"` under
  `DEBUG`, `"production"` otherwise) — both free, since they're already computed.
- A warning-level system check (`annuaire.checks`, id `annuaire.W003`) flags a
  missing `SENTRY_DSN` outside `DEBUG`, same rationale as `W001`/`W002`: it can't
  safely be an error (checks run before `collectstatic` at container boot under
  `set -euo pipefail`), but a silently-never-initialized tracker is worth surfacing.

**Manual VPS setup, once:** create a Sentry project (SaaS free tier), copy its DSN
into `/srv/bubu/.env`'s `SENTRY_DSN`. Nothing else needs configuring — the sampling
rates and PII handling above are fixed in code, not left to the Sentry project's
own defaults.

## `/healthz`

Checks the database, cache, queue and storage backends, wired into the compose
healthcheck and an external uptime monitor — see [`deployment.md`'s `/healthz`
section](deployment.md#healthz) for the response contract and criticality rules.
