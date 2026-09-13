"""resolve_language()'s precedence (Phase 15.5): Account.language -> django_language
cookie -> SiteConfig.default_language -> Accept-Language -> settings.LANGUAGE_CODE."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings

from annuaire.i18n import resolve_language
from annuaire.models import SiteConfig


@pytest.fixture
def anonymous_user():
    return AnonymousUser()


def _request(rf: RequestFactory, *, user, cookie=None, accept_language=None):
    extra = {}
    if accept_language is not None:
        extra["HTTP_ACCEPT_LANGUAGE"] = accept_language
    request = rf.get("/", **extra)
    request.user = user
    if cookie is not None:
        request.COOKIES["django_language"] = cookie
    else:
        request.COOKIES = {}
    return request


def test_authenticated_account_language_wins_over_everything_else(rf, account):
    account.language = "en"
    account.save(update_fields=["language"])
    request = _request(rf, user=account, cookie="fr", accept_language="fr")
    SiteConfig.objects.create(default_language="fr")
    assert resolve_language(request) == "en"


def test_falls_back_to_cookie_when_account_has_no_preference(rf, account):
    request = _request(rf, user=account, cookie="en")
    assert resolve_language(request) == "en"


def test_falls_back_to_site_default_when_no_account_or_cookie_preference(db, rf, anonymous_user):
    SiteConfig.objects.create(default_language="en")
    request = _request(rf, user=anonymous_user)
    assert resolve_language(request) == "en"


def test_falls_back_to_accept_language_header_last(db, rf, anonymous_user):
    request = _request(rf, user=anonymous_user, accept_language="en")
    assert resolve_language(request) == "en"


@override_settings(LANGUAGE_CODE="fr")
def test_falls_back_to_settings_language_code_when_nothing_else_matches(db, rf, anonymous_user):
    request = _request(rf, user=anonymous_user)
    assert resolve_language(request) == "fr"


def test_an_invalid_cookie_value_is_ignored(db, rf, anonymous_user):
    request = _request(rf, user=anonymous_user, cookie="not-a-real-language")
    assert resolve_language(request) == "fr"


def test_an_authenticated_users_blank_language_falls_through(rf, account):
    request = _request(rf, user=account, cookie="en")
    assert resolve_language(request) == "en"
