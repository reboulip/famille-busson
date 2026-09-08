import contextvars
import logging
import uuid

from django.shortcuts import redirect
from django.urls import reverse

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


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
