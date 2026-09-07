import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from events.models import Event


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.fixture
def group(db):
    return Group.objects.create(name="SCI grand chalet")


# ---------------------------------------------------------------------------
# Token resolution
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ical_feed_invalid_token_404(client):
    response = client.get(reverse("ical-feed", kwargs={"token": "not-a-real-token"}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_ical_feed_valid_token_returns_200_unauthenticated(client, account):
    token = account.get_or_create_calendar_token()
    response = client.get(reverse("ical-feed", kwargs={"token": token}))
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")


@pytest.mark.django_db
def test_ical_feed_body_is_a_valid_vcalendar(client, account):
    token = account.get_or_create_calendar_token()
    response = client.get(reverse("ical-feed", kwargs={"token": token}))
    body = response.content.decode("utf-8")
    assert body.startswith("BEGIN:VCALENDAR")
    assert body.rstrip().endswith("END:VCALENDAR")


# ---------------------------------------------------------------------------
# Access scoping (highest-severity risk: no leak of a restricted event)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ical_feed_excludes_restricted_event_for_non_member(client, account, group):
    today = datetime.date.today()
    event = Event.objects.create(title="Réunion privée", start=_aware(today.year, today.month, today.day, 12, 0))
    event.groups.add(group)
    token = account.get_or_create_calendar_token()

    response = client.get(reverse("ical-feed", kwargs={"token": token}))
    assert event.title not in response.content.decode("utf-8")


@pytest.mark.django_db
def test_ical_feed_includes_restricted_event_for_group_member(client, account, group):
    today = datetime.date.today()
    account.groups.add(group)
    event = Event.objects.create(title="Réunion privée", start=_aware(today.year, today.month, today.day, 12, 0))
    event.groups.add(group)
    token = account.get_or_create_calendar_token()

    response = client.get(reverse("ical-feed", kwargs={"token": token}))
    assert event.title in response.content.decode("utf-8")


@pytest.mark.django_db
def test_ical_feed_staff_does_not_see_restricted_event_outside_their_groups(client, staff_account, group):
    """Staff status must NOT expand the feed -- it represents this specific
    account's own effective access, not "everything"."""
    today = datetime.date.today()
    event = Event.objects.create(title="Réunion privée", start=_aware(today.year, today.month, today.day, 12, 0))
    event.groups.add(group)
    token = staff_account.get_or_create_calendar_token()

    response = client.get(reverse("ical-feed", kwargs={"token": token}))
    assert event.title not in response.content.decode("utf-8")


@pytest.mark.django_db
def test_ical_feed_includes_unrestricted_event(client, account):
    today = datetime.date.today()
    event = Event.objects.create(title="Barbecue", start=_aware(today.year, today.month, today.day, 12, 0))
    token = account.get_or_create_calendar_token()

    response = client.get(reverse("ical-feed", kwargs={"token": token}))
    assert event.title in response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# Type filtering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ical_feed_filter_types_event_only(client, account, presence):
    today = datetime.date.today()
    event = Event.objects.create(title="Barbecue", start=_aware(today.year, today.month, today.day, 12, 0))
    token = account.get_or_create_calendar_token()

    response = client.get(reverse("ical-feed", kwargs={"token": token}), {"types": "event"})
    body = response.content.decode("utf-8")
    assert event.title in body
    assert presence.chalet.name not in body


# ---------------------------------------------------------------------------
# Token regeneration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_regenerate_calendar_token_requires_login(client):
    response = client.post(reverse("regenerate-calendar-token"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_regenerate_calendar_token_changes_the_token(auth_client, account):
    old_token = account.get_or_create_calendar_token()
    response = auth_client.post(reverse("regenerate-calendar-token"))
    assert response.status_code == 302
    account.refresh_from_db()
    assert account.calendar_token != old_token


@pytest.mark.django_db
def test_regenerate_calendar_token_invalidates_old_link(client, auth_client, account):
    old_token = account.get_or_create_calendar_token()
    auth_client.post(reverse("regenerate-calendar-token"))

    response = client.get(reverse("ical-feed", kwargs={"token": old_token}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_two_accounts_never_share_a_token(account, other_account):
    assert account.get_or_create_calendar_token() != other_account.get_or_create_calendar_token()
