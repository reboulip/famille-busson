#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" = '0' ]; then
    # The container starts as root so it can fix ownership of the bind-mounted
    # media volume regardless of what UID owns it on the host -- pinning appuser's
    # UID to match the host's deploy user isn't reliable across VPS/redeploys.
    # Re-exec as appuser for the rest of this script (migrate/collectstatic/gunicorn
    # all run unprivileged); the id-check above is what makes that second pass skip
    # this block instead of looping.
    mkdir -p /app/media
    chown -R appuser:appuser /app/media
    mkdir -p /app/documents_data
    chown -R appuser:appuser /app/documents_data
    exec runuser -u appuser -- /app/docker-entrypoint.sh "$@"
fi

# Guards migrate/collectstatic/schedule-sync so only the web service runs them --
# the worker service (RUN_STARTUP_TASKS=0) shares this same entrypoint but must not
# race web to apply migrations or (re)create the same django-q2 Schedule rows.
if [ "${RUN_STARTUP_TASKS:-1}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    python manage.py sync_scheduled_tasks
fi

exec "$@"
