import pytest
from django.urls import reverse

from photos.models import Album, Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_album_detail_requires_login(client, album):
    response = client.get(reverse("album-detail", kwargs={"pk": album.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_album_detail_shows_photos(auth_client, album, photo):
    response = auth_client.get(reverse("album-detail", kwargs={"pk": album.pk}))
    assert response.status_code == 200
    assert list(response.context["photos"]) == [photo]


@pytest.mark.django_db
def test_album_detail_locked_hides_photos(auth_client, restricted_album):
    Photo.objects.create(album=restricted_album, file=make_uploaded_image())
    response = auth_client.get(reverse("album-detail", kwargs={"pk": restricted_album.pk}))
    assert response.status_code == 200
    assert response.context["can_access"] is False
    assert list(response.context["photos"]) == []
    assert "Cet album est réservé" in response.content.decode()


@pytest.mark.django_db
def test_album_detail_member_sees_restricted_photos(auth_client, account, restricted_album, group):
    account.groups.add(group)
    photo = Photo.objects.create(album=restricted_album, file=make_uploaded_image())
    response = auth_client.get(reverse("album-detail", kwargs={"pk": restricted_album.pk}))
    assert list(response.context["photos"]) == [photo]


@pytest.mark.django_db
def test_album_detail_paginates(auth_client, album):
    for _ in range(30):
        Photo.objects.create(album=album, file=make_uploaded_image())
    response = auth_client.get(reverse("album-detail", kwargs={"pk": album.pk}))
    assert response.context["is_paginated"] is True
    assert len(response.context["photos"]) == 24


@pytest.mark.django_db
def test_album_detail_can_edit_true_for_creator(auth_client, album, person):
    album.created_by = person
    album.save()
    response = auth_client.get(reverse("album-detail", kwargs={"pk": album.pk}))
    assert response.context["can_edit"] is True


@pytest.mark.django_db
def test_album_detail_can_edit_false_for_non_creator(auth_client, album):
    response = auth_client.get(reverse("album-detail", kwargs={"pk": album.pk}))
    assert response.context["can_edit"] is False


@pytest.mark.django_db
def test_album_create_redirects_to_detail(auth_client, person):
    response = auth_client.post(reverse("album-create"), {"title": "Nouvel album", "description": "", "groups": []})
    album = Album.objects.get(title="Nouvel album")
    assert response.url == reverse("album-detail", kwargs={"pk": album.pk})
