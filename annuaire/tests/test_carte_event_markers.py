import datetime
import json
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from events.models import Event


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.mark.django_db
def test_carte_includes_events_with_coordinates(auth_client, person):
    event = Event.objects.create(
        title="Barbecue", start=_aware(2026, 7, 1, 12, 0), latitude=Decimal("46.096"), longitude=Decimal("7.228")
    )
    response = auth_client.get(reverse("carte"))
    events = json.loads(response.context["events_json"])
    assert events[0]["entries"][0]["name"] == event.title
    assert events[0]["entries"][0]["url"] == reverse("event-detail", kwargs={"pk": event.pk})


@pytest.mark.django_db
def test_carte_excludes_events_without_coordinates(auth_client, person):
    Event.objects.create(title="Barbecue", start=_aware(2026, 7, 1, 12, 0))
    response = auth_client.get(reverse("carte"))
    events = json.loads(response.context["events_json"])
    assert events == []
