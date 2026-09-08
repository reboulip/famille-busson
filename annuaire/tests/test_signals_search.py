"""11.2 -- Person's signal-driven search reindexing."""

import pytest

from annuaire.models import Person


@pytest.mark.django_db
def test_creating_a_person_populates_search_text(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        person = Person.objects.create(first_name="Alice", last_name="Busson", description="Vit à Genève")

    person.refresh_from_db()
    assert "alice" in person.search_text
    assert "busson" in person.search_text
    assert "geneve" in person.search_text


@pytest.mark.django_db
def test_saving_with_unrelated_update_fields_does_not_reindex(person, django_capture_on_commit_callbacks):
    Person.objects.filter(pk=person.pk).update(search_text="")

    with django_capture_on_commit_callbacks(execute=True):
        person.birth_date = None
        person.save(update_fields=["birth_date"])

    person.refresh_from_db()
    assert person.search_text == ""


@pytest.mark.django_db
def test_saving_with_a_source_field_in_update_fields_reindexes(person, django_capture_on_commit_callbacks):
    Person.objects.filter(pk=person.pk).update(search_text="")

    with django_capture_on_commit_callbacks(execute=True):
        person.first_name = "Alicia"
        person.save(update_fields=["first_name"])

    person.refresh_from_db()
    assert "alicia" in person.search_text
