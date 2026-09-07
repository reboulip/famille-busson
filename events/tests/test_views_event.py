import pytest
from django.urls import reverse

from events.models import Event

LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# EventListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_event_list_requires_login(client):
    response = client.get(reverse("event-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_event_list_returns_200(auth_client):
    response = auth_client.get(reverse("event-list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_list_shows_upcoming_event(auth_client, event):
    response = auth_client.get(reverse("event-list"))
    assert event.title in response.content.decode()


@pytest.mark.django_db
def test_event_list_hides_past_event_by_default(auth_client, past_event):
    response = auth_client.get(reverse("event-list"))
    assert past_event.title not in response.content.decode()


@pytest.mark.django_db
def test_event_list_passes_toggle_shows_past_event(auth_client, past_event):
    response = auth_client.get(reverse("event-list") + "?passes=1")
    assert past_event.title in response.content.decode()


@pytest.mark.django_db
def test_event_list_hides_restricted_event_for_non_member(auth_client, restricted_event):
    response = auth_client.get(reverse("event-list"))
    assert restricted_event.title not in response.content.decode()


@pytest.mark.django_db
def test_event_list_shows_restricted_event_for_group_member(auth_client, restricted_event, account, group):
    account.groups.add(group)
    response = auth_client.get(reverse("event-list"))
    assert restricted_event.title in response.content.decode()


# ---------------------------------------------------------------------------
# EventDetailView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_event_detail_requires_login(client, event):
    response = client.get(reverse("event-detail", kwargs={"pk": event.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_event_detail_returns_200(auth_client, event):
    response = auth_client.get(reverse("event-detail", kwargs={"pk": event.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_detail_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("event-detail", kwargs={"pk": 999999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_event_detail_404_for_restricted_event_non_member(auth_client, restricted_event):
    """Locked events are invisible, never visible-but-locked."""
    response = auth_client.get(reverse("event-detail", kwargs={"pk": restricted_event.pk}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_event_detail_200_for_restricted_event_group_member(auth_client, restricted_event, account, group):
    account.groups.add(group)
    response = auth_client.get(reverse("event-detail", kwargs={"pk": restricted_event.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_detail_can_edit_true_for_organiser(auth_client, event):
    response = auth_client.get(reverse("event-detail", kwargs={"pk": event.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_event_detail_can_edit_false_for_non_organiser(auth_client, event, other_person):
    event.organisers.set([other_person])
    response = auth_client.get(reverse("event-detail", kwargs={"pk": event.pk}))
    assert response.context["can_edit"] is False


@pytest.mark.django_db
def test_event_detail_can_edit_true_for_staff(staff_client, event):
    response = staff_client.get(reverse("event-detail", kwargs={"pk": event.pk}))
    assert response.context["can_edit"] is True


# ---------------------------------------------------------------------------
# EventCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_event_create_requires_login(client):
    response = client.get(reverse("event-create"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_event_create_redirects_account_without_profile(client, db):
    from annuaire.models import Account

    # A fresh email with no matching Person -- the post-save signal only
    # auto-links when a same-email Person already exists.
    Account.objects.create_user(email="noprofile@example.com", password="testpass123!")
    client.login(username="noprofile@example.com", password="testpass123!")
    response = client.get(reverse("event-create"))
    assert response.status_code == 302
    assert reverse("profile-create") in response["Location"]


@pytest.mark.django_db
def test_event_create_get_returns_200(auth_client):
    response = auth_client.get(reverse("event-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_create_post_creates_event(auth_client, person):
    response = auth_client.post(
        reverse("event-create"),
        {
            "title": "Barbecue",
            "description": "",
            "start": "2026-07-14T12:00",
            "end": "2026-07-14T18:00",
            "location": "",
            "organisers": [str(person.pk)],
        },
    )
    assert response.status_code == 302
    assert Event.objects.filter(title="Barbecue").exists()


@pytest.mark.django_db
def test_event_create_post_auto_assigns_creator_as_organiser(auth_client, person):
    response = auth_client.post(
        reverse("event-create"),
        {
            "title": "Barbecue",
            "description": "",
            "start": "2026-07-14T12:00",
            "end": "2026-07-14T18:00",
            "location": "",
        },
    )
    assert response.status_code == 302
    event = Event.objects.get(title="Barbecue")
    assert person in event.organisers.all()


@pytest.mark.django_db
def test_event_create_post_invalid_returns_200_with_errors(auth_client):
    response = auth_client.post(reverse("event-create"), {"title": "", "start": ""})
    assert response.status_code == 200
    assert not Event.objects.filter(title="").exists()


# ---------------------------------------------------------------------------
# EventUpdateView / EventDeleteView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_event_edit_requires_login(client, event):
    response = client.get(reverse("event-edit", kwargs={"pk": event.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_event_edit_allowed_for_organiser(auth_client, event):
    response = auth_client.get(reverse("event-edit", kwargs={"pk": event.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_edit_forbidden_for_non_organiser(auth_client, event, other_person):
    event.organisers.set([other_person])
    response = auth_client.get(reverse("event-edit", kwargs={"pk": event.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_event_edit_allowed_for_staff(staff_client, event):
    response = staff_client.get(reverse("event-edit", kwargs={"pk": event.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_event_delete_forbidden_for_non_organiser(auth_client, event, other_person):
    event.organisers.set([other_person])
    response = auth_client.get(reverse("event-delete", kwargs={"pk": event.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_event_delete_post_removes_event(auth_client, event):
    response = auth_client.post(reverse("event-delete", kwargs={"pk": event.pk}))
    assert response.status_code == 302
    assert not Event.objects.filter(pk=event.pk).exists()
