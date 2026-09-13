"""The annuaire.W006 check (unset DEFAULT_FROM_EMAIL and no SiteConfig.sender_address
outside DEBUG, 16.6's neutralization of the code-level DEFAULT_FROM_EMAIL default)."""

import pytest
from django.core.checks import Warning
from django.test import override_settings

from annuaire.checks import default_from_email_check
from annuaire.models import SiteConfig


@pytest.mark.django_db
@override_settings(DEBUG=False, DEFAULT_FROM_EMAIL="")
def test_check_warns_when_both_default_from_email_and_sender_address_are_unset():
    warnings = default_from_email_check(None)
    assert len(warnings) == 1
    assert isinstance(warnings[0], Warning)
    assert warnings[0].id == "annuaire.W006"


@pytest.mark.django_db
@override_settings(DEBUG=False, DEFAULT_FROM_EMAIL="no-reply@example.com")
def test_check_is_silent_when_default_from_email_is_set():
    assert default_from_email_check(None) == []


@pytest.mark.django_db
@override_settings(DEBUG=False, DEFAULT_FROM_EMAIL="")
def test_check_is_silent_when_sender_address_is_set():
    SiteConfig.objects.create(sender_address="no-reply@example.com")
    assert default_from_email_check(None) == []


@pytest.mark.django_db
@override_settings(DEBUG=True, DEFAULT_FROM_EMAIL="")
def test_check_is_silent_under_debug():
    assert default_from_email_check(None) == []
