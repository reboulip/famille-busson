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
| `web` | `ghcr.io/reboulip/famille-busson:latest` | Media at `/srv/bubu/data/media`; protected document storage at `/srv/bubu/data/documents` (see below); reads `.env`; published on host port `8001` → container `8000`. |

On the VPS, `/srv/bubu/` holds `docker-compose.yml` (copied in by `build-and-deploy.yml`
from this repo's `docker-compose.prod.yml`), `.env` (see below), and the three data
volumes above.

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

There is no in-app scheduler. `send_birthday_reminders` (`annuaire/management/commands/
send_birthday_reminders.py`) emails subscribed members for each person whose birthday is
today, but only when it's actually run — it must be scheduled on the VPS via cron or a
systemd timer, set up by hand outside this repo's CI/CD. A daily cron entry running it
inside the `web` container from `/srv/bubu` (where `docker-compose.yml` lives, see
above):

```
0 8 * * * cd /srv/bubu && docker compose exec -T web python manage.py send_birthday_reminders
```

`extract_document_content` (`documents/management/commands/extract_document_content.py`)
backfills `DocumentFile.extracted_text`/`thumbnail` for pending uploads — PDF text via
PyMuPDF with Tesseract OCR fallback for image-only pages/scans, direct OCR for raster
image uploads, and a first-page thumbnail for PDFs (office docs and plain text files are
marked "unsupported" and never processed). Capped at 20 files and 20 OCR'd pages per file
per run, to avoid a pathological upload OOMing gunicorn. A cron entry every 15 minutes,
same pattern as above:

```
*/15 * * * * cd /srv/bubu && docker compose exec -T web python manage.py extract_document_content
```

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
