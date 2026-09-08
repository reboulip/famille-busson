import pytest
from django.urls import reverse

from annuaire.models import Person


@pytest.mark.django_db
def test_duplicate_list_requires_staff(auth_client):
    response = auth_client.get(reverse("person-duplicate-list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_duplicate_list_requires_login(client):
    response = client.get(reverse("person-duplicate-list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_duplicate_list_shows_candidates(staff_client, person):
    Person.objects.create(first_name=person.first_name, last_name=person.last_name)
    response = staff_client.get(reverse("person-duplicate-list"))
    assert response.status_code == 200
    assert person.first_name in response.content.decode()


@pytest.mark.django_db
def test_merge_view_requires_staff(auth_client, person, accountless_person):
    response = auth_client.get(reverse("person-merge", args=[person.pk, accountless_person.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_merge_view_get_200(staff_client, person, accountless_person):
    response = staff_client.get(reverse("person-merge", args=[person.pk, accountless_person.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_merge_view_get_shows_differing_fields(staff_client, person, accountless_person):
    accountless_person.phone_number = "0600000000"
    accountless_person.save()
    response = staff_client.get(reverse("person-merge", args=[person.pk, accountless_person.pk]))
    assert "0600000000" in response.content.decode()


@pytest.mark.django_db
def test_merge_view_post_merges_and_redirects(staff_client, person, accountless_person):
    response = staff_client.post(reverse("person-merge", args=[person.pk, accountless_person.pk]))
    assert response.status_code == 302
    assert response.url == reverse("personne-detail", kwargs={"pk": person.pk})
    assert not Person.objects.filter(pk=accountless_person.pk).exists()


@pytest.mark.django_db
def test_merge_view_post_respects_field_choice(staff_client, person, accountless_person):
    person.phone_number = "0611111111"
    person.save()
    accountless_person.phone_number = "0622222222"
    accountless_person.save()
    staff_client.post(
        reverse("person-merge", args=[person.pk, accountless_person.pk]),
        {"choice_phone_number": "2"},
    )
    person.refresh_from_db()
    assert person.phone_number == "0622222222"


@pytest.mark.django_db
def test_merge_view_post_refuses_when_both_have_accounts(staff_client, person, other_person):
    response = staff_client.post(reverse("person-merge", args=[person.pk, other_person.pk]))
    assert response.status_code == 302
    assert Person.objects.filter(pk=other_person.pk).exists()
