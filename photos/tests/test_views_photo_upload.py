import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from photos.models import Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_upload_requires_login(client, album):
    response = client.post(reverse("photo-upload", kwargs={"pk": album.pk}))
    assert response.status_code == 302


@pytest.mark.django_db
def test_upload_valid_file_creates_photo(auth_client, album, person):
    response = auth_client.post(
        reverse("photo-upload", kwargs={"pk": album.pk}), {"file": make_uploaded_image(name="nouvelle.png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "error" not in data
    photo = Photo.objects.get(pk=data["id"])
    assert photo.album_id == album.pk
    assert photo.uploaded_by_id == person.pk
    assert data["thumbnail_url"] == reverse("photo-file-thumbnail", kwargs={"pk": photo.pk})


@pytest.mark.django_db
def test_upload_invalid_extension_returns_json_error(auth_client, album):
    upload = SimpleUploadedFile("doc.pdf", b"%PDF-fake", content_type="application/pdf")
    response = auth_client.post(reverse("photo-upload", kwargs={"pk": album.pk}), {"file": upload})
    assert response.status_code == 400
    assert "error" in response.json()
    assert not Photo.objects.exists()


@pytest.mark.django_db
def test_upload_to_restricted_album_forbidden(auth_client, restricted_album):
    response = auth_client.post(
        reverse("photo-upload", kwargs={"pk": restricted_album.pk}), {"file": make_uploaded_image()}
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_upload_to_restricted_album_allowed_for_member(auth_client, account, restricted_album, group):
    account.groups.add(group)
    response = auth_client.post(
        reverse("photo-upload", kwargs={"pk": restricted_album.pk}), {"file": make_uploaded_image()}
    )
    assert response.status_code == 200
