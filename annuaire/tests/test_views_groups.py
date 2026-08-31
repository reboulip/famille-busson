import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

LOGIN_URL = "/annuaire/login/"


@pytest.fixture
def group(db):
    return Group.objects.create(name="SCI grand chalet")


# ---------------------------------------------------------------------------
# GroupListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_group_list_requires_login(client):
    response = client.get(reverse("group-list"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_group_list_requires_staff(auth_client):
    response = auth_client.get(reverse("group-list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_group_list_returns_200(staff_client):
    response = staff_client.get(reverse("group-list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_group_list_contains_group(staff_client, group):
    response = staff_client.get(reverse("group-list"))
    assert group.name in response.content.decode()


# ---------------------------------------------------------------------------
# GroupCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_group_create_requires_staff(auth_client):
    response = auth_client.get(reverse("group-create"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_group_create_get_returns_200(staff_client):
    response = staff_client.get(reverse("group-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_group_create_post_creates_group(staff_client, db):
    response = staff_client.post(reverse("group-create"), {"name": "Nouveau groupe"})
    assert response.status_code == 302
    assert Group.objects.filter(name="Nouveau groupe").exists()


# ---------------------------------------------------------------------------
# GroupUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_group_update_requires_staff(auth_client, group):
    response = auth_client.get(reverse("group-edit", kwargs={"pk": group.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_group_update_renames_group(staff_client, group):
    response = staff_client.post(reverse("group-edit", kwargs={"pk": group.pk}), {"name": "Nouveau nom"})
    assert response.status_code == 302
    group.refresh_from_db()
    assert group.name == "Nouveau nom"


# ---------------------------------------------------------------------------
# GroupDeleteView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_group_delete_requires_staff(auth_client, group):
    response = auth_client.get(reverse("group-delete", kwargs={"pk": group.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_group_delete_get_shows_member_count(staff_client, group, person):
    person.account.groups.add(group)
    response = staff_client.get(reverse("group-delete", kwargs={"pk": group.pk}))
    assert response.status_code == 200
    assert response.context["member_count"] == 1


@pytest.mark.django_db
def test_group_delete_post_deletes_group(staff_client, group):
    response = staff_client.post(reverse("group-delete", kwargs={"pk": group.pk}))
    assert response.status_code == 302
    assert not Group.objects.filter(pk=group.pk).exists()


# ---------------------------------------------------------------------------
# GroupMembersUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_group_members_requires_staff(auth_client, group):
    response = auth_client.get(reverse("group-members-edit", kwargs={"pk": group.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_group_members_get_returns_200(staff_client, group):
    response = staff_client.get(reverse("group-members-edit", kwargs={"pk": group.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_group_members_post_sets_members(staff_client, group, person, other_person):
    response = staff_client.post(
        reverse("group-members-edit", kwargs={"pk": group.pk}),
        {"members": [str(person.pk), str(other_person.pk)]},
    )
    assert response.status_code == 302
    assert set(group.account_set.all()) == {person.account, other_person.account}


@pytest.mark.django_db
def test_group_members_post_ignores_accountless_person(staff_client, group, accountless_person):
    response = staff_client.post(
        reverse("group-members-edit", kwargs={"pk": group.pk}),
        {"members": [str(accountless_person.pk)]},
    )
    assert response.status_code == 302
    assert group.account_set.count() == 0


@pytest.mark.django_db
def test_group_members_post_removes_existing_member(staff_client, group, person):
    person.account.groups.add(group)
    response = staff_client.post(reverse("group-members-edit", kwargs={"pk": group.pk}), {"members": []})
    assert response.status_code == 302
    assert group.account_set.count() == 0
