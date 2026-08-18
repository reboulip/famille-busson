import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

LOGIN_URL = "/annuaire/login/"


@pytest.fixture(autouse=True)
def use_tmp_media(tmp_path, settings):
    """Redirect file uploads to a temp directory so tests don't pollute MEDIA_ROOT."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def person_with_photo(person):
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    person.profile_photo = SimpleUploadedFile("photo.png", buf.getvalue(), content_type="image/png")
    person.save()
    return person


@pytest.mark.django_db
def test_media_requires_login(client, person_with_photo):
    response = client.get(person_with_photo.profile_photo.url)
    assert response.status_code == 302
    assert LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_media_accessible_when_authenticated(auth_client, person_with_photo):
    response = auth_client.get(person_with_photo.profile_photo.url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_media_returns_404_for_missing_file(auth_client):
    response = auth_client.get("/media/photos/does-not-exist.png")
    assert response.status_code == 404
