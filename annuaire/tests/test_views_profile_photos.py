"""10.8 — the ?tab=photos query-param tab on the profile page."""

import io

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from photos.models import Album, PersonTag, Photo


def _uploaded_image(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name=name, content=buffer.getvalue(), content_type="image/png")


@pytest.fixture
def album(db):
    return Album.objects.create(title="Album de test")


@pytest.fixture
def restricted_album(db):
    group = Group.objects.create(name="SCI grand chalet")
    album = Album.objects.create(title="Album privé")
    album.groups.add(group)
    return album


@pytest.mark.django_db
def test_default_tab_shows_relations_not_photos(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.context["tab"] == ""
    assert "photos_page" not in response.context


@pytest.mark.django_db
def test_photos_tab_shows_tagged_photos(auth_client, person, album):
    photo = Photo.objects.create(album=album, file=_uploaded_image())
    PersonTag.objects.create(photo=photo, person=person)

    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}), {"tab": "photos"})
    assert response.context["tab"] == "photos"
    assert photo in list(response.context["photos_page"])


@pytest.mark.django_db
def test_photos_tab_shows_photo_count(auth_client, person, album):
    photo = Photo.objects.create(album=album, file=_uploaded_image())
    PersonTag.objects.create(photo=photo, person=person)

    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}))
    assert response.context["photo_count"] == 1


@pytest.mark.django_db
def test_photos_tab_hides_photos_in_restricted_album(auth_client, person, restricted_album):
    photo = Photo.objects.create(album=restricted_album, file=_uploaded_image())
    PersonTag.objects.create(photo=photo, person=person)

    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}), {"tab": "photos"})
    assert photo not in list(response.context["photos_page"])
    assert response.context["photo_count"] == 0


@pytest.mark.django_db
def test_photos_tab_shows_photos_in_restricted_album_for_member(auth_client, account, person, restricted_album):
    account.groups.add(restricted_album.groups.first())
    photo = Photo.objects.create(album=restricted_album, file=_uploaded_image())
    PersonTag.objects.create(photo=photo, person=person)

    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}), {"tab": "photos"})
    assert photo in list(response.context["photos_page"])


@pytest.mark.django_db
def test_photos_tab_only_shows_photos_tagged_with_this_person(auth_client, person, other_person, album):
    own_photo = Photo.objects.create(album=album, file=_uploaded_image())
    PersonTag.objects.create(photo=own_photo, person=person)
    other_photo = Photo.objects.create(album=album, file=_uploaded_image())
    PersonTag.objects.create(photo=other_photo, person=other_person)

    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}), {"tab": "photos"})
    photos = list(response.context["photos_page"])
    assert own_photo in photos
    assert other_photo not in photos


@pytest.mark.django_db
def test_photos_tab_paginates_at_24(auth_client, person, album):
    for _ in range(30):
        photo = Photo.objects.create(album=album, file=_uploaded_image())
        PersonTag.objects.create(photo=photo, person=person)

    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}), {"tab": "photos"})
    assert len(response.context["photos_page"]) == 24


@pytest.mark.django_db
def test_photos_tab_empty_state(auth_client, person):
    response = auth_client.get(reverse("personne-detail", kwargs={"pk": person.pk}), {"tab": "photos"})
    assert "Aucune photo" in response.content.decode()
