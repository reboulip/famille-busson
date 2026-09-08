import pytest
from django.db import IntegrityError

from events.models import Rsvp


@pytest.mark.django_db
def test_rsvp_str(event, person):
    rsvp = Rsvp.objects.create(event=event, person=person, response="yes")
    assert str(rsvp) == f"{person} — Oui ({event})"


@pytest.mark.django_db
def test_rsvp_unique_constraint_per_event_person(event, person):
    Rsvp.objects.create(event=event, person=person, response="yes")
    with pytest.raises(IntegrityError):
        Rsvp.objects.create(event=event, person=person, response="no")


@pytest.mark.django_db
def test_rsvp_guest_count_defaults_to_zero(event, person):
    rsvp = Rsvp.objects.create(event=event, person=person, response="yes")
    assert rsvp.guest_count == 0
