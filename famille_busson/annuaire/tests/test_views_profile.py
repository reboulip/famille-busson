import pytest
from django.urls import reverse
from annuaire.models import Person, Relation


LOGIN_URL = "/annuaire/login/"


# ---------------------------------------------------------------------------
# my_profile
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_my_profile_requires_login(client):
    response = client.get(reverse("my-profile"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_my_profile_redirects_to_person_detail(auth_client, person):
    response = auth_client.get(reverse("my-profile"))
    assert response.status_code == 302
    assert reverse("personne-detail", kwargs={"pk": person.pk}) in response["Location"]


@pytest.mark.django_db
def test_my_profile_no_profile_returns_no_profile_page(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("my-profile"))
    assert response.status_code == 200
    assert "annuaire/no_profile.html" in [t.name for t in response.templates]


# ---------------------------------------------------------------------------
# edit_my_profile
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_edit_my_profile_requires_login(client):
    response = client.get(reverse("edit-my-profile"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_edit_my_profile_redirects_to_person_edit(auth_client, person):
    response = auth_client.get(reverse("edit-my-profile"))
    assert response.status_code == 302
    assert reverse("person-edit", kwargs={"pk": person.pk}) in response["Location"]


@pytest.mark.django_db
def test_edit_my_profile_no_profile_returns_no_profile_page(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("edit-my-profile"))
    assert response.status_code == 200
    assert "annuaire/no_profile.html" in [t.name for t in response.templates]


# ---------------------------------------------------------------------------
# DirectoryListView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_directory_requires_login(client):
    response = client.get(reverse("directory"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_directory_returns_200(auth_client):
    response = auth_client.get(reverse("directory"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_directory_lists_all_persons(auth_client, person, other_person):
    response = auth_client.get(reverse("directory"))
    assert person in response.context["persons"]
    assert other_person in response.context["persons"]


@pytest.mark.django_db
def test_directory_search_filters_by_name(auth_client, person, other_person):
    response = auth_client.get(reverse("directory") + "?q=Alice")
    assert person in response.context["persons"]
    assert other_person not in response.context["persons"]


@pytest.mark.django_db
def test_directory_search_no_results(auth_client, person):
    response = auth_client.get(reverse("directory") + "?q=zzznomatch")
    assert list(response.context["persons"]) == []


# ---------------------------------------------------------------------------
# ProfileDetailView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_profile_detail_requires_login(client, person):
    response = client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_profile_detail_returns_200(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_detail_404_on_invalid_pk(auth_client):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_profile_detail_context_has_person(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.context["person"] == person


@pytest.mark.django_db
def test_profile_detail_shows_partner(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.context.get("partner") == other_person


@pytest.mark.django_db
def test_profile_detail_shows_parents(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert other_person in response.context["parents"]


@pytest.mark.django_db
def test_profile_detail_shows_children(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=3)
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert other_person in response.context["children"]


# ---------------------------------------------------------------------------
# ProfileUpdateView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_profile_update_requires_login(client, person):
    response = client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_profile_update_own_profile_get_200(auth_client, person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_update_other_profile_returns_403(auth_client, other_person):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": other_person.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_profile_update_invalid_pk_returns_404(auth_client):
    response = auth_client.get(reverse("person-edit", kwargs={"pk": 99999}))
    assert response.status_code == 404


def _empty_formset_data(prefix="ascending_relations"):
    """Return management form data for the RelationEditFormSet (prefix = related_name on person1 FK)."""
    return {
        f"{prefix}-TOTAL_FORMS": "0",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


@pytest.mark.django_db
def test_profile_update_post_valid_updates_person(auth_client, person):
    data = {"first_name": "Alicia", "last_name": "Busson"}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    person.refresh_from_db()
    assert person.first_name == "Alicia"


@pytest.mark.django_db
def test_profile_update_post_invalid_returns_200_with_errors(auth_client, person):
    data = {"first_name": "", "last_name": ""}
    data.update(_empty_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 200
