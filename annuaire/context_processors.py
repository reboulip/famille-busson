from django.conf import settings

from .models import SiteConfig
from .privacy_notice import has_accepted
from .site_config import get_site_config
from .theming import brand_css_overrides


def site_version(request) -> dict[str, str]:
    return {"site_version": settings.APP_VERSION}


def site_config(request) -> dict[str, SiteConfig]:
    return {"site_config": get_site_config()}


def brand_css(request) -> dict[str, str]:
    return {"brand_css_overrides": brand_css_overrides(get_site_config())}


def privacy_notice_banner(request) -> dict[str, bool]:
    user = getattr(request, "user", None)
    show = bool(user and user.is_authenticated and not has_accepted(user))
    return {"show_privacy_notice_banner": show}


def trash_retention(request) -> dict[str, int]:
    return {"trash_retention_days": settings.TRASH_RETENTION_DAYS}
