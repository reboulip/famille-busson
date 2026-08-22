import pytest
from django.urls import reverse

from annuaire.models import Account, Person
from annuaire.views import can_edit_person

LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# can_edit_person()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_can_edit_person_true_for_own_profile(account, person):
    assert can_edit_person(account, person) is True


@pytest.mark.django_db
def test_can_edit_person_false_for_unrelated_user(account, other_person):
    assert can_edit_person(account, other_person) is False


@pytest.mark.django_db
def test_can_edit_person_true_for_staff(staff_account, other_person):
    assert can_edit_person(staff_account, other_person) is True


@pytest.mark.django_db
def test_can_edit_person_true_for_owner_of_accountless_profile(account, person, owned_person):
    assert can_edit_person(account, owned_person) is True


@pytest.mark.django_db
def test_can_edit_person_false_once_owned_profile_has_account(account, owned_person, other_account):
    owned_person.account = other_account
    owned_person.save()
    assert can_edit_person(account, owned_person) is False


# ---------------------------------------------------------------------------
# PersonCreateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_person_create_requires_login(client):
    response = client.get(reverse("person-create"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_person_create_get_returns_200(auth_client):
    response = auth_client.get(reverse("person-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_person_create_requires_own_profile(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("person-create"))
    assert response.status_code == 302
    assert reverse("profile-create") in response["Location"]


@pytest.mark.django_db
def test_person_create_post_creates_accountless_person_owned_by_creator(auth_client, person):
    response = auth_client.post(
        reverse("person-create"),
        {"first_name": "Charlie", "last_name": "Busson"},
    )
    new_person = Person.objects.get(first_name="Charlie", last_name="Busson")
    assert new_person.account is None
    assert list(new_person.owners.all()) == [person]
    assert response.status_code == 302
    assert reverse("person-relations-edit", kwargs={"pk": new_person.pk}) in response["Location"]


# ---------------------------------------------------------------------------
# PersonOwnersUpdateView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_person_owners_requires_login(client, owned_person):
    response = client.get(reverse("person-owners-edit", kwargs={"pk": owned_person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_person_owners_forbidden_for_non_owner(client, other_account, owned_person):
    client.login(username="bob@example.com", password="testpass123!")
    response = client.get(reverse("person-owners-edit", kwargs={"pk": owned_person.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_person_owners_allowed_for_owner(auth_client, owned_person):
    response = auth_client.get(reverse("person-owners-edit", kwargs={"pk": owned_person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_person_owners_allowed_for_staff(staff_client, owned_person):
    response = staff_client.get(reverse("person-owners-edit", kwargs={"pk": owned_person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_person_owners_forbidden_once_profile_has_account(auth_client, owned_person, other_account):
    owned_person.account = other_account
    owned_person.save()
    response = auth_client.get(reverse("person-owners-edit", kwargs={"pk": owned_person.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_person_owners_post_sets_owners_and_redirects(auth_client, person, other_person, owned_person):
    response = auth_client.post(
        reverse("person-owners-edit", kwargs={"pk": owned_person.pk}),
        {"owners": [other_person.pk]},
    )
    owned_person.refresh_from_db()
    assert list(owned_person.owners.all()) == [other_person]
    assert response.status_code == 302
    assert reverse("personne-detail", kwargs={"pk": owned_person.pk}) in response["Location"]


@pytest.mark.django_db
def test_person_owners_post_excludes_accountless_persons(auth_client, person, accountless_person, owned_person):
    # accountless_person has no Account -- can't log in, so "owning" through it is
    # meaningless and must be silently filtered out rather than accepted.
    response = auth_client.post(
        reverse("person-owners-edit", kwargs={"pk": owned_person.pk}),
        {"owners": [accountless_person.pk]},
    )
    owned_person.refresh_from_db()
    assert list(owned_person.owners.all()) == []
    assert response.status_code == 302


# ---------------------------------------------------------------------------
# ProfileDetailView.can_edit / ProfileUpdateView / relations editing for owners
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_detail_can_edit_true_for_owner(auth_client, owned_person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": owned_person.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_person_edit_allowed_for_owner(auth_client, owned_person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": owned_person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_person_relations_allowed_for_owner_of_accountless_profile(auth_client, owned_person):
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": owned_person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_privilege_escalation_owner_loses_access_once_person_gets_account(auth_client, owned_person, other_account):
    # Baseline: owner can edit while the profile is accountless.
    assert auth_client.get(reverse("person-edit", kwargs={"pk": owned_person.pk})).status_code == 200

    owned_person.account = other_account
    owned_person.save()

    detail_response = auth_client.get(reverse("personne-detail", kwargs={"pk": owned_person.pk}))
    assert detail_response.context["can_edit"] is False

    for url_name in ("person-edit", "person-relations-edit", "person-owners-edit"):
        response = auth_client.get(reverse(url_name, kwargs={"pk": owned_person.pk}))
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# link_account_to_person signal hardening
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_account_creation_links_only_one_of_several_matching_accountless_persons(db):
    # Person.email is not unique -- two distinct, still-accountless Person rows
    # sharing the same email must not raise MultipleObjectsReturned when an
    # Account for that email is created; exactly one (the oldest by pk) is linked.
    first = Person.objects.create(first_name="Foo", last_name="Busson", email="shared@example.com")
    second = Person.objects.create(first_name="Bar", last_name="Busson", email="shared@example.com")
    new_account = Account.objects.create_user(email="shared@example.com", password="testpass123!")
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.account_id == new_account.pk
    assert second.account_id is None


@pytest.mark.django_db
def test_account_creation_clears_owners_of_newly_linked_person(owned_person):
    owned_person.email = "charlie@example.com"
    owned_person.save()

    new_account = Account.objects.create_user(email="charlie@example.com", password="testpass123!")
    owned_person.refresh_from_db()
    assert owned_person.account_id == new_account.pk
    assert list(owned_person.owners.all()) == []
