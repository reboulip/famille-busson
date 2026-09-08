import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from events.models import Event


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.fixture
def group(db):
    from django.contrib.auth.models import Group

    return Group.objects.create(name="SCI grand chalet")


@pytest.mark.django_db
def test_home_shows_upcoming_event(auth_client, person):
    event = Event.objects.create(title="Barbecue", start=timezone.now() + datetime.timedelta(days=1))
    response = auth_client.get(reverse("home"))
    assert event in response.context["upcoming_events"]


@pytest.mark.django_db
def test_home_hides_past_event(auth_client, person):
    event = Event.objects.create(title="Ancien événement", start=timezone.now() - datetime.timedelta(days=1))
    response = auth_client.get(reverse("home"))
    assert event not in response.context["upcoming_events"]


@pytest.mark.django_db
def test_home_hides_restricted_event_for_non_member(auth_client, person, group):
    event = Event.objects.create(title="Réunion privée", start=timezone.now() + datetime.timedelta(days=1))
    event.groups.add(group)
    response = auth_client.get(reverse("home"))
    assert event not in response.context["upcoming_events"]


@pytest.mark.django_db
def test_home_shows_restricted_event_for_group_member(auth_client, person, account, group):
    account.groups.add(group)
    event = Event.objects.create(title="Réunion privée", start=timezone.now() + datetime.timedelta(days=1))
    event.groups.add(group)
    response = auth_client.get(reverse("home"))
    assert event in response.context["upcoming_events"]


@pytest.mark.django_db
def test_home_links_events_card_to_event_list(auth_client, person):
    response = auth_client.get(reverse("home"))
    content = response.content.decode()
    assert reverse("event-list") in content
