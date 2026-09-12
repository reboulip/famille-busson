from django.conf import settings

from .privacy_notice import has_accepted


def site_version(request) -> dict[str, str]:
    return {"site_version": settings.APP_VERSION}


def privacy_notice_banner(request) -> dict[str, bool]:
    user = getattr(request, "user", None)
    show = bool(user and user.is_authenticated and not has_accepted(user))
    return {"show_privacy_notice_banner": show}
