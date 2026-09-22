"""Read access to the SiteConfig singleton (Phase 15), kept in its own module
so email_utils.py, context_processors.py and middleware.py can import it
without pulling in the whole models module graph."""

from django.core.cache import cache

from .models import SiteConfig

CACHE_KEY = "site_config"
CACHE_TTL = 300


def get_site_config() -> SiteConfig:
    """Never creates a row -- returns an unsaved, defaults-only instance when
    none exists yet, so a plain GET can't fire a write (post_save signals,
    cache churn) or trip the 14.4 audit log. Only SiteConfigUpdateView (and
    later 16.5's bootstrap_site) actually persists a SiteConfig."""
    config = cache.get(CACHE_KEY)
    if config is None:
        config = SiteConfig.objects.first() or SiteConfig()
        cache.set(CACHE_KEY, config, CACHE_TTL)
    return config
