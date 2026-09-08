import datetime

import pytest

from annuaire.models import Person
from annuaire.privacy import always_redacted, is_living, is_redacted, redacted_display_name, redacted_person_ids


def _years_ago(n: int) -> datetime.date:
    today = datetime.date.today()
    return today.replace(year=today.year - n)


@pytest.mark.django_db
def test_is_living_true_for_recent_birth_date(person):
    person.birth_date = _years_ago(30)
    person.save()
    assert is_living(person) is True


@pytest.mark.django_db
def test_is_living_false_for_deceased_flag(person):
    person.deceased = True
    person.save()
    assert is_living(person) is False


@pytest.mark.django_db
def test_is_living_false_for_death_date(person):
    person.death_date = datetime.date(2000, 1, 1)
    person.save()
    assert is_living(person) is False


@pytest.mark.django_db
def test_is_living_false_when_over_100_years_old(person):
    person.birth_date = _years_ago(101)
    person.save()
    assert is_living(person) is False


@pytest.mark.django_db
def test_is_living_true_when_just_under_100(person):
    person.birth_date = _years_ago(99)
    person.save()
    assert is_living(person) is True


@pytest.mark.django_db
def test_is_living_fails_closed_with_no_birth_date_and_no_deceased_flag(person):
    # No birth date, not flagged deceased: a long-dead ancestor entered
    # without a birth date must not be treated as safe to reveal.
    assert person.birth_date is None
    assert person.deceased is False
    assert is_living(person) is True


@pytest.mark.django_db
def test_is_redacted_auto_redacts_the_living(person):
    person.birth_date = _years_ago(30)
    person.export_privacy = Person.ExportPrivacy.AUTO
    person.save()
    assert is_redacted(person) is True


@pytest.mark.django_db
def test_is_redacted_auto_does_not_redact_the_deceased(person):
    person.deceased = True
    person.export_privacy = Person.ExportPrivacy.AUTO
    person.save()
    assert is_redacted(person) is False


@pytest.mark.django_db
def test_is_redacted_share_never_redacts_even_if_living(person):
    person.birth_date = _years_ago(30)
    person.export_privacy = Person.ExportPrivacy.SHARE
    person.save()
    assert is_redacted(person) is False


@pytest.mark.django_db
def test_is_redacted_redact_always_redacts_even_if_deceased(person):
    person.deceased = True
    person.export_privacy = Person.ExportPrivacy.REDACT
    person.save()
    assert is_redacted(person) is True


@pytest.mark.django_db
def test_always_redacted_ignores_auto_even_for_living_person(person):
    person.birth_date = _years_ago(30)
    person.export_privacy = Person.ExportPrivacy.AUTO
    person.save()
    assert always_redacted(person) is False


@pytest.mark.django_db
def test_always_redacted_true_only_for_explicit_redact(person):
    person.export_privacy = Person.ExportPrivacy.REDACT
    person.save()
    assert always_redacted(person) is True


@pytest.mark.django_db
def test_redacted_person_ids_bulk(person, other_person):
    person.birth_date = _years_ago(30)
    person.export_privacy = Person.ExportPrivacy.AUTO
    person.save()
    other_person.export_privacy = Person.ExportPrivacy.SHARE
    other_person.birth_date = _years_ago(30)
    other_person.save()
    assert redacted_person_ids([person, other_person]) == {person.pk}


def test_redacted_display_name_keeps_surname():
    person = Person(first_name="Alice", last_name="Busson")
    given, surname = redacted_display_name(person)
    assert given == "Vivant"
    assert surname == "Busson"
