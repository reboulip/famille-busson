import io

import pytest
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
from genealogy.models import Source, Story
from photos.models import Album, Photo


@pytest.fixture(autouse=True)
def use_tmp_photos_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.DOCUMENTS_ROOT = tmp_path / "documents_data"
    settings.PHOTOS_ROOT = tmp_path / "documents_data" / "photos"


def _real_image_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def album(db):
    return Album.objects.create(title="Été 2025")


@pytest.fixture
def photo(db, album):
    return Photo.objects.create(
        album=album, file=SimpleUploadedFile(name="photo.png", content=_real_image_bytes(), content_type="image/png")
    )


@pytest.fixture
def story(db, person):
    return Story.objects.create(person=person, title="Le voyage en Bretagne", body="Un été mémorable.")


@pytest.fixture
def source(db):
    return Source.objects.create(title="Acte de naissance", kind="acte_civil")
