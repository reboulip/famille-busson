import importlib

import pytest
from django.apps import apps

from annuaire.models import Person, Settings

_migration = importlib.import_module("annuaire.migrations.0011_notifications_opt_in_by_default")


@pytest.mark.django_db
def test_backfill_creates_missing_settings_row():
    person = Person.objects.create(first_name="Alice", last_name="Busson")
    # Simulate a historical Person predating the Settings model -- the post_save
    # signal that normally auto-creates Settings never ran for one.
    Settings.objects.filter(person=person).delete()
    assert not Settings.objects.filter(person=person).exists()

    _migration.backfill_notifications_checked(apps, None)

    settings = Settings.objects.get(person=person)
    assert settings.notify_on_birthday is True
    assert settings.notify_on_new_blog_post is True


@pytest.mark.django_db
def test_backfill_checks_every_existing_settings_row():
    person = Person.objects.create(first_name="Alice", last_name="Busson")
    other_person = Person.objects.create(first_name="Bob", last_name="Busson")
    Settings.objects.filter(person__in=[person, other_person]).update(
        notify_on_birthday=False, notify_on_new_blog_post=False
    )

    _migration.backfill_notifications_checked(apps, None)

    for p in (person, other_person):
        p.settings.refresh_from_db()
        assert p.settings.notify_on_birthday is True
        assert p.settings.notify_on_new_blog_post is True
