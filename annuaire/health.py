"""Deepened /healthz (9.10) -- checks the database, cache, queue and storage
writability, not just "the process is up."

Lives here rather than in famille_busson/urls.py because famille_busson/ is outside
[tool.coverage.run].source (pyproject.toml), so health code there would be invisible
to the 80% coverage gate -- annuaire is already where project-wide non-model code
lives (checks.py, middleware.py, throttling.py, email_utils.py).
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger("django")

# database/media_storage/documents_storage are critical: any failure means the
# overall response is 503. cache/queue are not: a dead Valkey shouldn't take the
# whole site down, and this is what keeps a local dev `curl -sf .../healthz` (no
# Valkey running locally) reporting healthy.
CRITICAL_CHECKS = frozenset({"database", "media_storage", "documents_storage"})

# Namespaced away from every other cache key this sprint added:
# annuaire/tasks.py's "birthday-reminders:<date>", annuaire/throttling.py's
# "throttle:<scope>:...".
_CACHE_PROBE_KEY = "healthz:probe"


def _check_database() -> str | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return None


def _check_cache() -> str | None:
    token = uuid.uuid4().hex
    cache.set(_CACHE_PROBE_KEY, token, timeout=10)
    if cache.get(_CACHE_PROBE_KEY) != token:
        return "cache-roundtrip-mismatch"
    return None


def _check_queue() -> str | None:
    from django_q.brokers import get_broker

    if not get_broker().ping():
        return "broker-ping-failed"
    return None


def _check_storage_writable(root: str) -> str | None:
    # Read the setting at call time, not a module-level constant -- storage.py
    # documents why: caching it would freeze a value that override_settings (tests)
    # or a runtime config change can no longer affect.
    probe_dir = Path(root)
    probe_path = probe_dir / f".healthz-{uuid.uuid4().hex}"
    probe_path.write_bytes(b"healthz")
    probe_path.unlink()
    return None


def _check_media_storage() -> str | None:
    return _check_storage_writable(settings.MEDIA_ROOT)


def _check_documents_storage() -> str | None:
    return _check_storage_writable(settings.DOCUMENTS_ROOT)


CHECKS = {
    "database": _check_database,
    "cache": _check_cache,
    "queue": _check_queue,
    "media_storage": _check_media_storage,
    "documents_storage": _check_documents_storage,
}


@login_not_required
def healthz(request):
    checks = {}
    overall_ok = True
    overall_degraded = False

    for name, probe in CHECKS.items():
        start = time.monotonic()
        try:
            error_code = probe()
        except Exception:
            # Never the raw exception text in the response body -- a psycopg error
            # string can leak the DSN host/user. Full detail goes to the log only.
            duration_ms = round((time.monotonic() - start) * 1000, 3)
            logger.warning("healthz: %s check failed", name, exc_info=True)
            checks[name] = {"status": "error", "duration_ms": duration_ms}
            if name in CRITICAL_CHECKS:
                overall_ok = False
            else:
                overall_degraded = True
            continue

        duration_ms = round((time.monotonic() - start) * 1000, 3)
        if error_code:
            logger.warning("healthz: %s check failed (%s)", name, error_code)
            checks[name] = {"status": "error", "duration_ms": duration_ms}
            if name in CRITICAL_CHECKS:
                overall_ok = False
            else:
                overall_degraded = True
        else:
            checks[name] = {"status": "ok", "duration_ms": duration_ms}

    status = "ok" if overall_ok and not overall_degraded else ("error" if not overall_ok else "degraded")

    response = JsonResponse(
        {"status": status, "checks": checks, "version": settings.APP_VERSION},
        status=200 if overall_ok else 503,
    )
    response["Cache-Control"] = "no-store"
    return response
