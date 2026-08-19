import io
import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from annuaire.models import Chalet, Person


@pytest.fixture(autouse=True)
def use_tmp_media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path


def _tiny_png(name="photo.png"):
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@pytest.mark.django_db
def test_person_delete_removes_profile_photo_file(django_capture_on_commit_callbacks):
    person = Person.objects.create(first_name="Alice", last_name="Busson", profile_photo=_tiny_png())
    file_path = person.profile_photo.path
    assert os.path.exists(file_path)

    with django_capture_on_commit_callbacks(execute=True):
        person.delete()

    assert not os.path.exists(file_path)


@pytest.mark.django_db
def test_person_replace_profile_photo_removes_old_file(django_capture_on_commit_callbacks):
    person = Person.objects.create(first_name="Alice", last_name="Busson", profile_photo=_tiny_png("old.png"))
    old_path = person.profile_photo.path
    assert os.path.exists(old_path)

    with django_capture_on_commit_callbacks(execute=True):
        person.profile_photo = _tiny_png("new.png")
        person.save()

    assert not os.path.exists(old_path)
    assert os.path.exists(person.profile_photo.path)


@pytest.mark.django_db
def test_person_clear_profile_photo_removes_file(django_capture_on_commit_callbacks):
    person = Person.objects.create(first_name="Alice", last_name="Busson", profile_photo=_tiny_png())
    old_path = person.profile_photo.path

    with django_capture_on_commit_callbacks(execute=True):
        person.profile_photo = None
        person.save()

    assert not os.path.exists(old_path)


@pytest.mark.django_db
def test_chalet_delete_removes_photo_file(django_capture_on_commit_callbacks):
    chalet = Chalet.objects.create(name="Le Grand Chalet", address="1 rue de la Montagne", photo=_tiny_png())
    file_path = chalet.photo.path
    assert os.path.exists(file_path)

    with django_capture_on_commit_callbacks(execute=True):
        chalet.delete()

    assert not os.path.exists(file_path)


@pytest.mark.django_db
def test_shared_filename_not_deleted_while_another_row_references_it(django_capture_on_commit_callbacks):
    photo = _tiny_png("shared.png")
    person1 = Person.objects.create(first_name="Alice", last_name="Busson", profile_photo=photo)
    shared_name = person1.profile_photo.name
    person2 = Person.objects.create(first_name="Bob", last_name="Busson")
    person2.profile_photo.name = shared_name
    person2.save(update_fields=["profile_photo"])

    file_path = person1.profile_photo.path
    assert os.path.exists(file_path)

    with django_capture_on_commit_callbacks(execute=True):
        person1.delete()

    # person2 still references the same file -- must survive.
    assert os.path.exists(file_path)


@pytest.mark.django_db
def test_missing_file_on_disk_does_not_raise(django_capture_on_commit_callbacks):
    person = Person.objects.create(first_name="Alice", last_name="Busson", profile_photo=_tiny_png())
    os.remove(person.profile_photo.path)

    with django_capture_on_commit_callbacks(execute=True):
        person.delete()  # must not raise even though the file is already gone
