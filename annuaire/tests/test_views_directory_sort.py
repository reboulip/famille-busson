import datetime

import pytest
from django.urls import reverse

from annuaire.models import Person


@pytest.mark.django_db
def test_directory_default_sort_is_most_recently_created_first(auth_client, person):
    second = Person.objects.create(first_name="Second", last_name="Busson")
    third = Person.objects.create(first_name="Third", last_name="Busson")
    response = auth_client.get(reverse("directory"))
    persons = list(response.context["persons"])
    assert persons.index(third) < persons.index(second) < persons.index(person)


@pytest.mark.django_db
def test_directory_sort_name_asc(auth_client, person, other_person):
    response = auth_client.get(reverse("directory"), {"sort": "name_asc"})
    persons = list(response.context["persons"])
    assert persons.index(person) < persons.index(other_person)


@pytest.mark.django_db
def test_directory_sort_name_desc(auth_client, person, other_person):
    response = auth_client.get(reverse("directory"), {"sort": "name_desc"})
    persons = list(response.context["persons"])
    assert persons.index(other_person) < persons.index(person)


@pytest.mark.django_db
def test_directory_sort_birth_date_asc_puts_null_birth_date_last(auth_client, person):
    with_date = Person.objects.create(first_name="Avec", last_name="Date", birth_date=datetime.date(1990, 1, 1))
    response = auth_client.get(reverse("directory"), {"sort": "birth_asc"})
    persons = list(response.context["persons"])
    assert persons.index(with_date) < persons.index(person)


@pytest.mark.django_db
def test_directory_sort_birth_date_desc_puts_null_birth_date_last(auth_client, person):
    with_date = Person.objects.create(first_name="Avec", last_name="Date", birth_date=datetime.date(1990, 1, 1))
    response = auth_client.get(reverse("directory"), {"sort": "birth_desc"})
    persons = list(response.context["persons"])
    assert persons.index(with_date) < persons.index(person)


@pytest.mark.django_db
def test_directory_sort_unknown_value_falls_back_to_default(auth_client):
    response = auth_client.get(reverse("directory"), {"sort": "bogus"})
    assert response.status_code == 200
    assert response.context["sort"] == "recent"


@pytest.mark.django_db
def test_directory_sort_context_reflects_selected_value(auth_client):
    response = auth_client.get(reverse("directory"), {"sort": "name_asc"})
    assert response.context["sort"] == "name_asc"


@pytest.mark.django_db
def test_directory_sort_combines_with_search_query(auth_client, person, other_person):
    response = auth_client.get(reverse("directory"), {"q": "Busson", "sort": "name_asc"})
    persons = list(response.context["persons"])
    assert person in persons
    assert other_person in persons
    assert persons.index(person) < persons.index(other_person)


@pytest.mark.django_db
def test_directory_sort_select_marks_current_option_selected(auth_client):
    response = auth_client.get(reverse("directory"), {"sort": "name_desc"})
    content = response.content.decode()
    assert 'value="name_desc" selected' in content
