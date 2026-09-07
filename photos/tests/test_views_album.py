import pytest
from django.urls import reverse

from photos.models import Album, Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_album_list_requires_login(client, album):
    response = client.get(reverse("album-list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_album_list_shows_public_album(auth_client, album):
    response = auth_client.get(reverse("album-list"))
    assert response.status_code == 200
    assert album.title in response.content.decode()


@pytest.mark.django_db
def test_album_list_shows_locked_album_name_but_not_as_link(auth_client, restricted_album):
    response = auth_client.get(reverse("album-list"))
    content = response.content.decode()
    assert restricted_album.title in content
    assert "fb-chip--lock" in content


@pytest.mark.django_db
def test_album_create_requires_profile(client, account):
    client.force_login(account)
    response = client.post(reverse("album-create"), {"title": "Nouvel album", "description": "", "groups": []})
    assert response.status_code == 302
    assert response.url == reverse("profile-create")


@pytest.mark.django_db
def test_album_create_sets_created_by(auth_client, person):
    response = auth_client.post(reverse("album-create"), {"title": "Nouvel album", "description": "", "groups": []})
    assert response.status_code == 302
    album = Album.objects.get(title="Nouvel album")
    assert album.created_by_id == person.pk


@pytest.mark.django_db
def test_album_edit_by_non_creator_is_forbidden(auth_client, album, person):
    album.created_by = None
    album.save()
    response = auth_client.post(
        reverse("album-edit", kwargs={"pk": album.pk}),
        {"title": "Modifié", "description": "", "groups": []},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_album_edit_by_creator_succeeds(auth_client, album, person):
    album.created_by = person
    album.save()
    response = auth_client.post(
        reverse("album-edit", kwargs={"pk": album.pk}),
        {"title": "Modifié", "description": "", "groups": []},
    )
    assert response.status_code == 302
    album.refresh_from_db()
    assert album.title == "Modifié"


@pytest.mark.django_db
def test_album_edit_by_staff_succeeds(staff_client, album):
    response = staff_client.post(
        reverse("album-edit", kwargs={"pk": album.pk}),
        {"title": "Modifié", "description": "", "groups": []},
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_album_delete_shows_photo_count(staff_client, album):
    Photo.objects.create(album=album, file=make_uploaded_image())
    response = staff_client.get(reverse("album-delete", kwargs={"pk": album.pk}))
    assert response.context["photo_count"] == 1


@pytest.mark.django_db
def test_album_delete_cascades_photos(staff_client, album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    response = staff_client.post(reverse("album-delete", kwargs={"pk": album.pk}))
    assert response.status_code == 302
    assert not Album.objects.filter(pk=album.pk).exists()
    assert not Photo.objects.filter(pk=photo.pk).exists()
