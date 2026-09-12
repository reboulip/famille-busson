import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from annuaire.models import AuditEvent, Person, Relation

LOGIN_URL = "/annuaire/login/"


def _empty_formset_data(prefix="ascending_relations"):
    return {
        f"{prefix}-TOTAL_FORMS": "0",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


@pytest.fixture
def group(db):
    return Group.objects.create(name="SCI grand chalet")


# --- register_audit: create / update / delete ---------------------------


@pytest.mark.django_db
def test_create_logs_audit_event():
    person = Person.objects.create(first_name="Denise", last_name="Busson")
    event = AuditEvent.objects.get(content_type__model="person", object_id=str(person.pk))
    assert event.action == AuditEvent.Action.CREATE
    assert event.object_repr == str(person)


@pytest.mark.django_db
def test_update_tracked_field_logs_changes(person):
    AuditEvent.objects.all().delete()
    person.first_name = "Alicia"
    person.save()
    event = AuditEvent.objects.get(
        content_type__model="person", object_id=str(person.pk), action=AuditEvent.Action.UPDATE
    )
    assert event.changes["first_name"] == {"from": "Alice", "to": "Alicia"}


@pytest.mark.django_db
def test_update_untracked_field_does_not_log(person):
    AuditEvent.objects.all().delete()
    person.search_text = "some indexed text"
    person.save()
    assert not AuditEvent.objects.filter(content_type__model="person", object_id=str(person.pk)).exists()


@pytest.mark.django_db
def test_delete_logs_audit_event(person):
    label = str(person)
    pk = person.pk
    person.delete()
    event = AuditEvent.objects.get(content_type__model="person", object_id=str(pk), action=AuditEvent.Action.DELETE)
    assert event.object_repr == label


@pytest.mark.django_db
def test_relation_create_logs_audit_event(person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    assert AuditEvent.objects.filter(content_type__model="relation", action=AuditEvent.Action.CREATE).exists()


# --- Actor capture --------------------------------------------------------


@pytest.mark.django_db
def test_actor_is_none_outside_a_request(person):
    AuditEvent.objects.all().delete()
    person.first_name = "Changed"
    person.save()
    event = AuditEvent.objects.get(content_type__model="person", object_id=str(person.pk))
    assert event.actor is None
    assert event.actor_label == ""


@pytest.mark.django_db
def test_actor_is_captured_from_the_request(auth_client, person):
    AuditEvent.objects.all().delete()
    data = {"first_name": "Alice", "last_name": "Bussonne"}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    event = AuditEvent.objects.get(
        content_type__model="person", object_id=str(person.pk), action=AuditEvent.Action.UPDATE
    )
    assert event.actor_id == person.account_id


# --- M2M membership audit -------------------------------------------------


@pytest.mark.django_db
def test_group_membership_add_logs_audit_event_against_the_account(staff_client, group, person):
    AuditEvent.objects.all().delete()
    response = staff_client.post(reverse("group-members-edit", kwargs={"pk": group.pk}), {"members": [str(person.pk)]})
    assert response.status_code == 302
    event = AuditEvent.objects.get(content_type__model="account", action=AuditEvent.Action.MEMBERSHIP_ADD)
    assert event.object_id == str(person.account_id)
    assert event.changes["groupes"]["to"] == group.name


@pytest.mark.django_db
def test_group_membership_remove_logs_audit_event(staff_client, group, person):
    person.account.groups.add(group)
    AuditEvent.objects.all().delete()
    response = staff_client.post(reverse("group-members-edit", kwargs={"pk": group.pk}), {"members": []})
    assert response.status_code == 302
    assert AuditEvent.objects.filter(
        content_type__model="account", action=AuditEvent.Action.MEMBERSHIP_REMOVE
    ).exists()


@pytest.mark.django_db
def test_person_owners_add_logs_audit_event_against_the_managed_profile(accountless_person, person):
    AuditEvent.objects.all().delete()
    accountless_person.owners.add(person)
    event = AuditEvent.objects.get(
        content_type__model="person", object_id=str(accountless_person.pk), action=AuditEvent.Action.MEMBERSHIP_ADD
    )
    assert event.changes["proprietaires"]["to"] == str(person)


# --- AuditLogListView ------------------------------------------------------


@pytest.mark.django_db
def test_audit_log_requires_login(client):
    response = client.get(reverse("audit-log-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_audit_log_requires_staff(auth_client):
    response = auth_client.get(reverse("audit-log-list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_audit_log_staff_sees_events(staff_client, person):
    response = staff_client.get(reverse("audit-log-list"))
    assert response.status_code == 200
    assert str(person) in response.content.decode()
