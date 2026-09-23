# Observability

How to find out that something is wrong, and how to read the logs.

## Structured logging

`LOG_FORMAT` chooses the log format:

- `console` (default when `DEBUG` is on) — plain text, easy to read in a terminal.
- `json` (default in production) — one JSON object per line, easy for tools to search.

Each JSON line has these fields:

| Key | Always present? | Meaning |
|---|---|---|
| `timestamp` | yes | Date and time, in UTC. |
| `level` | yes | `INFO`, `WARNING`, `ERROR`, etc. |
| `logger` | yes | The logger name (usually the Python module). |
| `message` | yes | The log message. |
| `module` | yes | The Python module that wrote the log. |
| `line` | yes | The line number in that module. |
| `request_id` | when available | See below. |
| `exception` | on errors | The error traceback. |

Extra values passed with `logger.info(..., extra={...})` are added as more fields.

## Request correlation

Each web request gets an id. If the reverse proxy sends an `X-Request-ID` header, the
app uses it. Otherwise it creates one. The id is sent back in the response's
`X-Request-ID` header, and added to every log line written during that request. To see
everything that happened during one request, search the logs for its `request_id`.

Background tasks run in another process, so their log lines do **not** carry the id of
the request that started them.

## Error monitoring (Sentry)

Sentry is only active when `SENTRY_DSN` is set. By default it is empty, so development,
CI and tests do not use Sentry.

- **No personal data is sent.** The site holds personal data about real people. Sentry
  never receives cookies or values named `email`.
- **Errors only.** Performance monitoring is off. A family site does not need it, and
  it would use up the free quota.
- Each error is tagged with the app version and the environment (`SENTRY_ENVIRONMENT`,
  default `production`, or `development` when `DEBUG` is on).
- If `SENTRY_DSN` is missing in production, the app shows the warning `annuaire.W003`
  at startup (see [`deployment.md`](deployment.md#environment-variables)).

**Set up once:** create a Sentry project (the free plan is enough), and copy its DSN
into `SENTRY_DSN` in `/srv/bubu/.env`. There is nothing else to configure.

## `/healthz`

`/healthz` checks the database, cache, queue and file storage. Docker and an external
uptime monitor use it. See [`/healthz`](deployment.md#healthz) for details.
