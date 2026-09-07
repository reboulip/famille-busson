"""11.3 -- global search UI."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from annuaire.models import Person
from documents.models import Category, Document
from photos.models import Album

LOGIN_URL = "/annuaire/login/"


@pytest.fixture
def category(db):
    return Category.objects.create(name="Actes de famille")


@pytest.fixture
def restricted_group(db):
    return Group.objects.create(name="SCI grand chalet")


@pytest.fixture
def restricted_category(db, restricted_group):
    category = Category.objects.create(name="Réservé")
    category.groups.add(restricted_group)
    return category


@pytest.fixture
def restricted_album(db, restricted_group):
    album = Album.objects.create(title="Album privé")
    album.groups.add(restricted_group)
    return album


@pytest.mark.django_db
def test_search_requires_login(client):
    response = client.get(reverse("search"), {"q": "busson"})
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_query_under_min_length_shows_no_results(auth_client):
    response = auth_client.get(reverse("search"), {"q": "b"})
    assert response.context["groups"] == []
    assert response.context["expanded"] is None


@pytest.mark.django_db
def test_search_finds_matching_person(auth_client, person, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        person.save()

    response = auth_client.get(reverse("search"), {"q": "busson"})

    matched = [g for g in response.context["groups"] if g.label == "Personnes"][0]
    assert person in matched.results


@pytest.mark.django_db
def test_search_finds_accented_query_against_unaccented_name(auth_client, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        Person.objects.create(first_name="Alice", last_name="Büsson")

    response = auth_client.get(reverse("search"), {"q": "busson"})

    matched = [g for g in response.context["groups"] if g.label == "Personnes"][0]
    assert len(matched.results) == 1


@pytest.mark.django_db
def test_search_excludes_document_in_locked_category(
    auth_client, category, restricted_category, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        Document.objects.create(title="Acte public de Genève", category=category)
        Document.objects.create(title="Acte privé de Genève", category=restricted_category)

    response = auth_client.get(reverse("search"), {"q": "genève"})

    matched = [g for g in response.context["groups"] if g.label == "Documents"][0]
    titles = {d.title for d in matched.results}
    assert "Acte public de Genève" in titles
    assert "Acte privé de Genève" not in titles


@pytest.mark.django_db
def test_search_excludes_album_restricted_to_another_group(
    auth_client, restricted_album, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        Album.objects.create(title="Été à Genève public")
        restricted_album.title = "Été à Genève privé"
        restricted_album.save()

    response = auth_client.get(reverse("search"), {"q": "genève"})

    matched = [g for g in response.context["groups"] if g.label == "Albums"][0]
    titles = {a.title for a in matched.results}
    assert "Été à Genève public" in titles
    assert "Été à Genève privé" not in titles


@pytest.mark.django_db
def test_expand_type_paginates_full_results(auth_client, category, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        for i in range(25):
            Document.objects.create(title=f"Acte de Genève {i}", category=category)

    response = auth_client.get(reverse("search"), {"q": "genève", "type": "documents.document"})

    assert response.context["expanded"]["label"] == "Documents"
    assert response.context["expanded"]["page_obj"].paginator.count == 25
    assert len(response.context["expanded"]["page_obj"]) == 20


@pytest.mark.django_db
def test_home_page_still_renders_with_search_form(auth_client):
    response = auth_client.get(reverse("home"))
    assert response.status_code == 200
    assert 'name="q"' in response.content.decode()
