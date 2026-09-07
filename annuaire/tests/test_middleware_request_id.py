"""Per-request id middleware (9.9) -- annuaire.middleware.RequestIdMiddleware."""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from annuaire.middleware import RequestIdMiddleware, _request_id_var


@pytest.mark.django_db
def test_generates_a_request_id_when_none_is_supplied():
    request = RequestFactory().get("/")
    response = RequestIdMiddleware(lambda r: HttpResponse())(request)
    assert response["X-Request-ID"]
    assert request.request_id == response["X-Request-ID"]


@pytest.mark.django_db
def test_reuses_an_inbound_request_id_header():
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID="upstream-id-123")
    response = RequestIdMiddleware(lambda r: HttpResponse())(request)
    assert response["X-Request-ID"] == "upstream-id-123"


@pytest.mark.django_db
def test_the_context_var_is_set_during_the_request_and_cleared_after():
    seen_during = []

    def get_response(request):
        seen_during.append(_request_id_var.get())
        return HttpResponse()

    request = RequestFactory().get("/")
    assert _request_id_var.get() is None

    RequestIdMiddleware(get_response)(request)

    assert seen_during[0] is not None
    assert _request_id_var.get() is None
