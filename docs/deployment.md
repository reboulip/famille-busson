# Deployment

famille-busson runs on a single server (`bubu.reboulip.fr`) with Docker. Every push to
`main` deploys a new version automatically. This page explains how the pieces fit
together. To set up a new installation from scratch, see
[`installation.md`](installation.md).

## CI/CD pipeline

Four GitHub workflows (in `.github/workflows/`):

| Workflow | Runs on | What it does |
|---|---|---|
| `tests.yml` | push to `develop` or `main`, and PRs into `main` | Runs the linters and the tests. A PR into `main` must pass it. |
| `build-and-deploy.yml` | push to `main` | Builds the Docker image, pushes it to GHCR, and deploys it to the server over SSH. |
| `release.yml` | push to `main` | Creates the `v<version>` tag and the GitHub Release, using the version in `pyproject.toml`. |
| `dependency-upgrade.yml` | every Friday night, or by hand | Upgrades Python, the Python packages and the front-end libraries, then opens a PR into `main` if all checks pass. |

### Automated dependency upgrades

`dependency-upgrade.yml` is the only workflow that opens a PR into `main` from a branch
other than `develop` or `hotfix/*`. It runs the same checks as a person would: ruff,
ty, the static files check, and the full test suite. If one check fails, it opens no PR.
It always bumps the **minor** version.

Before the ruff and format checks, it first runs `ruff check --fix` and `ruff format`
(safe fixes only, never `--unsafe-fixes`) so a routine style-rule change in the new
ruff version doesn't block the whole upgrade by itself — whatever ruff can't fix on
its own still fails the check gate afterwards. It also installs `gettext` and runs
`manage.py compilemessages` before the test suite, the same as `tests.yml` does,
since some tests (e.g. `test_middleware_user_language.py`) need compiled `.mo` files
to pass. `.pre-commit-config.yaml`'s ruff hooks run through `uv run ruff` rather than
a pinned external revision, so a local commit and this workflow always use the exact
same ruff version from `uv.lock`.

The front-end libraries in `annuaire/static/vendor/` (leaflet, d3, family-chart,
pdfjs, etc.) have no build tool. Their versions are listed in
`annuaire/static/vendor/manifest.json`. The command `manage.py upgrade_vendored_assets`
downloads new versions and updates that file.

## Docker image

The image is built from `Dockerfile`: Python 3.13 slim, plus `uv`. It also installs:

- `tesseract-ocr` and `tesseract-ocr-fra`, to read text from scanned documents (OCR);
- `gettext`, to compile the translation files.

Translations are compiled **when the image is built**, not when the container starts.
This matters because the `worker` container sends emails but skips the startup tasks.
If translations were compiled at startup, its emails would not be translated. See
[`i18n.md`](i18n.md).

The container starts as `root`, then switches to a normal user (see below).

## `docker-entrypoint.sh` — the root → chown → appuser dance

The entrypoint script runs in two passes:

1. **As root:** it gives the `appuser` user ownership of the `media` and `documents`
   folders. These folders come from the server, so their owner is not always correct.
   Then the script restarts itself as `appuser`.
2. **As `appuser`:** it applies database migrations (`migrate`), collects static files
   (`collectstatic`), and starts Gunicorn.

## Production stack (`docker-compose.prod.yml`)

| Service | Image | Notes |
|---|---|---|
| `db` | `postgres:16-alpine` | The database. Data in `${DATA_ROOT}/postgres`. |
| `cache` | `valkey/valkey:8-alpine` | Cache and job queue. Data in `${DATA_ROOT}/valkey`. Not reachable from outside. See "Shared cache" below. |
| `web` | `${APP_IMAGE}` | The Django app. Uploaded files in `${DATA_ROOT}/media` and `${DATA_ROOT}/documents`. Listens on port `${WEB_PORT}`. Health check on `/healthz`. |
| `worker` | `${APP_IMAGE}` | Runs the background jobs (see [`background_tasks.md`](background_tasks.md)). Same image and same folders as `web`. |

The defaults are `DATA_ROOT=/srv/bubu/data`,
`APP_IMAGE=ghcr.io/reboulip/famille-busson:latest` and `WEB_PORT=8001`. Another
installation can change them in `.env` without editing the compose file.

On the server, `/srv/bubu/` holds `docker-compose.yml` (a copy of
`docker-compose.prod.yml`, made by the deploy workflow), `.env`, and the data folders.

### Shared cache

The app reads its cache settings from `CACHE_URL`. In production it points to the
Valkey container. Without it, each Gunicorn worker has its own private memory cache, and
features that need a shared cache (like rate limiting) do not work correctly.

The Valkey container has two roles: database 0 is the Django cache, and database 1 is
the job queue. Two settings are important:

- `--maxmemory-policy noeviction`: Valkey must never drop data when memory is full.
  Otherwise it could lose queued jobs.
- `--appendonly yes`: data, including queued jobs, survives a restart.

In development and in tests, you do not need Valkey. The app uses a memory cache by
default.

### `/healthz`

`/healthz` checks that the database, cache, queue and file storage all work. It returns:

