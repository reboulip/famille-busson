"""The annuaire.W005 check (blank SiteConfig.site_name outside DEBUG)."""

import pytest
from django.core.checks import Warning
from django.db import ProgrammingError
from django.test import override_settings

from annuaire.checks import site_name_check
from annuaire.models import SiteConfig


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_check_warns_when_site_name_blank_in_production():
    warnings = site_name_check(None)
    assert len(warnings) == 1
    assert isinstance(warnings[0], Warning)
    assert warnings[0].id == "annuaire.W005"


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_check_is_silent_once_site_name_is_set():
    SiteConfig.objects.create(site_name="Ma Famille")
    assert site_name_check(None) == []


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_check_is_silent_under_debug():
    assert site_name_check(None) == []


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_check_is_silent_when_the_table_does_not_exist_yet(monkeypatch):
    """System checks run before `migrate` applies anything: on a database that has
    never been migrated, this check must stay quiet instead of aborting migrate."""
    monkeypatch.setattr(
        "annuaire.checks.get_site_config",
        lambda: (_ for _ in ()).throw(ProgrammingError('relation "annuaire_siteconfig" does not exist')),
    )
    assert site_name_check(None) == []
