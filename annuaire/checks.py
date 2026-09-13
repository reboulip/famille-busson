from pathlib import Path

from django.conf import settings
from django.core.checks import Warning, register

from .site_config import get_site_config


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


@register()
def sentry_dsn_check(app_configs, **kwargs):
    """Warn (never error) when SENTRY_DSN is unset outside DEBUG.

    Warning, not error: same rationale as W001/W002 -- checks run before
    `collectstatic` at container boot under `set -euo pipefail`. Without this, 9.9
    ships as a silent no-op until someone notices errors were never reaching Sentry.
    """
    if not settings.DEBUG and not settings.SENTRY_DSN:
        return [
            Warning(
                "SENTRY_DSN is unset outside of DEBUG -- errors are not being reported.",
                hint="Set SENTRY_DSN in the environment to enable error monitoring.",
                id="annuaire.W003",
            )
        ]
    return []


@register()
def compiled_locale_check(app_configs, **kwargs):
    """Warn (never error) when a configured language has a .po but no compiled .mo.

    Warning, not error: same rationale as W001-W003 -- checks run before
    `collectstatic` at container boot under `set -euo pipefail`. A missing .mo falls
    back to source-language (French) rendering, not a crash, so this can't be fatal --
    but it's worth surfacing since it means a language silently isn't working.
    """
    if settings.DEBUG:
        return []
    errors = []
    for code, name in settings.LANGUAGES:
        for locale_path in settings.LOCALE_PATHS:
            po_path = Path(locale_path) / code / "LC_MESSAGES" / "django.po"
            mo_path = po_path.with_suffix(".mo")
            if po_path.exists() and not mo_path.exists():
                errors.append(
                    Warning(
                        f"Locale '{code}' ({name}) has a .po file but no compiled .mo file.",
                        hint="Run `manage.py compilemessages` (done automatically at "
                        "image build time in the Dockerfile).",
                        id="annuaire.W004",
                    )
                )
    return errors


@register()
def site_name_check(app_configs, **kwargs):
    """Warn (never error) when SiteConfig.site_name is still blank outside DEBUG.

    Warning, not error: same rationale as W001-W004 -- checks run before
    `collectstatic` at container boot under `set -euo pipefail`. A blank site_name
    means `bootstrap_site` was never run on this instance.
    """
    if not settings.DEBUG and not get_site_config().site_name:
        return [
            Warning(
                "SiteConfig.site_name is blank outside of DEBUG -- bootstrap_site was never run on this instance.",
                hint="Run `manage.py bootstrap_site` to configure this instance.",
                id="annuaire.W005",
            )
        ]
    return []