```json
{
  "status": "ok|degraded|error",
  "checks": {
    "database": {"status": "ok", "duration_ms": 1.2},
    "cache": {"status": "ok", "duration_ms": 0.4},
    "queue": {"status": "ok", "duration_ms": 2.1},
    "media_storage": {"status": "ok", "duration_ms": 0.3},
    "documents_storage": {"status": "ok", "duration_ms": 0.3}
  },
  "version": "1.3.0"
}
```

Error details are never shown in the response. They go to the log.

**Not all checks are equally important:**

- If `database`, `media_storage` or `documents_storage` fails, the status is `error`
  and the HTTP code is `503`.
- If `cache` or `queue` fails, the status is `degraded`, but the HTTP code stays `200`.
  A short Valkey problem does not take the whole site down.

**Docker health check:** the `web` container runs `scripts/healthcheck.py` (the image
has no `curl`). If `/healthz` returns `503`, Docker marks the container "unhealthy".
This is only for visibility: nothing restarts the container automatically.

**External monitoring:** set this up by hand. Add `https://bubu.reboulip.fr/healthz`
to a free uptime monitor (for example UptimeRobot), with a keyword check on
`"status": "ok"`.

### Protected document storage

Documents and photos are stored in `/srv/bubu/data/documents`, apart from the normal
`media` folder. They have no public URL. The only way to download one is through the
app, which checks the user's group access on every request. When a file is deleted or
replaced in the app, the old file on disk is removed automatically.

## Environment variables

`.env.example` lists every variable. Copy it to `/srv/bubu/.env` on the server. Never
commit a real `.env`.

The most important points:

- **Database:** `POSTGRES_*` configures the `db` container. `DATABASE_URL` is what
  Django reads. You must keep them in sync by hand.
- **Email:** emails are only logged until you set `EMAIL_BACKEND` to SMTP. Set the
  sender address with `DEFAULT_FROM_EMAIL`, or in the site settings (see
  [`site_config.md`](site_config.md)).
- **`SITE_BASE_URL`:** used to build links in emails sent by background jobs (birthday
  reminders, new post notifications). In production, set it to
  `https://bubu.reboulip.fr`. If it is missing, the app tries to guess it from
  `CSRF_TRUSTED_ORIGINS` or `ALLOWED_HOSTS`.
