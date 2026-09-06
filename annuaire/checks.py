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
