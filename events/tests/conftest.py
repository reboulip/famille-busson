import datetime

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone

from annuaire.tests.conftest import (  # noqa: F401 -- re-exported as fixtures
    account,
    accountless_person,
    auth_client,
    client,
    other_account,
    other_person,
    owned_person,
    person,
    staff_account,
    staff_client,
)
from events.models import Event


def _aware(*args):
    return timezone.make_aware(datetime.datetime(*args), datetime.UTC)


@pytest.fixture
def group(db):
    return Group.objects.create(name="SCI grand chalet")


@pytest.fixture
def event(db, person):
    # Relative to today, not a hardcoded date -- a fixed future date eventually
    # becomes past and starts failing the "upcoming" listing tests.
    start = timezone.now() + datetime.timedelta(days=30)
    event = Event.objects.create(
        title="Réunion de famille",
        description="Un repas ensemble.",
        start=start,
        end=start + datetime.timedelta(hours=3),
    )
    event.organisers.add(person)
    return event


@pytest.fixture
def restricted_event(db, group):
    start = timezone.now() + datetime.timedelta(days=30)
    event = Event.objects.create(title="Réunion privée", start=start)
    event.groups.add(group)
    return event


@pytest.fixture
def past_event(db):
    return Event.objects.create(title="Ancien événement", start=_aware(2020, 1, 1, 12, 0))
