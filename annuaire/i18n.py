"""Language resolution for UserLanguageMiddleware (Phase 15.5).

Precedence, most specific first: the logged-in user's own saved preference,
then the `django_language` cookie (set by SetLanguageView, works for anonymous
visitors too), then the site's configured default, then the browser's
Accept-Language header, then settings.LANGUAGE_CODE.

Kept separate from settings.py's LocaleMiddleware: that middleware runs first
and sets an initial language using Django's own algorithm, but has no idea
about Account.language or SiteConfig.default_language. UserLanguageMiddleware
(placed after it, see settings.py's MIDDLEWARE) calls resolve_language() and
activates the result, overriding LocaleMiddleware's guess with this project's
own precedence.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import get_language_from_request, get_supported_language_variant


def _valid_language_code(code: str | None) -> str | None:
    if not code:
        return None
    try:
        return get_supported_language_variant(code)
    except LookupError:
        return None


def resolve_language(request: HttpRequest) -> str:
    if request.user.is_authenticated:
        account_language = _valid_language_code(getattr(request.user, "language", ""))
        if account_language:
            return account_language

    cookie_language = _valid_language_code(request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME))
    if cookie_language:
        return cookie_language

    # Imported lazily, same rationale as SiteTimezoneMiddleware's import of
    # get_site_config(): this module is loaded before the app registry is
    # ready during django.setup().
    from .site_config import get_site_config

    site_default = _valid_language_code(str(get_site_config().default_language))
    if site_default:
        return site_default

    # Falls all the way back through Accept-Language to settings.LANGUAGE_CODE
    # itself, so this is never None.
    return get_language_from_request(request, check_path=False)
