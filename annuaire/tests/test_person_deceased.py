import datetime

import pytest
from django.urls import reverse

from annuaire.forms import ProfileEditForm
from annuaire.models import Person

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_person_deceased_defaults_to_false(person):
    assert person.deceased is False
    assert person.death_date is None


# ---------------------------------------------------------------------------
# ProfileEditForm -- staff-only field gating
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_edit_form_pops_deceased_fields_for_non_staff_user(person, account):
    form = ProfileEditForm(instance=person, user=account)
    assert "deceased" not in form.fields
    assert "death_date" not in form.fields


@pytest.mark.django_db
def test_profile_edit_form_keeps_deceased_fields_for_staff_user(person, staff_account):
    form = ProfileEditForm(instance=person, user=staff_account)
    assert "deceased" in form.fields
    assert "death_date" in form.fields


@pytest.mark.django_db
def test_profile_edit_form_non_staff_post_cannot_smuggle_deceased(person, account):
    data = {
        "first_name": person.first_name,
        "last_name": person.last_name,
        "deceased": "on",
        "death_date": "2020-01-01",
    }
    form = ProfileEditForm(data, instance=person, user=account)
    assert form.is_valid(), form.errors
    saved = form.save()
    assert saved.deceased is False
    assert saved.death_date is None


@pytest.mark.django_db
def test_profile_edit_form_clean_forces_deceased_true_when_death_date_set(person, staff_account):
    data = {
        "first_name": person.first_name,
        "last_name": person.last_name,
        "death_date": "2020-01-01",
    }
    form = ProfileEditForm(data, instance=person, user=staff_account)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["deceased"] is True


# ---------------------------------------------------------------------------
# ProfileUpdateView / PersonCreateView -- end-to-end staff gating
# ---------------------------------------------------------------------------


def _empty_relations_formset_data(prefix="ascending_relations"):
    return {
        f"{prefix}-TOTAL_FORMS": "0",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


@pytest.mark.django_db
def test_profile_update_non_staff_post_cannot_set_deceased(auth_client, person):
    data = {"first_name": person.first_name, "last_name": person.last_name, "deceased": "on"}
    data.update(_empty_relations_formset_data())
    response = auth_client.post(reverse("person-edit", kwargs={"pk": person.pk}), data)
    assert response.status_code == 302
    person.refresh_from_db()
    assert person.deceased is False


@pytest.mark.django_db
def test_profile_update_staff_post_can_set_deceased(staff_client, other_person):
    data = {
        "first_name": other_person.first_name,
        "last_name": other_person.last_name,
        "deceased": "on",
        "death_date": "2020-01-01",
    }
    data.update(_empty_relations_formset_data())
    response = staff_client.post(reverse("person-edit", kwargs={"pk": other_person.pk}), data)
    assert response.status_code == 302
    other_person.refresh_from_db()
    assert other_person.deceased is True
    assert other_person.death_date == datetime.date(2020, 1, 1)


@pytest.mark.django_db
def test_person_create_non_staff_post_cannot_set_deceased(auth_client, db):
    data = {"first_name": "Grand", "last_name": "Parent", "deceased": "on"}
    response = auth_client.post(reverse("person-create"), data)
    assert response.status_code == 302
    created = Person.objects.get(first_name="Grand", last_name="Parent")
    assert created.deceased is False


# ---------------------------------------------------------------------------
# MapListView -- "profils sans adresse géolocalisée" count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_map_unresolved_count_excludes_deceased_person(auth_client, person, other_person):
    other_person.deceased = True
    other_person.save()
    response = auth_client.get(reverse("carte"))
    assert other_person not in response.context["unresolved_persons"]
    assert person in response.context["unresolved_persons"]
    assert response.context["unresolved_count"] == 1


# ---------------------------------------------------------------------------
# Template rendering -- annuaire list, profile detail
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_annuaire_list_marks_deceased_photo(auth_client, person):
    person.deceased = True
    person.save()
    response = auth_client.get(reverse("directory"))
    assert "person-photo--deceased" in response.content.decode()


@pytest.mark.django_db
def test_annuaire_list_does_not_mark_living_photo(auth_client, person):
    response = auth_client.get(reverse("directory"))
    assert "person-photo--deceased" not in response.content.decode()


@pytest.mark.django_db
def test_personne_detail_shows_deceased_class_and_date(auth_client, person):
    person.deceased = True
    person.death_date = datetime.date(2020, 1, 1)
    person.save()
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert "person-photo--deceased" in content
    assert "1 janvier 2020" in content


@pytest.mark.django_db
def test_personne_detail_shows_deceased_without_date(auth_client, person):
    person.deceased = True
    person.save()
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert "Décédé" in response.content.decode()


@pytest.mark.django_db
def test_personne_detail_hides_deceased_markers_when_alive(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    content = response.content.decode()
    assert "person-photo--deceased" not in content
    assert "Décédé" not in content
