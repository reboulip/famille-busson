"""10.9 — the AJAX album picker backing the publication form's "Albums liés" field."""

import pytest
from django.urls import reverse

from photos.models import Album


@pytest.mark.django_db
def test_album_search_requires_two_characters(auth_client):
    response = auth_client.get(reverse("album-search-ajax"), {"q": "a"})
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_album_search_returns_matching_albums(auth_client, album):
    response = auth_client.get(reverse("album-search-ajax"), {"q": album.title[:4]})
    results = response.json()["results"]
    assert {"id": album.pk, "name": album.title} in results


@pytest.mark.django_db
def test_album_search_excludes_ids_in_the_exclude_param(auth_client, album):
    response = auth_client.get(reverse("album-search-ajax"), {"q": album.title[:4], "exclude": str(album.pk)})
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_album_search_hides_restricted_albums(auth_client, group):
    accessible = Album.objects.create(title="Album accessible")
    restricted = Album.objects.create(title="Album restreint")
    restricted.groups.add(group)
    response = auth_client.get(reverse("album-search-ajax"), {"q": "Album"})
    ids = {r["id"] for r in response.json()["results"]}
    assert accessible.pk in ids
    assert restricted.pk not in ids


@pytest.mark.django_db
def test_album_search_requires_login(client, album):
    response = client.get(reverse("album-search-ajax"), {"q": album.title[:4]})
    assert response.status_code == 302