- **`PRIVACY_*` (five variables):** the legal facts shown on the privacy page. They
  must all be set in production. See
  [`privacy.md`](privacy.md#legal-facts-environment-variables-not-hardcoded).
- **`TIME_ZONE`** (default `Europe/Paris`): the time zone for background jobs and
  management commands. Web pages use the time zone from the site settings instead.
- **`GEOCODER_PRIMARY`** (default `ban`): the service used first to turn an address
  into map coordinates. `ban` is the French national address database. `photon` works
  worldwide. Set `photon` for an installation outside France.
- **`DATA_ROOT`, `APP_IMAGE`, `WEB_PORT`:** read by Docker Compose, not by Django. See
  "Production stack" above.

**Configuration warnings.** When `DEBUG` is off, the app checks its configuration at
startup and shows a warning if something is missing:

| Id | Problem |
|---|---|
| `annuaire.W001` | `SITE_BASE_URL` still points to `localhost`. |
| `annuaire.W002` | No shared cache (`CACHE_URL` not set). |
| `annuaire.W003` | No `SENTRY_DSN` (see [`observability.md`](observability.md)). |
| `annuaire.W004` | A language has no compiled translation file (see [`i18n.md`](i18n.md)). |
| `annuaire.W005` | The site has no name (`bootstrap_site` was never run). |
| `annuaire.W006` | No sender address for emails. |

These are warnings, not errors, on purpose: an error would stop the container from
starting.

## App version

The app reads its version from `pyproject.toml` when it starts. The version appears in
small text in the fixed left sidebar, next to the logout/login control (`v1.5.0`, for
example), and in `/healthz`.

## Scheduled tasks

These jobs run automatically on the job queue (see
[`background_tasks.md`](background_tasks.md)). You can also run each one by hand, for
example to test it or to catch up.

`send_birthday_reminders` emails the members who asked for birthday reminders, for each
person whose birthday is today. It runs once a day. Use `--date YYYY-MM-DD` to run it
for another day, and `--dry-run` to see who would get an email without sending
anything:

```
docker compose exec -T web python manage.py send_birthday_reminders --date 2026-06-10 --dry-run
```

`extract_document_content` reads the text of new documents (so they can be searched)
and makes a preview image for PDFs. It uses OCR for scans and images. Office and plain
text files are not processed. Each run handles up to 20 files. It runs every 15 minutes:

```
docker compose exec -T web python manage.py extract_document_content
```

`generate_photo_derivatives` makes the thumbnail and web-size version of new photos,
and reads their date. This normally happens right after upload. This job is a safety
net for photos uploaded while the worker was down. Each run handles up to 20 photos. It
runs every 15 minutes:

```
docker compose exec -T web python manage.py generate_photo_derivatives
```

`reindex_search` rebuilds the search index from scratch. The index is normally updated
each time something is saved. This job is a safety net. Run it by hand after you change
what is indexed. It runs every night at 03:00 UTC:

```
docker compose exec -T web python manage.py reindex_search
```

## Sauvegardes

`scripts/backup.sh` backs up the site. It:

1. dumps the Postgres database;
2. archives the `media/` and `documents/` folders;
3. encrypts a copy of `.env`;
4. copies everything to off-site storage with `rclone`.

The script runs on the server itself, not in a container. The deploy workflow copies it
to the server, but you must schedule it yourself with cron:

```
0 3 * * * cd /srv/bubu && bash scripts/backup.sh >> logs/backup.log 2>&1
```

Each run creates a folder named after the time (e.g. `backups/20260906T030000Z/`), with:

- `db.dump` — the database;
- `media.tar.gz` and `documents.tar.gz` — the files;
- `env.age` — the encrypted `.env`;
- `manifest.json` — the size and checksum of each file, the app and Postgres versions,
  and the result. The restore script reads this file. If you change its format, increase
  its `manifest_version` field.

**Configuration** (the `BACKUP_*` variables in `.env.example`):

| Var | Meaning |
|---|---|
| `BACKUP_DIR` | Where backups are written on the server. |
| `BACKUP_KEEP_DAILY` / `BACKUP_KEEP_WEEKLY` | How many backups to keep on the server: the last N, plus M older ones (about one per week). |
| `BACKUP_KEEP_MONTHLY` | How many monthly backups to keep off-site, in addition. |
| `BACKUP_REMOTE` | The `rclone` destination (e.g. `b2:famille-busson-backups/`). Empty = no off-site copy. |
| `BACKUP_AGE_RECIPIENT` | The [age](https://github.com/FiloSottile/age) public key used to encrypt `.env`. Empty = `.env` is not backed up. Without `.env`, you lose `SECRET_KEY` and the database password if the server is lost. |
| `BACKUP_PING_URL` | A monitoring URL (e.g. healthchecks.io), called at start, on success (`/0`) and on failure (`/fail`). Empty = no monitoring. |
| `BACKUP_MIN_DB_BYTES` / `BACKUP_MIN_MEDIA_BYTES` / `BACKUP_MIN_DOCUMENTS_BYTES` | Minimum size for each file. A smaller file stops the backup with an error, because it is probably incomplete. `0` = no check. Only the database check is on by default. |
| `BACKUP_MIN_DB_RATIO` / `BACKUP_MIN_MEDIA_RATIO` / `BACKUP_MIN_DOCUMENTS_RATIO` | Each file must be at least this fraction of the previous backup's file (default `0.5`). This catches a backup that gets slowly smaller. `0` = no check (default for documents). |

### Backup monitoring

- **A backup fails, or a file is too small:** the script calls `$BACKUP_PING_URL/fail`
  and stops with an error.
- **A backup does not run at all:** the script cannot detect this itself. The monitoring
  service does it: it sends an alert when it gets no success call in time. Set its
  schedule to daily, with a grace period of about one hour.

**Set up once on the server** (by hand, not automated):

- Install `age` and `rclone`.
- Create an age key pair with `age-keygen`. Put the public key in
  `BACKUP_AGE_RECIPIENT`. Keep the private key somewhere safe, **not** on the server.
  You will need it to restore `.env` (see [`restore.md`](restore.md)).
- Configure the `rclone` destination with `rclone config`.
- If you use monitoring, create the check and set `BACKUP_PING_URL`.
- Create the log folder: `mkdir -p /srv/bubu/logs`.

Then run `bash scripts/backup.sh --dry-run` to check the setup without writing
anything.

## One-time setup

**On a new installation only:** `bootstrap_site` creates the first administrator (with
a profile), the default groups, the starter document categories and the site settings,
in one step. You can run it again safely: it never overwrites a site that is already set
up. Run it interactively, or with `--noinput` and all the `--admin-*` and `--site-*`
options:

```
cd /srv/bubu && docker compose exec -T web python manage.py bootstrap_site
```

See [`site_config.md`](site_config.md) for the site settings.

Two other commands add map coordinates to addresses entered before the map existed. Run
them once. You can run them again safely: they skip addresses that already have
coordinates.

```
cd /srv/bubu && docker compose exec -T web python manage.py geocode_person_addresses
```

This one handles members' addresses.

```
cd /srv/bubu && docker compose exec -T web python manage.py geocode_place_addresses
```

This one handles houses' addresses.

## Deploying

Nothing to do by hand. A push to `main` starts `build-and-deploy.yml`. It builds the
image, copies `docker-compose.prod.yml` to the server, and then runs
`docker compose pull && docker compose up -d` over SSH.

It needs these repository secrets: `SSH_HOST`, `SSH_PORT`, `SSH_USER`,
`SSH_PRIVATE_KEY`, `SSH_KNOWN_HOSTS`. The server folder (`/srv/bubu`) and the image name
are set once at the top of the workflow (`DEPLOY_DIR`, `IMAGE_NAME`).
