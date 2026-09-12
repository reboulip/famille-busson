import contextvars
import logging
import uuid
from zoneinfo import ZoneInfo

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
# Set by AuditActorMiddleware below; read by annuaire.audit.record_audit_event so
# a signal handler deep in the save path can attribute the change without every
# call site threading `request.user` through. None outside a request (management
# commands, background tasks) -- those changes are recorded with actor=None.
_actor_var: contextvars.ContextVar = contextvars.ContextVar("audit_actor", default=None)


def get_current_actor():
    return _actor_var.get()


class RequestIdLogFilter(logging.Filter):
    """Attaches the current request's id (if any) to every log record, so
    JsonFormatter (annuaire/log_formatters.py) can include it without every call
    site having to pass `extra={"request_id": ...}` by hand."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


class RequestIdMiddleware:
    """Tags every request/response with an id, for correlating the several log
    lines one request can produce. Accepts an inbound X-Request-ID (e.g. from a
    reverse proxy that already generates one) so a request can be traced across
    both hops; generates one otherwise."""

    HEADER = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get(self.HEADER) or uuid.uuid4().hex
        request.request_id = request_id
        token = _request_id_var.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _request_id_var.reset(token)
        response[self.HEADER] = request_id
        return response


class AuditActorMiddleware:
    """Captures the logged-in account for the duration of a request, so
    annuaire.audit's signal receivers (which run deep inside .save()/.delete(),
    with no access to the request) can attribute an AuditEvent to whoever made
    the change. Placed after AuthenticationMiddleware in MIDDLEWARE so
    request.user is already resolved."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        actor = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        token = _actor_var.set(actor)
        try:
            response = self.get_response(request)
        finally:
            _actor_var.reset(token)
        return response


class SiteTimezoneMiddleware:
    """Activates the configured SiteConfig timezone for the duration of a
    request. Placed after SessionMiddleware. Only affects the request/response
    cycle -- management commands and background tasks keep using
    settings.TIME_ZONE, which is also this field's default."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Imported lazily: this module is loaded by LOGGING's request_id filter
        # during django.setup(), before the app registry (and therefore models)
        # is ready -- a top-level import here would break every management
        # command and the dev server at startup.
        from .site_config import get_site_config

        timezone.activate(ZoneInfo(str(get_site_config().timezone)))
        try:
            response = self.get_response(request)
        finally:
            timezone.deactivate()
        return response


class ForcePasswordChangeMiddleware:
    EXEMPT_URL_NAMES = ("password-change-forced", "logout", "login")
    EXEMPT_URL_PREFIXES = ("/admin/", "/annuaire/password/reset/", "/annuaire/login/magic/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, "must_change_password", False)
            and not self._is_exempt(request)
        ):
            return redirect("password-change-forced")
        return self.get_response(request)

    def _is_exempt(self, request):
        exempt_paths = {reverse(name) for name in self.EXEMPT_URL_NAMES}
        return request.path in exempt_paths or request.path.startswith(self.EXEMPT_URL_PREFIXES)
