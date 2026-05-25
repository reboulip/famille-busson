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
def test_my_profile_no_profile_redirects_to_create(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("my-profile"))
    assert response.status_code == 302
    assert reverse("profile-create") in response["Location"]


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
def test_edit_my_profile_no_profile_redirects_to_create(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("edit-my-profile"))
    assert response.status_code == 302
    assert reverse("profile-create") in response["Location"]


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


@pytest.mark.django_db
def test_profile_detail_can_edit_true_for_own_profile(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_profile_detail_can_edit_false_for_other_profile(auth_client, other_person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": other_person.pk}))
    assert response.context["can_edit"] is False


@pytest.mark.django_db
def test_profile_detail_can_edit_true_for_staff(staff_client, other_person):
    response = staff_client.get(reverse("personne-detail", kwargs={"pk": other_person.pk}))
    assert response.context["can_edit"] is True


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
def test_profile_update_staff_can_edit_any_profile(staff_client, other_person):
    response = staff_client.get(reverse("person-edit", kwargs={"pk": other_person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_update_staff_redirects_to_person_detail_after_save(staff_client, other_person):
    data = {"first_name": other_person.first_name, "last_name": other_person.last_name}
    data.update(_empty_formset_data())
    response = staff_client.post(reverse("person-edit", kwargs={"pk": other_person.pk}), data)
    assert response.status_code == 302
    assert reverse("personne-detail", kwargs={"pk": other_person.pk}) in response["Location"]


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


# ---------------------------------------------------------------------------
# ProfileCreateView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_profile_create_requires_login(client):
    response = client.get(reverse("profile-create"))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_profile_create_get_returns_200(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.get(reverse("profile-create"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_create_redirects_if_profile_exists(auth_client, person):
    response = auth_client.get(reverse("profile-create"))
    assert response.status_code == 302
    assert reverse("my-profile") in response["Location"]


@pytest.mark.django_db
def test_profile_create_post_creates_person_and_links_account(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(
        reverse("profile-create"),
        {"first_name": "Alice", "last_name": "Busson"},
    )
    assert response.status_code == 302
    from annuaire.models import Person
    person = Person.objects.get(account=account)
    assert person.first_name == "Alice"
    assert reverse("personne-detail", kwargs={"pk": person.pk}) in response["Location"]


@pytest.mark.django_db
def test_profile_create_post_invalid_returns_200_with_errors(client, account):
    client.login(username="alice@example.com", password="testpass123!")
    response = client.post(reverse("profile-create"), {"first_name": "", "last_name": ""})
    assert response.status_code == 200
    assert response.context["form"].errors


# ---------------------------------------------------------------------------
# PersonRelationsView (GET)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_person_relations_requires_login(client, person):
    response = client.get(reverse("person-relations-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_person_relations_forbidden_for_other_user(auth_client, other_person):
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": other_person.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_person_relations_allowed_for_owner(auth_client, person):
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_person_relations_allowed_for_staff(staff_client, person):
    response = staff_client.get(reverse("person-relations-edit", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_person_relations_404_for_invalid_pk(auth_client):
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": 99999}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_person_relations_lists_existing(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=1)
    response = auth_client.get(reverse("person-relations-edit", kwargs={"pk": person.pk}))
    row_forms = response.context["row_forms"]
    assert len(row_forms) == 1
    relation, _form = row_forms[0]
    assert relation.person2 == other_person


# ---------------------------------------------------------------------------
# AddRelationView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_add_relation_creates_relation_and_inverse(auth_client, person, other_person):
    response = auth_client.post(
        reverse("person-relation-add", kwargs={"pk": person.pk}),
        {"person2": other_person.pk, "relationship_type": 2},
    )
    assert response.status_code == 302
    assert Relation.objects.filter(person1=person, person2=other_person, relationship_type=2).exists()
    # inverse: parent -> enfant
    assert Relation.objects.filter(person1=other_person, person2=person, relationship_type=3).exists()


@pytest.mark.django_db
def test_add_relation_rejects_self(auth_client, person):
    response = auth_client.post(
        reverse("person-relation-add", kwargs={"pk": person.pk}),
        {"person2": person.pk, "relationship_type": 2},
    )
    assert response.status_code == 302
    assert not Relation.objects.filter(person1=person).exists()


@pytest.mark.django_db
def test_add_relation_rejects_duplicate(auth_client, person, other_person):
    Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-add", kwargs={"pk": person.pk}),
        {"person2": other_person.pk, "relationship_type": 1},
    )
    assert response.status_code == 302
    assert Relation.objects.filter(person1=person, person2=other_person).count() == 1


@pytest.mark.django_db
def test_add_relation_forbidden_for_other_user(auth_client, other_person, person):
    response = auth_client.post(
        reverse("person-relation-add", kwargs={"pk": other_person.pk}),
        {"person2": person.pk, "relationship_type": 2},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# UpdateRelationView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_update_relation_changes_type(auth_client, person, other_person):
    relation = Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-update", kwargs={"pk": person.pk, "rid": relation.pk}),
        {f"rel-{relation.pk}-relationship_type": "3", f"rel-{relation.pk}-start_date": ""},
    )
    assert response.status_code == 302
    relation.refresh_from_db()
    assert relation.relationship_type == 3


@pytest.mark.django_db
def test_update_relation_404_for_other_person_relation(auth_client, person, other_person):
    foreign = Person.objects.create(first_name="Foreign", last_name="Person")
    relation = Relation.objects.create(person1=other_person, person2=foreign, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-update", kwargs={"pk": person.pk, "rid": relation.pk}),
        {f"rel-{relation.pk}-relationship_type": "3"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DeleteRelationView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_delete_relation_removes_both_sides(auth_client, person, other_person):
    relation = Relation.objects.create(person1=person, person2=other_person, relationship_type=2)
    inverse = Relation.objects.get(person1=other_person, person2=person)
    response = auth_client.post(
        reverse("person-relation-delete", kwargs={"pk": person.pk, "rid": relation.pk}),
    )
    assert response.status_code == 302
    assert not Relation.objects.filter(pk=relation.pk).exists()
    assert not Relation.objects.filter(pk=inverse.pk).exists()


@pytest.mark.django_db
def test_delete_relation_forbidden_for_other_user(auth_client, other_person, person):
    relation = Relation.objects.create(person1=other_person, person2=person, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-delete", kwargs={"pk": other_person.pk, "rid": relation.pk}),
    )
    assert response.status_code == 403
    assert Relation.objects.filter(pk=relation.pk).exists()


@pytest.mark.django_db
def test_delete_relation_404_for_other_person_relation(auth_client, person, other_person):
    foreign = Person.objects.create(first_name="Foreign", last_name="Person")
    relation = Relation.objects.create(person1=other_person, person2=foreign, relationship_type=2)
    response = auth_client.post(
        reverse("person-relation-delete", kwargs={"pk": person.pk, "rid": relation.pk}),
    )
    assert response.status_code == 404
