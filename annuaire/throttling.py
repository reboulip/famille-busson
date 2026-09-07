"""Fixed-window rate limiting for unauthenticated email-sending views (9.8).

Uses the shared cache (`django.core.cache`) so the limit holds across every gunicorn
worker -- see docs/deployment.md's "Shared cache" section. `cache.add()` + `cache.incr()`
is properly atomic on the production RedisCache backend; on LocMemCache (dev/tests) it
isn't perfectly atomic under concurrency, but the test suite never exercises concurrent
requests, so this is a documented, accepted gap rather than a bug.

Never keyed by IP: the reverse proxy in front of this app's own port is outside this
repo, and trusting a client-supplied X-Forwarded-For without confirming the proxy's
behavior would make the throttle both bypassable (spoof the header) and weaponizable
(lock out a real IP by spoofing it). Keyed on the submitted email plus a global
per-endpoint counter instead.
"""

from __future__ import annotations

from django.contrib.auth.base_user import BaseUserManager
from django.core.cache import cache

PER_EMAIL_HOURLY_LIMIT = 3
PER_EMAIL_DAILY_LIMIT = 10
GLOBAL_HOURLY_LIMIT = 60

HOUR = 60 * 60
DAY = 60 * 60 * 24

THROTTLE_MESSAGE = "Trop de tentatives. Merci de réessayer plus tard."


def _hit(key: str, window_seconds: int) -> int:
    """Increment a fixed-window counter, creating it with the given TTL if absent.

    The attempt is counted even when it turns out to be over the limit -- an
    attacker retrying past the limit must not get free, uncounted retries.
    """
    cache.add(key, 0, window_seconds)
    return cache.incr(key)


class EmailRateLimitMixin:
    """Mix into a FormView whose form has an `email` field and sends mail on success.

    Subclasses set `throttle_scope` to a short, stable, URL-safe name unique to that
    view (e.g. "signup", "password-reset") -- it namespaces this view's cache keys
    from every other throttled view and from unrelated cache users (e.g. the
    background task queue's day-lock, keyed `birthday-reminders:<date>`).

    Views with no form_valid() of their own get correct behavior automatically via
    this mixin's form_valid(). A view with its own form_valid() (anything that does
    more than call super()) must call `is_throttled()`/`throttled_response()`
    explicitly, as its first step -- see SignupView.
    """

    throttle_scope: str = ""

    def _key(self, suffix: str) -> str:
        return f"throttle:{self.throttle_scope}:{suffix}"

    def is_throttled(self, email: str) -> bool:
        normalized = BaseUserManager.normalize_email(email)
        global_count = _hit(self._key("global"), HOUR)
        hourly_count = _hit(self._key(f"email:{normalized}:hour"), HOUR)
        daily_count = _hit(self._key(f"email:{normalized}:day"), DAY)
        return (
            global_count > GLOBAL_HOURLY_LIMIT
            or hourly_count > PER_EMAIL_HOURLY_LIMIT
            or daily_count > PER_EMAIL_DAILY_LIMIT
        )

    def throttled_response(self, form):
        # A non-field error so the message doesn't read as being about any specific
        # field (in particular, not the email field -- that would itself hint at
        # whether the address is recognized). Same wording regardless of whether the
        # email exists: no enumeration signal either way.
        form.add_error(None, THROTTLE_MESSAGE)
        response = self.form_invalid(form)
        response.status_code = 429
        return response

    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        if email and self.is_throttled(email):
            return self.throttled_response(form)
        return super().form_valid(form)
