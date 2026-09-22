import pytest
from django.urls import reverse

LOGIN_URL = "/annuaire/login/"


@pytest.mark.django_db
def test_anonymise_requires_login(client, person):
    response = client.get(reverse("person-anonymise", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_anonymise_requires_staff(auth_client, other_person):
    response = auth_client.get(reverse("person-anonymise", kwargs={"pk": other_person.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_anonymise_get_returns_confirm_page(staff_client, person):
    response = staff_client.get(reverse("person-anonymise", kwargs={"pk": person.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_anonymise_post_anonymises_and_redirects(staff_client, person):
    response = staff_client.post(reverse("person-anonymise", kwargs={"pk": person.pk}))
    assert response.status_code == 302
    assert response["Location"] == reverse("personne-detail", kwargs={"pk": person.pk})
    person.refresh_from_db()
    assert person.anonymised_at is not None


@pytest.mark.django_db
def test_anonymise_post_twice_shows_error_message(staff_client, person):
    staff_client.post(reverse("person-anonymise", kwargs={"pk": person.pk}))
    response = staff_client.post(reverse("person-anonymise", kwargs={"pk": person.pk}), follow=True)
    page_messages = list(response.context["messages"])
    assert any("déjà" in str(m).lower() for m in page_messages)


@pytest.mark.django_db
def test_anonymise_button_hidden_for_non_staff(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert reverse("person-anonymise", kwargs={"pk": person.pk}) not in response.content.decode()


@pytest.mark.django_db
def test_anonymise_button_shown_for_staff(staff_client, person):
    response = staff_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert reverse("person-anonymise", kwargs={"pk": person.pk}) in response.content.decode()


@pytest.mark.django_db
def test_anonymise_button_hidden_once_already_anonymised(staff_client, person):
    from annuaire.anonymisation import anonymise_person

    anonymise_person(person, actor=None)
    response = staff_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert reverse("person-anonymise", kwargs={"pk": person.pk}) not in response.content.decode()
