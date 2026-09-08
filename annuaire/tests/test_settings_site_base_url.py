"""SITE_BASE_URL's non-localhost fallback derivation and the accompanying warning
system check (Phase 8.1) -- production emails must not silently link to localhost."""

from django.core.checks import Warning
from django.test import override_settings

from annuaire.checks import site_base_url_check
from famille_busson.settings import _default_site_base_url


def test_derives_from_the_first_csrf_trusted_origin():
    assert _default_site_base_url(["https://bubu.reboulip.fr"], ["bubu.reboulip.fr"]) == "https://bubu.reboulip.fr"


def test_falls_back_to_the_first_real_allowed_host_when_no_csrf_origin():
    assert _default_site_base_url([], ["bubu.reboulip.fr"]) == "https://bubu.reboulip.fr"


def test_skips_wildcard_and_localhost_allowed_hosts():
    assert (
        _default_site_base_url([], ["*", ".internal", "localhost", "127.0.0.1", "bubu.reboulip.fr"])
        == "https://bubu.reboulip.fr"
    )


def test_falls_back_to_localhost_when_nothing_usable_is_configured():
    assert _default_site_base_url([], []) == "http://localhost:8000"
    assert _default_site_base_url([], ["*"]) == "http://localhost:8000"


@override_settings(DEBUG=False, SITE_BASE_URL="http://localhost:8000")
def test_check_warns_when_localhost_in_production():
    warnings = site_base_url_check(None)
    assert len(warnings) == 1
    assert isinstance(warnings[0], Warning)
    assert warnings[0].id == "annuaire.W001"


@override_settings(DEBUG=False, SITE_BASE_URL="https://bubu.reboulip.fr")
def test_check_is_silent_with_a_real_domain_in_production():
    assert site_base_url_check(None) == []


@override_settings(DEBUG=True, SITE_BASE_URL="http://localhost:8000")
def test_check_is_silent_under_debug():
    assert site_base_url_check(None) == []
