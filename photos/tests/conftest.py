import io

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from annuaire.tests.conftest import (  # noqa: F401 -- re-exported as fixtures
    account,
    auth_client,
    client,
    other_account,
    other_person,
    person,
    staff_account,
    staff_client,
)
from photos.models import Album, Photo


@pytest.fixture(autouse=True)
def use_tmp_photos_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.DOCUMENTS_ROOT = tmp_path / "documents_data"
    settings.PHOTOS_ROOT = tmp_path / "documents_data" / "photos"


def _real_image_bytes(fmt="PNG", size=(10, 10), color="blue"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format=fmt)
    return buffer.getvalue()


def make_uploaded_image(name="photo.png", fmt="PNG"):
    return SimpleUploadedFile(name=name, content=_real_image_bytes(fmt=fmt), content_type="image/png")


@pytest.fixture
def album(db):
    return Album.objects.create(title="Été 2025")


@pytest.fixture
def photo(db, album):
    return Photo.objects.create(album=album, file=make_uploaded_image())


@pytest.fixture
def group(db):
    return Group.objects.create(name="SCI grand chalet")


@pytest.fixture
def restricted_album(db, group):
    album = Album.objects.create(title="Album privé")
    album.groups.add(group)
    return album
