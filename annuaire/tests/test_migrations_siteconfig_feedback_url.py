import importlib

import pytest
from django.apps import apps

from annuaire.models import SiteConfig

_migration = importlib.import_module("annuaire.migrations.0028_siteconfig_restore_feedback_url")

FEEDBACK_URL = "https://github.com/reboulip/famille-busson/issues/new"


@pytest.mark.django_db
def test_restores_the_url_on_the_seeded_empty_row():
    SiteConfig.objects.create(pk=1, site_name="Famille Busson", feedback_url="")

    _migration.restore_feedback_url(apps, None)

    config = SiteConfig.objects.get(pk=1)
    assert config.feedback_url == FEEDBACK_URL


@pytest.mark.django_db
def test_leaves_an_already_set_url_alone():
    SiteConfig.objects.create(pk=1, site_name="Famille Busson", feedback_url="https://example.com/report")

    _migration.restore_feedback_url(apps, None)

    config = SiteConfig.objects.get(pk=1)
    assert config.feedback_url == "https://example.com/report"


@pytest.mark.django_db
def test_leaves_a_differently_named_site_alone():
    SiteConfig.objects.create(pk=1, site_name="Une Autre Famille", feedback_url="")

    _migration.restore_feedback_url(apps, None)

    config = SiteConfig.objects.get(pk=1)
    assert config.feedback_url == ""


@pytest.mark.django_db
def test_no_row_is_a_no_op():
    assert not SiteConfig.objects.exists()

    _migration.restore_feedback_url(apps, None)

    assert not SiteConfig.objects.exists()
