import pytest
from django.urls import reverse

from events.models import Rsvp

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_rsvp_requires_login(client, event, person):
    response = client.post(
        reverse("event-rsvp", kwargs={"pk": event.pk}),
        {"person": person.pk, "response": "yes", "guest_count": 0},
    )
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_rsvp_creates_response_for_self(auth_client, event, person):
    response = auth_client.post(
        reverse("event-rsvp", kwargs={"pk": event.pk}),
        {"person": person.pk, "response": "yes", "guest_count": 2, "note": "On arrive tôt"},
    )
    assert response.status_code == 302
    rsvp = Rsvp.objects.get(event=event, person=person)
    assert rsvp.response == "yes"
    assert rsvp.guest_count == 2
    assert rsvp.note == "On arrive tôt"


@pytest.mark.django_db
def test_rsvp_updates_existing_response(auth_client, event, person):
    Rsvp.objects.create(event=event, person=person, response="maybe")
    auth_client.post(
        reverse("event-rsvp", kwargs={"pk": event.pk}),
        {"person": person.pk, "response": "no", "guest_count": 0},
    )
    rsvp = Rsvp.objects.get(event=event, person=person)
    assert rsvp.response == "no"
    assert Rsvp.objects.filter(event=event, person=person).count() == 1


@pytest.mark.django_db
def test_rsvp_forbidden_for_person_the_user_cannot_edit(auth_client, event, other_person):
    response = auth_client.post(
        reverse("event-rsvp", kwargs={"pk": event.pk}),
        {"person": other_person.pk, "response": "yes", "guest_count": 0},
    )
    assert response.status_code == 403
    assert not Rsvp.objects.filter(event=event, person=other_person).exists()


@pytest.mark.django_db
def test_rsvp_allowed_for_owned_accountless_person(auth_client, event, owned_person):
    response = auth_client.post(
        reverse("event-rsvp", kwargs={"pk": event.pk}),
        {"person": owned_person.pk, "response": "yes", "guest_count": 0},
    )
    assert response.status_code == 302
    assert Rsvp.objects.filter(event=event, person=owned_person, response="yes").exists()


@pytest.mark.django_db
def test_rsvp_forbidden_for_restricted_event_non_member(auth_client, restricted_event, person):
    response = auth_client.post(
        reverse("event-rsvp", kwargs={"pk": restricted_event.pk}),
        {"person": person.pk, "response": "yes", "guest_count": 0},
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_event_detail_shows_attendee_headcount(auth_client, event, person, other_person):
    Rsvp.objects.create(event=event, person=person, response="yes", guest_count=1)
    Rsvp.objects.create(event=event, person=other_person, response="yes", guest_count=0)
    response = auth_client.get(reverse("event-detail", kwargs={"pk": event.pk}))
    assert response.context["attendee_headcount"] == 3


@pytest.mark.django_db
def test_event_detail_rsvp_rows_include_self(auth_client, event, person):
    response = auth_client.get(reverse("event-detail", kwargs={"pk": event.pk}))
    people = [row[0] for row in response.context["rsvp_rows"]]
    assert person in people
