import pytest
from django.urls import reverse

from annuaire.models import Person

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_profile_claim_requires_login(client):
    response = client.get(reverse("profile-claim"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_profile_claim_redirects_if_profile_already_exists(auth_client, person):
    response = auth_client.get(reverse("profile-claim"))
    assert response.status_code == 302
    assert reverse("my-profile") in response["Location"]


@pytest.mark.django_db
def test_profile_claim_get_lists_only_accountless_persons(client, account, other_person, accountless_person):
    # `account` (alice) has no linked profile; `other_person` (bob) is linked to a
    # different account -- only the accountless one should be listed.
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("profile-claim"))
    assert response.status_code == 200
    assert list(response.context["persons"]) == [accountless_person]


@pytest.mark.django_db
def test_profile_claim_search_filters_by_name(client, account, accountless_person):
    Person.objects.create(first_name="Someone", last_name="Else")
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("profile-claim"), {"q": "Charlie"})
    assert list(response.context["persons"]) == [accountless_person]


@pytest.mark.django_db
def test_profile_claim_post_links_account_and_redirects(client, account, accountless_person):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(reverse("profile-claim"), {"person": accountless_person.pk})
    accountless_person.refresh_from_db()
    assert accountless_person.account_id == account.pk
    assert response.status_code == 302
    assert reverse("person-edit", kwargs={"pk": accountless_person.pk}) in response["Location"]


@pytest.mark.django_db
def test_profile_claim_post_already_claimed_person_fails_gracefully(client, account, other_person):
    # `account` (alice) has no profile; `other_person` (bob) is already linked to
    # a different account -- claiming him must fail without changing anything.
    original_account_id = other_person.account_id
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(reverse("profile-claim"), {"person": other_person.pk}, follow=True)
    other_person.refresh_from_db()
    assert other_person.account_id == original_account_id
    messages = list(response.context["messages"])
    assert any("plus disponible" in str(m) for m in messages)


@pytest.mark.django_db
def test_profile_claim_post_user_with_profile_redirects_without_claiming(auth_client, person, accountless_person):
    response = auth_client.post(reverse("profile-claim"), {"person": accountless_person.pk})
    accountless_person.refresh_from_db()
    assert accountless_person.account is None
    assert response.status_code == 302
    assert reverse("my-profile") in response["Location"]


@pytest.mark.django_db
def test_profile_claim_backfills_blank_email(client, account, accountless_person):
    assert not accountless_person.email
    client.login(username="alice@example.com", password="testpass123!")
    client.post(reverse("profile-claim"), {"person": accountless_person.pk})
    accountless_person.refresh_from_db()
    assert accountless_person.email == "alice@example.com"


@pytest.mark.django_db
def test_profile_claim_does_not_overwrite_existing_email(client, account, accountless_person):
    accountless_person.email = "curated@example.com"
    accountless_person.save()
    client.login(username="alice@example.com", password="testpass123!")
    client.post(reverse("profile-claim"), {"person": accountless_person.pk})
    accountless_person.refresh_from_db()
    assert accountless_person.email == "curated@example.com"


@pytest.mark.django_db
def test_profile_claim_clears_owners(client, other_account, person, owned_person):
    # `owned_person` is owned by `person` (alice); claim it as a *different*,
    # profileless account (bob's) so the claimer isn't blocked by already having
    # a profile.
    assert list(owned_person.owners.all()) == [person]
    client.login(username="bob@example.com", password="testpass123!")
    client.post(reverse("profile-claim"), {"person": owned_person.pk})
    owned_person.refresh_from_db()
    assert list(owned_person.owners.all()) == []


@pytest.mark.django_db
def test_profile_create_renders_claim_link(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("profile-create"))
    assert reverse("profile-claim") in response.content.decode()
