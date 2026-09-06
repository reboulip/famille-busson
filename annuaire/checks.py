from django.conf import settings
from django.core.checks import Warning, register


@register()
def site_base_url_check(app_configs, **kwargs):
    """Warn (never error) when SITE_BASE_URL still resolves to localhost outside DEBUG.

    Warning, not error: this runs before `collectstatic` at container boot
    (docker-entrypoint.sh, `set -euo pipefail`) -- an error-level check would take the
    whole site down over a wrong link in an email rather than just sending it wrong.
    """
    if not settings.DEBUG and "localhost" in settings.SITE_BASE_URL:
        return [
            Warning(
                "SITE_BASE_URL resolves to localhost outside of DEBUG.",
                hint="Set SITE_BASE_URL in the environment to the real production domain.",
                id="annuaire.W001",
            )
        ]
    return []


@register()
def cache_backend_check(app_configs, **kwargs):
    """Warn (never error) when CACHES still resolves to LocMemCache outside DEBUG.

    Warning, not error: same rationale as W001 -- this runs before `collectstatic` at
    container boot under `set -euo pipefail`. A typo'd CACHE_URL silently falling back
    to per-worker LocMemCache is exactly the bug this item exists to prevent, so it's
    worth surfacing even though it can't safely be fatal.
    """
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    if not settings.DEBUG and backend == "django.core.cache.backends.locmem.LocMemCache":
        return [
            Warning(
                "CACHES resolves to LocMemCache outside of DEBUG -- each gunicorn worker "
                "will hold its own independent cache.",
                hint="Set CACHE_URL in the environment to a shared Valkey/Redis instance.",
                id="annuaire.W002",
            )
        ]
    return []
