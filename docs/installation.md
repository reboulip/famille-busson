# Installation

Start here if you want to set up a new installation of this project, for example for
another family. This page covers "day zero". To learn how the current installation is
deployed and run, see [`deployment.md`](deployment.md).

**Status:** this recipe was tested once (see the [run log](#run-log) below), but without
Docker. The steps that need Docker (`docker compose up -d` and the container health
checks) have been reviewed but not run. Treat them as unverified until someone runs
them on a real Docker host.

## Prerequisites

- A server with Docker and Docker Compose v2 (the `docker compose` command, not the old
  `docker-compose`).
- A domain name, if you want to reach the site by name and not by IP address.
- [`age`](https://github.com/FiloSottile/age) and [`rclone`](https://rclone.org/), if
  you want automatic backups (see [Sauvegardes](deployment.md#sauvegardes)). The site
  runs without them.

## DNS

Point the domain's A record (and AAAA record, if the server has IPv6) to the server's
public IP address. The change can take from a few minutes to a few hours to spread.

## Reverse proxy and TLS

**This repository does not handle HTTPS.** The app listens on port `8001` (or
`WEB_PORT`) in plain HTTP. You need a reverse proxy in front of it (nginx, Traefik or
Caddy) to handle HTTPS.

The simplest choice is [Caddy](https://caddyserver.com/). It gets a Let's Encrypt
certificate by itself, with this config:

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

Edit `.env`. Fill in at least:

- `SECRET_KEY` — a long random value. Never keep the example value.
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_BASE_URL` — your domain.
- `POSTGRES_PASSWORD` and `DATABASE_URL`. `DATABASE_URL` must contain the same password.
- `DATA_ROOT`, `APP_IMAGE`, `WEB_PORT` — where data is stored on the server, which
  Docker image to run, and which port to use. The defaults are fine in most cases.
- `DEFAULT_FROM_EMAIL` — the sender address for emails (see
  [Email provider](#email-provider) below).
- The five `PRIVACY_*` variables — legal facts shown on the privacy page (see
  [privacy.md](privacy.md#legal-facts-environment-variables-not-hardcoded)). You must
  set them before going live. You can leave them empty for a test.

The full list of variables is in
[`deployment.md`](deployment.md#environment-variables).

## Email provider

By default, emails are only written to the log. They are not sent. To send real
emails, set `EMAIL_BACKEND` to `django.core.mail.backends.smtp.EmailBackend`. Then fill
in `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_PORT` and
`DEFAULT_FROM_EMAIL` with your provider's values.

## First boot

```bash
mkdir -p "${DATA_ROOT:-/srv/bubu/data}"/{postgres,valkey,media,documents}
docker compose up -d
docker compose exec -T web python manage.py bootstrap_site
```

`bootstrap_site` asks for the site name and for the first administrator's details.
Then it creates, in one step:

- the administrator account;
- the default groups;
- a few starter document categories;
- the site settings (see [`site_config.md`](site_config.md)).

You can run it again safely. It never overwrites a site that is already set up.

## Backup job

Follow the one-time setup in [Sauvegardes](deployment.md#sauvegardes).

## Scheduler

Nothing to set up. The `worker` container runs the scheduled jobs. It starts with the
others when you run `docker compose up -d`. You do not need a crontab. See
[`background_tasks.md`](background_tasks.md) for the list of jobs.

## Verification checklist

- `docker compose ps` shows `db`, `cache`, `web` and `worker` as healthy.
- `curl -sf https://<your-domain>/healthz` returns `{"status": "ok", ...}`. The
  `database`, `media_storage` and `documents_storage` checks must be `ok`. `cache` and
  `queue` may show `degraded` if Valkey is not ready yet (see [`/healthz`](deployment.md#healthz)).
- You can log in with the administrator account created by `bootstrap_site`.
- This command finishes without a `MissingFileError`:
  `DEBUG=False SECRET_KEY=x docker compose exec -T web python manage.py collectstatic --noinput`.
  This is the most common failure on a new installation, and no automatic check catches
  it.

## Run log

| Date | Operator | Result | Notes |
|------|----------|--------|-------|
| 2026-09-13 | dev-pipeline sprint (item 16.7) | Partial — steps without Docker only | Run in a container with no Docker, Postgres or Valkey. **Worked:** fresh checkout, `uv sync`, `migrate` on an empty SQLite database, and `bootstrap_site --noinput` with another family name ("Famille Dupont"). The login page showed "Famille Dupont", with no trace of "Busson". `/healthz` was `ok`, except `queue` (`degraded`, as expected with no broker). The expected warnings appeared with `DEBUG=False`. `collectstatic` passed. The branding test (`test_no_residual_branding.py`) passed. **Not run:** `docker compose up -d` and the container health checks, DNS, HTTPS and the reverse proxy, backup and restore. |
