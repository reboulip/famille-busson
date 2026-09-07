import datetime

import pytest
from django.utils import timezone

from annuaire.calendar_data import build_calendar_entries, parse_types_param
from events.models import Event


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.fixture
def group(db):
    from django.contrib.auth.models import Group

    return Group.objects.create(name="SCI grand chalet")


# ---------------------------------------------------------------------------
# parse_types_param
# ---------------------------------------------------------------------------


def test_parse_types_param_none_for_empty_string():
    assert parse_types_param("") is None
    assert parse_types_param(None) is None


def test_parse_types_param_parses_valid_types():
    assert parse_types_param("event,birthday") == {"event", "birthday"}


def test_parse_types_param_drops_unknown_types():
    assert parse_types_param("event,nonsense") == {"event"}


def test_parse_types_param_none_when_nothing_valid():
    assert parse_types_param("nonsense") is None


# ---------------------------------------------------------------------------
# build_calendar_entries
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_build_calendar_entries_includes_event(account, person):
    today = datetime.date.today()
    event = Event.objects.create(title="Barbecue", start=_aware(today.year, today.month, today.day, 12, 0))
    entries = build_calendar_entries(account, today, today + datetime.timedelta(days=1))
    assert any(e.type == "event" and e.title == event.title for e in entries)


@pytest.mark.django_db
def test_build_calendar_entries_includes_presence(account, presence):
    today = datetime.date.today()
    entries = build_calendar_entries(account, today, today + datetime.timedelta(days=60))
    assert any(e.type == "presence" for e in entries)


@pytest.mark.django_db
def test_build_calendar_entries_includes_birthday(account, person):
    today = datetime.date.today()
    person.birth_date = datetime.date(1990, today.month, today.day)
    person.save()
    entries = build_calendar_entries(account, today, today)
    assert any(e.type == "birthday" and str(person) in e.title for e in entries)


@pytest.mark.django_db
def test_build_calendar_entries_excludes_deceased_birthday(account, person):
    today = datetime.date.today()
    person.birth_date = datetime.date(1990, today.month, today.day)
    person.deceased = True
    person.save()
    entries = build_calendar_entries(account, today, today)
    assert not any(e.type == "birthday" for e in entries)


@pytest.mark.django_db
def test_build_calendar_entries_respects_types_filter(account, person, presence):
    today = datetime.date.today()
    Event.objects.create(title="Barbecue", start=_aware(today.year, today.month, today.day, 12, 0))
    entries = build_calendar_entries(account, today, today + datetime.timedelta(days=60), types={"event"})
    assert all(e.type == "event" for e in entries)


@pytest.mark.django_db
def test_build_calendar_entries_excludes_restricted_event_for_non_member(account, group):
    today = datetime.date.today()
    event = Event.objects.create(title="Réunion privée", start=_aware(today.year, today.month, today.day, 12, 0))
    event.groups.add(group)
    entries = build_calendar_entries(account, today, today)
    assert not any(e.type == "event" for e in entries)


@pytest.mark.django_db
def test_build_calendar_entries_includes_restricted_event_for_group_member(account, group):
    today = datetime.date.today()
    account.groups.add(group)
    event = Event.objects.create(title="Réunion privée", start=_aware(today.year, today.month, today.day, 12, 0))
    event.groups.add(group)
    entries = build_calendar_entries(account, today, today)
    assert any(e.type == "event" and e.title == event.title for e in entries)


@pytest.mark.django_db
def test_build_calendar_entries_uid_includes_host_when_given(account, person):
    today = datetime.date.today()
    Event.objects.create(title="Barbecue", start=_aware(today.year, today.month, today.day, 12, 0))
    entries = build_calendar_entries(account, today, today, host="example.com")
    assert all(e.uid.endswith("@example.com") for e in entries)
