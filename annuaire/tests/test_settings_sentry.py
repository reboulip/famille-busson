"""Sentry init guard, the annuaire.W003 check, and the before_send PII scrubber (9.9)."""

import typing

from django.core.checks import Warning
from django.test import override_settings
from sentry_sdk.types import Event, Hint

from annuaire.checks import sentry_dsn_check
from famille_busson.settings import _sentry_before_send

# _sentry_before_send is typed against sentry-sdk's own Event/Hint TypedDicts, so a
# plain dict literal needs an explicit cast to satisfy ty -- the real shape has many
# more (optional) keys than any single test constructs.
_NO_HINT = typing.cast(Hint, {})


def test_before_send_drops_cookies():
    event = typing.cast(Event, {"request": {"cookies": {"sessionid": "abc"}, "url": "https://example.com"}})
    result = _sentry_before_send(event, _NO_HINT)
    assert "cookies" not in result["request"]
    assert result["request"]["url"] == "https://example.com"


def test_before_send_drops_email_keyed_extras_case_insensitively():
    event = typing.cast(Event, {"extra": {"Email": "alice@example.com", "other": "kept"}})
    result = _sentry_before_send(event, _NO_HINT)
    assert "Email" not in result["extra"]
    assert result["extra"]["other"] == "kept"


def test_before_send_drops_email_keyed_contexts():
    event = typing.cast(Event, {"contexts": {"email": "alice@example.com", "other": "kept"}})
    result = _sentry_before_send(event, _NO_HINT)
    assert "email" not in result["contexts"]
    assert result["contexts"]["other"] == "kept"


def test_before_send_is_a_noop_on_an_event_with_neither():
    event = typing.cast(Event, {"message": "boom"})
    assert _sentry_before_send(event, _NO_HINT) == {"message": "boom"}


@override_settings(DEBUG=False, SENTRY_DSN="")
def test_check_warns_when_dsn_unset_in_production():
    warnings = sentry_dsn_check(None)
    assert len(warnings) == 1
    assert isinstance(warnings[0], Warning)
    assert warnings[0].id == "annuaire.W003"


@override_settings(DEBUG=False, SENTRY_DSN="https://key@sentry.io/1")
def test_check_is_silent_with_a_dsn_in_production():
    assert sentry_dsn_check(None) == []


@override_settings(DEBUG=True, SENTRY_DSN="")
def test_check_is_silent_under_debug():
    assert sentry_dsn_check(None) == []
