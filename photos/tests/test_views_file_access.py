import pytest
from django.urls import reverse

from photos.models import Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_photo_file_requires_login(client, photo):
    response = client.get(reverse("photo-file", kwargs={"pk": photo.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_photo_file_accessible_returns_200(auth_client, photo):
    response = auth_client.get(reverse("photo-file", kwargs={"pk": photo.pk}))
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, max-age=604800"
    assert response["X-Content-Type-Options"] == "nosniff"


@pytest.mark.django_db
def test_photo_file_restricted_album_is_forbidden(auth_client, restricted_album):
    photo = Photo.objects.create(album=restricted_album, file=make_uploaded_image())
    response = auth_client.get(reverse("photo-file", kwargs={"pk": photo.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_photo_file_restricted_album_accessible_to_member(auth_client, account, restricted_album, group):
    account.groups.add(group)
    photo = Photo.objects.create(album=restricted_album, file=make_uploaded_image())
    response = auth_client.get(reverse("photo-file", kwargs={"pk": photo.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_photo_web_variant_falls_back_to_original_when_absent(auth_client, photo):
    """Derivatives are generated asynchronously (10.3) -- until then, every
    variant must still serve something rather than 404."""
    response = auth_client.get(reverse("photo-file-web", kwargs={"pk": photo.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_photo_thumbnail_variant_falls_back_to_original_when_absent(auth_client, photo):
    response = auth_client.get(reverse("photo-file-thumbnail", kwargs={"pk": photo.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_photo_file_download_forces_attachment(auth_client, photo):
    response = auth_client.get(reverse("photo-file", kwargs={"pk": photo.pk}), {"download": "1"})
    assert response["Content-Disposition"].startswith("attachment")


@pytest.mark.django_db
def test_photo_file_inline_for_image_extension(auth_client, photo):
    response = auth_client.get(reverse("photo-file", kwargs={"pk": photo.pk}))
    assert response["Content-Disposition"].startswith("inline")
