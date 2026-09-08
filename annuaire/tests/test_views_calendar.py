import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from events.models import Event

LOGIN_URL = "/annuaire/login/"


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.mark.django_db
def test_calendar_requires_login(client):
    response = client.get(reverse("calendrier"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_calendar_returns_200(auth_client):
    response = auth_client.get(reverse("calendrier"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_calendar_shows_empty_state_with_no_entries(auth_client):
    response = auth_client.get(reverse("calendrier"))
    assert response.context["has_entries"] is False


@pytest.mark.django_db
def test_calendar_context_has_event_entry(auth_client, person):
    today = datetime.date.today()
    Event.objects.create(title="Barbecue", start=_aware(today.year, today.month, today.day, 12, 0))
    response = auth_client.get(reverse("calendrier"))
    assert response.context["has_entries"] is True
    assert "Barbecue" in response.content.decode()


@pytest.mark.django_db
def test_calendar_feed_ajax_requires_login(client):
    response = client.get(reverse("calendar-feed-ajax"), {"start": "2026-01-01", "end": "2026-01-31"})
    assert response.status_code == 302


@pytest.mark.django_db
def test_calendar_feed_ajax_returns_entries(auth_client, person):
    today = datetime.date.today()
    Event.objects.create(title="Barbecue", start=_aware(today.year, today.month, today.day, 12, 0))
    response = auth_client.get(reverse("calendar-feed-ajax"), {"start": today.isoformat(), "end": today.isoformat()})
    assert response.status_code == 200
    data = response.json()
    assert any(e["type"] == "event" and e["title"] == "Barbecue" for e in data["entries"])


@pytest.mark.django_db
def test_calendar_feed_ajax_invalid_dates_returns_400(auth_client):
    response = auth_client.get(reverse("calendar-feed-ajax"), {"start": "nope", "end": "nope"})
    assert response.status_code == 400


@pytest.mark.django_db
def test_calendar_feed_ajax_respects_types_filter(auth_client, person, presence):
    today = datetime.date.today()
    Event.objects.create(title="Barbecue", start=_aware(today.year, today.month, today.day, 12, 0))
    response = auth_client.get(
        reverse("calendar-feed-ajax"),
        {"start": today.isoformat(), "end": (today + datetime.timedelta(days=60)).isoformat(), "types": "event"},
    )
    data = response.json()
    assert all(e["type"] == "event" for e in data["entries"])
