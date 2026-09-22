# Installation

Start here if you're standing up a fresh instance of this project — for a
different family, or a differently-branded copy — from a clean checkout. If
you're looking for how *this* instance's CI/CD and running stack work, see
[`deployment.md`](deployment.md) instead; this page is the "day zero" recipe.

**Status:** item 16.7's drill has run once — see the [run log](#run-log) at
the bottom. It exercised every step that doesn't require Docker (this
environment has none available — no `docker`, no standalone Postgres/Valkey);
the Docker Compose stand-up itself (`docker compose up -d`, the three
containers' healthchecks) is reviewed but **not** executed by that run. Treat
the Docker-dependent half of the recipe as documented but unverified, the
same posture `restore.md` takes for its own drill, until someone runs it on a
real Docker host.

## Prerequisites

- A host with Docker and Docker Compose v2 (`docker compose`, not the
  standalone `docker-compose`).
- A domain name you control, if you want the site reachable over a real
  hostname rather than an IP/port.
- [`age`](https://github.com/FiloSottile/age) and
  [`rclone`](https://rclone.org/) if you intend to use the automated backup
  job (see [`deployment.md`'s "Sauvegardes" section](deployment.md#sauvegardes))
  — not required just to run the site.

## DNS

Point the domain's A (and AAAA, if the host has IPv6) record at the host's
public IP address. Propagation can take anywhere from a few minutes to a few
hours depending on the previous record's TTL.

## Reverse proxy and TLS

**Out of scope for this repository.** `docker-compose.prod.yml` publishes the
app on `${WEB_PORT:-8001}` over plain HTTP only — terminating TLS and
forwarding to that port is left to a reverse proxy of your choice (nginx,
Traefik, Caddy), run outside this compose file. No such proxy config is
shipped here.

The simplest option for a single-domain deploy is
[Caddy](https://caddyserver.com/), which handles Let's Encrypt automatically
from a one-line config:

```
your-domain.tld {
    reverse_proxy localhost:8001
}
```

## Clone and configure

```bash
git clone <this repository's URL>
cd famille-busson
cp .env.example .env
```

Edit `.env` and fill in at least:

- `SECRET_KEY` — generate a real random value; never reuse the placeholder.
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_BASE_URL` — your domain.
- `POSTGRES_PASSWORD` and `DATABASE_URL` (the latter must embed the former).
- `DATA_ROOT`, `APP_IMAGE`, `WEB_PORT` — the new deployment-level block near
  the top of `.env.example`. The defaults match this project's own VPS; only
  change them if you want the data directory elsewhere, a different image,
  or a different published port.
- `DEFAULT_FROM_EMAIL` — no longer defaults to anything family-specific; set
  it explicitly (see [Email provider](#email-provider) below).
- The five `PRIVACY_*` variables — see privacy.md's
  ["Legal facts: environment variables, not hardcoded"](privacy.md#legal-facts-environment-variables-not-hardcoded)
  section. Required before a real deploy; safe to leave blank for a local trial.

See [`deployment.md`'s "Environment variables" section](deployment.md#environment-variables)
for the full reference of every variable Django itself reads.

## Email provider

By default `EMAIL_BACKEND` is the console backend (mail is logged, never
sent). To actually send mail, set `EMAIL_BACKEND` to
`django.core.mail.backends.smtp.EmailBackend` and fill in
`EMAIL_HOST`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`/`EMAIL_PORT` for
whichever provider you use, plus `DEFAULT_FROM_EMAIL`.

## First boot

```bash
mkdir -p "${DATA_ROOT:-/srv/bubu/data}"/{postgres,valkey,media,documents}
docker compose up -d
docker compose exec -T web python manage.py bootstrap_site
```

`bootstrap_site` is interactive by default — it prompts for the site's name
and the first administrator's details, then creates the superuser, default
groups, starter document categories, and the `SiteConfig` row in one step
(see [`deployment.md`'s "One-time setup" section](deployment.md#one-time-setup)
and [`site_config.md`](site_config.md)). It's idempotent — safe to re-run,
and a re-run never overwrites an already-configured site.

## Backup job

Set up the one-time `age`/`rclone` configuration and the cron entry described
in [`deployment.md`'s "Sauvegardes" section](deployment.md#sauvegardes) — not
duplicated here.

## Scheduler

Nothing to configure. The `worker` container (running `manage.py qcluster`,
django-q2's consumer) starts automatically as part of `docker compose up -d`
alongside `web`, `db` and `cache` — there's no separate crontab to install,
unlike a stack migrating from a plain cron-based setup might expect. See
[`background_tasks.md`](background_tasks.md) for what it runs and when.

## Verification checklist

- `docker compose ps` shows `db`, `cache`, `web` and `worker` all healthy.
- `curl -sf https://<your-domain>/healthz` returns `{"status": "ok", ...}`
  with `database`/`media_storage`/`documents_storage` green (`cache`/`queue`
  may show `degraded` only if Valkey isn't reachable yet — see
  [`deployment.md`'s `/healthz` section](deployment.md#healthz)).
- `bootstrap_site` reported a created superuser, and logging in with those
  credentials works.
- `DEBUG=False SECRET_KEY=x docker compose exec -T web python manage.py collectstatic --noinput`
  completes without a `MissingFileError` — this is the single most common
  first-boot failure on a fresh instance and is not caught by any automated
  check today (see `CLAUDE.md`'s toolchain notes).

## Run log

| Date | Operator | Result | Notes |
|------|----------|--------|-------|
| 2026-09-13 | dev-pipeline sprint (item 16.7) | Partial — Docker-free steps only | Ran in a sandboxed container with no `docker`/`docker compose`/standalone Postgres or Valkey available. Verified: fresh checkout → `uv sync` → `manage.py migrate` against a clean throwaway SQLite database (all migrations applied cleanly, including publications' `post_type`→`Tag` data migration) → `manage.py bootstrap_site --noinput` with a **differently-branded identity** ("Famille Dupont", not "Famille Busson") → created superuser, default groups, starter categories and `SiteConfig` correctly → `manage.py runserver` → confirmed the login page renders "Famille Dupont" with zero "Busson" residue → `/healthz` returned `database`/`cache`/`media_storage`/`documents_storage` all `ok` (`queue` `degraded`, expected: no real broker in this sandbox) → `DEBUG=False` system checks correctly fired W002 (LocMemCache)/W003 (no Sentry DSN)/W006 (no DEFAULT_FROM_EMAIL) and correctly did **not** fire W005 (site_name), confirming `bootstrap_site` set it → `DEBUG=False SECRET_KEY=x manage.py collectstatic --noinput` completed with no `MissingFileError` → the no-residual-branding guard test (`annuaire/tests/test_no_residual_branding.py`) passed. **Not executed:** the actual `docker compose up -d` stand-up and the three containers' healthchecks, DNS, TLS/reverse-proxy setup, and the backup/restore job — these remain reviewed-but-unverified pending a run on a real Docker host. |
