# Deployment

famille-busson runs on a single VPS (`bubu.reboulip.fr`) as two Docker containers —
Postgres and the Django app behind Gunicorn — deployed automatically on every push to
`main`. This page ties together what's otherwise spread across `Dockerfile`,
`docker-entrypoint.sh`, `docker-compose.prod.yml`, `.env.example` and the two deploy
workflows.

## CI/CD pipeline

Four workflows run on `main` (all in `.github/workflows/`):

| Workflow | Trigger | Does |
|---|---|---|
| `tests.yml` | push to `develop`/`main`, PRs into `main` | Runs the pytest suite; the gate a `develop` → `main` PR must pass (see the `/release` skill). |
| `build-and-deploy.yml` | push to `main` | Builds the Docker image, pushes it to GHCR, then deploys it to the VPS over SSH. |
| `release.yml` | push to `main` | Tags `v<version>` (read from `pyproject.toml`) and creates the GitHub Release, if not already tagged (see `CLAUDE.md` §10). |
| `dependency-upgrade.yml` | weekly (Friday night, `cron`), or manual (`workflow_dispatch`) | Upgrades the pinned Python minor version, every uv-managed package, and the vendored front-end assets (see below), then opens a `deps/<date>` → `main` PR only if lint/ty/collectstatic-sanity/the full test suite all pass (see `CLAUDE.md` §8/§10/§11). |

### Automated dependency upgrades

`dependency-upgrade.yml` is the only workflow that opens a PR straight to `main` from a
branch other than `develop`/`hotfix/*` — a documented exception, on the same footing as
a hotfix (`CLAUDE.md` §8). It runs every gate a human contributor would (ruff, ty,
`collectstatic` sanity check, full pytest suite) *before* opening the PR — if anything
fails, the workflow run fails and no PR is opened, so a broken upstream release never
reaches `main` unreviewed. It always bumps the **minor** version, since there's no human
in the loop to judge release-worthiness (`CLAUDE.md` §10).

Vendored front-end libraries under `annuaire/static/vendor/` (leaflet, d3, family-chart,
pdfjs, leaflet.markercluster, html-to-image — not the Django admin's own bundled vendor
assets, which upgrade with Django itself) have no build tooling of their own; they're
tracked by `annuaire/static/vendor/manifest.json` (package name, pinned version, and
npm-package-path → local-file mapping per library) and fetched via jsdelivr by
`manage.py upgrade_vendored_assets` — see that command's docstring.

## Docker image

`Dockerfile` is Python 3.13 slim + `uv`. Dependencies are synced in a separate layer
before the app code is copied in, so `uv sync` only reruns when `pyproject.toml`/
`uv.lock` change. The image is built without dev dependencies (`--no-dev`). It does
**not** set `USER appuser` — the container starts as root so `docker-entrypoint.sh` can
fix ownership of the bind-mounted media volume before dropping privileges (see below).
The `tesseract-ocr`/`tesseract-ocr-fra` system packages are installed via `apt-get` in
their own early layer, ahead of the OCR content-extraction pipeline that will consume
them (see `ROADMAP.md`); `tests.yml`'s CI job installs the same packages so the test
suite runs against the same environment.

## `docker-entrypoint.sh` — the root → chown → appuser dance

The entrypoint runs twice per container start:
1. **As root** (first pass): `chown -R appuser:appuser` on both `/app/media` and
   `/app/documents_data`, then re-execs itself as `appuser` via `runuser`. This exists
   because both are host bind mounts whose ownership can't be relied on to already
   match `appuser`'s UID (1000) — pinning the host-side UID ahead of time isn't
   reliable across VPS redeploys.
2. **As `appuser`** (second pass, the `id -u` check no longer matches root): runs
   `manage.py migrate --noinput` and `collectstatic --noinput`, then `exec`s the
   container's `CMD` (`gunicorn famille_busson.wsgi:application`).

## Production stack (`docker-compose.prod.yml`)

| Service | Image | Notes |
|---|---|---|
| `db` | `postgres:16-alpine` | Data at `/srv/bubu/data/postgres` on the host; healthcheck gates `web`'s startup. |
| `cache` | `valkey/valkey:8-alpine` | Data at `/srv/bubu/data/valkey`; internal-only (no published port); healthcheck gates `web`'s startup. See "Shared cache" below. |
| `web` | `ghcr.io/reboulip/famille-busson:latest` | Media at `/srv/bubu/data/media`; protected document storage at `/srv/bubu/data/documents` (see below); reads `.env`; published on host port `8001` → container `8000`. |

