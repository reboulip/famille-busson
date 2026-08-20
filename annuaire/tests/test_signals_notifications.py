import pytest

from annuaire.models import Person, Settings


@pytest.mark.django_db
def test_settings_auto_created_on_person_creation():
    person = Person.objects.create(first_name="Alice", last_name="Busson")
    assert Settings.objects.filter(person=person).exists()


@pytest.mark.django_db
def test_settings_defaults_are_opted_out():
    person = Person.objects.create(first_name="Alice", last_name="Busson")
    assert person.settings.notify_on_birthday is False
    assert person.settings.notify_on_new_blog_post is False


@pytest.mark.django_db
def test_settings_not_duplicated_on_person_update():
    person = Person.objects.create(first_name="Alice", last_name="Busson")
    person.first_name = "Alicia"
    person.save()
    assert Settings.objects.filter(person=person).count() == 1
