"""13.2 — the AJAX photo picker backing the life-story form's "Photos" field."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_photo_search_requires_two_characters(auth_client):
    response = auth_client.get(reverse("photo-search-ajax"), {"q": "a"})
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_photo_search_returns_matching_photos(auth_client, photo):
    photo.caption = "Portrait de famille"
    photo.save()
    response = auth_client.get(reverse("photo-search-ajax"), {"q": "Portrait"})
    results = response.json()["results"]
    assert {"id": photo.pk, "name": "Portrait de famille"} in results


@pytest.mark.django_db
def test_photo_search_falls_back_to_filename_when_no_caption(auth_client, photo):
    response = auth_client.get(reverse("photo-search-ajax"), {"q": photo.filename[:4]})
    results = response.json()["results"]
    assert {"id": photo.pk, "name": photo.filename} in results


@pytest.mark.django_db
def test_photo_search_excludes_ids_in_the_exclude_param(auth_client, photo):
    photo.caption = "Portrait"
    photo.save()
    response = auth_client.get(reverse("photo-search-ajax"), {"q": "Portrait", "exclude": str(photo.pk)})
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_photo_search_hides_photos_in_restricted_albums(auth_client, group, album, photo):
    from photos.models import Album, Photo
    from photos.tests.conftest import make_uploaded_image

    photo.caption = "Album accessible"
    photo.save()
    restricted_album = Album.objects.create(title="Album restreint")
    restricted_album.groups.add(group)
    restricted = Photo.objects.create(album=restricted_album, file=make_uploaded_image(), caption="Album restreint")

    response = auth_client.get(reverse("photo-search-ajax"), {"q": "Album"})
    ids = {r["id"] for r in response.json()["results"]}
    assert photo.pk in ids
    assert restricted.pk not in ids


@pytest.mark.django_db
def test_photo_search_requires_login(client, photo):
    response = client.get(reverse("photo-search-ajax"), {"q": "photo"})
    assert response.status_code == 302