On the VPS, `/srv/bubu/` holds `docker-compose.yml` (copied in by `build-and-deploy.yml`
from this repo's `docker-compose.prod.yml`), `.env` (see below), and the data volumes
above.

### Shared cache

`CACHES` was unset until this item, so every gunicorn worker held its own independent
`LocMemCache` — a value written by one worker was invisible to the others, which quietly
undermines anything relying on the cache being actually shared (rate-limiting, in
particular — see a later item). `famille_busson/settings.py` now reads `CACHES` via
`django-environ`'s `env.cache("CACHE_URL", default="locmemcache://")`, resolving a
`redis://`/`valkey://` URL to Django's built-in `django.core.cache.backends.redis.
RedisCache` (no `django-redis` package needed — only plain `redis`, the client library,
is a dependency). A warning-level system check (`annuaire.checks`, id `annuaire.W002`)
flags a `CACHES` that's still `LocMemCache` outside `DEBUG`, same rationale as `W001`:
checks run before `collectstatic` under `set -euo pipefail`, so it warns rather than
blocking container boot.

The `cache` container serves **two roles on separate logical DBs**: db 0 is the Django
cache (this item); db 1 is reserved for the background task queue's broker (a later
item) — one Valkey instance, not two containers. `--maxmemory-policy noeviction` is
required, not just a sane default: once the queue shares this instance, an eviction
policy would silently drop unprocessed jobs along with cache entries under memory
pressure. `--appendonly yes` persistence means in-flight state (soon: queued jobs)
survives a container restart. Dev and the test suite never need a real Valkey —
`CACHE_URL` defaults to `locmemcache://`, and `conftest.py` forces `LocMemCache` plus
clears it before every test regardless of a developer's local `.env`.

### Protected document storage

`/srv/bubu/data/documents` (mounted at `/app/documents_data`, `settings.DOCUMENTS_ROOT`)
is deliberately separate from the `media` volume: it holds `documents.DocumentFile`
uploads and their generated thumbnails, which are access-controlled per `documents.
Category` and must never be reachable through `MEDIA_URL`/`media_serve` or any other
public path (`documents/storage.py`'s `DocumentStorage.url()` raises rather than
producing one). The only way to reach a file's bytes is `documents.views.
DocumentFileView` (routes `document-file`/`document-file-thumbnail`, keyed by
`DocumentFile` pk, never by path), which re-checks the category's effective group
access on every request. Orphaned files (a deleted
`DocumentFile`, or one whose `file`/`thumbnail` is replaced) are cleaned up
automatically via `annuaire/file_cleanup.py`'s `register_file_cleanup`, wired in
`documents/signals.py`.

## Environment variables

`.env.example` at the repo root is the checklist — copy it to `/srv/bubu/.env` on the
VPS (never commit a real `.env`). Key point: `POSTGRES_*` feeds the `db` container
directly, while `DATABASE_URL` is what Django (`famille_busson/settings.py`, via
`django-environ`) actually reads — the two must be kept in sync by hand. Email defaults
to the console backend (no-op) until `EMAIL_BACKEND` is switched to SMTP. `SITE_BASE_URL`
is used to build absolute links in emails sent outside a request context — birthday
reminders and blog post notifications — and should still be set explicitly to
`https://bubu.reboulip.fr` in production. If left unset, `famille_busson/settings.py`'s
`_default_site_base_url()` now derives a non-localhost fallback from
`CSRF_TRUSTED_ORIGINS` (first entry) or, failing that, the first non-wildcard,
non-localhost `ALLOWED_HOSTS` entry — falling back to `http://localhost:8000` only if
neither yields anything. This is a safety net, not a substitute: a warning-level system
check (`annuaire.checks`, id `annuaire.W001`) flags a `SITE_BASE_URL` that still resolves
to localhost outside `DEBUG`.

## App version

`APP_VERSION` (`famille_busson/settings.py`) is read once at import time from
`pyproject.toml`'s `[project].version`, via `tomllib` directly — not
`importlib.metadata`, which has no dist-info to look up on this uv *virtual* project
(no `[build-system]` table, `--no-install-project` in the Dockerfile). It's exposed to
every template through the new `annuaire.context_processors.site_version` context
processor and shown as a discreet `v<version>` line in the footer, on both the
authenticated app shell and the anonymous/login threshold pages. Falls back to an empty
string (footer line omitted) rather than a 500 if `pyproject.toml` is missing or
malformed. This is also the seam Phase 15.1's planned `SiteConfig` context processor is
expected to build on.

## Scheduled tasks

Both recurring jobs now run on the background task queue (django-q2's `worker`
container) instead of crontab — see [`background_tasks.md`](background_tasks.md) for
the queue itself. This section covers the commands' hand-runnable form, still useful
for an ad-hoc run or a birthday-reminder backfill.

`send_birthday_reminders` (`annuaire/management/commands/send_birthday_reminders.py`)
emails subscribed members for each person whose birthday is today. The scheduled queue
run happens once a day; the command exits non-zero (and logs at ERROR level) if any
reminder fails to send. Use `--date YYYY-MM-DD` to run it for a specific day (e.g. to
verify things work without waiting for a real birthday) and `--dry-run` to see who would
receive a reminder without sending anything:

```
docker compose exec -T web python manage.py send_birthday_reminders --date 2026-06-10 --dry-run
```

`extract_document_content` (`documents/management/commands/extract_document_content.py`)
backfills `DocumentFile.extracted_text`/`thumbnail` for pending uploads — PDF text via
PyMuPDF with Tesseract OCR fallback for image-only pages/scans, direct OCR for raster
image uploads, and a first-page thumbnail for PDFs (office docs and plain text files are
marked "unsupported" and never processed). Capped at 20 files and 20 OCR'd pages per file
per run, to avoid a pathological upload OOMing gunicorn. The scheduled queue run happens
every 15 minutes; run it by hand the same way:

```
docker compose exec -T web python manage.py extract_document_content
```

**Migration step, once, when this deploy first ships**: remove the two old crontab
entries that used to run these commands (`send_birthday_reminders` daily,
`extract_document_content` every 15 minutes) from the VPS's crontab. Leaving them active
alongside the new queue would run both jobs twice — the birthday reminder task has its
own same-day lock guarding against that specific case, but the extraction job does not,
and there's no reason to run either path twice regardless.

## Sauvegardes

`scripts/backup.sh` dumps Postgres, archives `media/` and `documents/`, encrypts a
copy of `.env`, and copies the result off-VPS via `rclone`. It's a plain host-side bash
script (not run inside a container, unlike the scheduled tasks above) — it shells out to
`docker compose exec` itself for the parts that need the running containers. It ships
with the repo and is copied to the VPS by `build-and-deploy.yml` alongside
`docker-compose.prod.yml`, so a fix to it reaches production the same way any other code
change does; it still has to be scheduled by hand, same as the jobs above:

```
0 3 * * * cd /srv/bubu && bash scripts/backup.sh >> logs/backup.log 2>&1
```

Each run writes to `$BACKUP_DIR/<UTC-timestamp>/` (e.g. `backups/20260906T030000Z/`):
`db.dump` (`pg_dump -Fc`), `media.tar.gz`, `documents.tar.gz`, an age-encrypted `env.age`,
and a `manifest.json` recording per-artifact size and sha256, the app and Postgres
versions, start/end time, and exit status. `manifest.json`'s shape is a contract other
tooling reads (the restore script, backup monitoring) — treat a change to it as a breaking
change and bump its `manifest_version` field.

**Configuration** (`.env.example`'s `BACKUP_*` block):

| Var | Meaning |
|---|---|
| `BACKUP_DIR` | Where run directories are written on the VPS. |
| `BACKUP_KEEP_DAILY` / `BACKUP_KEEP_WEEKLY` | Local retention: the most recent N runs, plus M older ones kept roughly weekly. |
| `BACKUP_KEEP_MONTHLY` | Extra off-site-only retention, beyond daily+weekly — off-site storage is cheap, VPS disk is not. |
| `BACKUP_REMOTE` | An `rclone` remote path (e.g. `b2:famille-busson-backups/`) to copy each run to. Empty disables off-site copy entirely. |
| `BACKUP_AGE_RECIPIENT` | The [age](https://github.com/FiloSottile/age) public key/recipient `.env` is encrypted to. Empty skips encrypting `.env` (it's still excluded from the backup, which then loses `SECRET_KEY`/the DB password if the VPS is lost — set this up before relying on the backup for disaster recovery). |
| `BACKUP_PING_URL` | A dead-man's-switch base URL (e.g. a healthchecks.io check) — pinged at start, on success (`/0`), and on failure (`/fail`). Empty disables monitoring pings. |
| `BACKUP_MIN_DB_BYTES` / `BACKUP_MIN_MEDIA_BYTES` / `BACKUP_MIN_DOCUMENTS_BYTES` | Absolute sanity floors: a dump/archive smaller than this aborts the run rather than shipping a silently truncated backup. All disabled (`0`) except the DB floor by default. |
| `BACKUP_MIN_DB_RATIO` / `BACKUP_MIN_MEDIA_RATIO` / `BACKUP_MIN_DOCUMENTS_RATIO` | Relative sanity floors: this run's artifact must be at least this fraction of the *previous* run's size for the same artifact, or the run aborts. Catches a slow-creeping truncation that stays individually above the absolute floor every night. `0` disables the check (the default for documents, since that archive can legitimately shrink a lot in one run). Deliberately loose defaults (`0.5`) — a family site's day-to-day size swings shouldn't page anyone. |

### Backup monitoring

- **A run that fails, or produces an artifact under one of the floors above**: `scripts/backup.sh`'s `fail()` pings `$BACKUP_PING_URL/fail` and exits non-zero. Both absolute and relative floors route through the same `fail()` path.
- **A run that doesn't happen at all**: this is what the dead-man's-switch itself is for, not something this script can detect from inside its own run — a healthchecks.io-style check has its own schedule and grace period configured on its dashboard, and it alerts on its own once a `/0` ping doesn't arrive in time. Set the check's schedule to match the cron frequency (daily) and its grace period to something comfortably longer than a normal run (an hour is generous). No Django/Python code is needed for this case; don't build one.

**Manual VPS setup this needs, once**, none of it automated by CI/CD:
- Install `age` and `rclone` on the VPS.
- Generate an age keypair (`age-keygen`); put the public key in `BACKUP_AGE_RECIPIENT`,
  keep the private key safe and *off* the VPS's own backup (a backup that can decrypt
  itself defeats the point) — the operator uses this same private key by hand later, per
  [`restore.md`](restore.md), to decrypt `env.age` if a restore ever needs it.
- Configure an `rclone` remote matching `BACKUP_REMOTE` (`rclone config`).
- If using a dead-man's-switch monitor: create the check, set its schedule and grace
  period as above, and set `BACKUP_PING_URL`.
- `mkdir -p /srv/bubu/logs` if it doesn't already exist, for the cron entry's log
  redirect.

Run `bash scripts/backup.sh --dry-run` after setup to verify configuration without
writing anything.

## One-time setup

Some features ship with a manual backfill step that only needs to run once on the VPS,
after the deploy that introduces them — unlike the recurring jobs above. Run it by hand,
the same way as a scheduled command (`docker compose exec` from `/srv/bubu`), but just
once:

```
cd /srv/bubu && docker compose exec -T web python manage.py geocode_person_addresses
```

Geocodes every existing `Person.postal_address` that doesn't yet have coordinates (via
`annuaire/geocoding.py`'s `geocode()` — BAN first, falling back to Photon for addresses
BAN can't resolve, e.g. outside France), so members who already had an address on file
before the "Carte" view (`/annuaire/carte/`) shipped show up on it right away, instead of
only after their next profile edit. Safe to re-run — skips anyone who already has
coordinates.

```
cd /srv/bubu && docker compose exec -T web python manage.py geocode_chalet_addresses
```

Same idea, for `Chalet.address`/`Chalet.latitude`/`Chalet.longitude`: geocodes every
existing chalet address that doesn't yet have coordinates (same BAN-then-Photon
`geocode()` fallback as above), so chalets that already had
an address on file before the coordinate fields shipped are backfilled immediately
instead of only after their next edit. Safe to re-run — skips any chalet that already
has coordinates.

## Deploying

Nothing manual: pushing to `main` triggers `build-and-deploy.yml`, which builds/pushes
the image, copies `docker-compose.prod.yml` to the VPS, then over SSH runs
`docker compose pull && docker compose up -d && docker image prune -f`. Required repo
secrets: `SSH_HOST`, `SSH_PORT`, `SSH_USER`, `SSH_PRIVATE_KEY`, `SSH_KNOWN_HOSTS`.
