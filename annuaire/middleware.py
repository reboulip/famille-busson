from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    EXEMPT_URL_NAMES = ("password-change-forced", "logout", "login")
    EXEMPT_URL_PREFIXES = ("/admin/", "/annuaire/password/reset/")

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
