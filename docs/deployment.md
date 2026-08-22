# Deployment

famille-busson runs on a single VPS (`bubu.reboulip.fr`) as two Docker containers —
Postgres and the Django app behind Gunicorn — deployed automatically on every push to
`main`. This page ties together what's otherwise spread across `Dockerfile`,
`docker-entrypoint.sh`, `docker-compose.prod.yml`, `.env.example` and the two deploy
workflows.

## CI/CD pipeline

Three workflows run on `main` (all in `.github/workflows/`):

| Workflow | Trigger | Does |
|---|---|---|
| `tests.yml` | push to `develop`/`main`, PRs into `main` | Runs the pytest suite; the gate a `develop` → `main` PR must pass (see the `/release` skill). |
| `build-and-deploy.yml` | push to `main` | Builds the Docker image, pushes it to GHCR, then deploys it to the VPS over SSH. |
| `release.yml` | push to `main` | Tags `v<version>` (read from `pyproject.toml`) and creates the GitHub Release, if not already tagged (see `CLAUDE.md` §10). |

## Docker image

`Dockerfile` is Python 3.13 slim + `uv`. Dependencies are synced in a separate layer
before the app code is copied in, so `uv sync` only reruns when `pyproject.toml`/
`uv.lock` change. The image is built without dev dependencies (`--no-dev`). It does
**not** set `USER appuser` — the container starts as root so `docker-entrypoint.sh` can
fix ownership of the bind-mounted media volume before dropping privileges (see below).

## `docker-entrypoint.sh` — the root → chown → appuser dance

The entrypoint runs twice per container start:
1. **As root** (first pass): `chown -R appuser:appuser /app/media`, then re-execs
   itself as `appuser` via `runuser`. This exists because the media volume is a
   host bind mount whose ownership can't be relied on to already match `appuser`'s
   UID (1000) — pinning the host-side UID ahead of time isn't reliable across VPS
   redeploys.
2. **As `appuser`** (second pass, the `id -u` check no longer matches root): runs
   `manage.py migrate --noinput` and `collectstatic --noinput`, then `exec`s the
   container's `CMD` (`gunicorn famille_busson.wsgi:application`).

## Production stack (`docker-compose.prod.yml`)

| Service | Image | Notes |
|---|---|---|
| `db` | `postgres:16-alpine` | Data at `/srv/bubu/data/postgres` on the host; healthcheck gates `web`'s startup. |
| `web` | `ghcr.io/reboulip/famille-busson:latest` | Media at `/srv/bubu/data/media`; reads `.env`; published on host port `8001` → container `8000`. |

On the VPS, `/srv/bubu/` holds `docker-compose.yml` (copied in by `build-and-deploy.yml`
from this repo's `docker-compose.prod.yml`), `.env` (see below), and the two data
volumes above.

## Environment variables

`.env.example` at the repo root is the checklist — copy it to `/srv/bubu/.env` on the
VPS (never commit a real `.env`). Key point: `POSTGRES_*` feeds the `db` container
directly, while `DATABASE_URL` is what Django (`famille_busson/settings.py`, via
`django-environ`) actually reads — the two must be kept in sync by hand. Email defaults
to the console backend (no-op) until `EMAIL_BACKEND` is switched to SMTP. `SITE_BASE_URL`
(default `http://localhost:8000`) is used to build absolute links in emails sent outside
a request context — birthday reminders and blog post notifications — and should be set
to `https://bubu.reboulip.fr` in production.

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
