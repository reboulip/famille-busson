import pytest

from photos.models import Photo
from photos.tasks import generate_photo_derivatives, process_pending_photos

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_generate_photo_derivatives_applies_result(album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    generate_photo_derivatives(photo.pk)
    photo.refresh_from_db()
    assert photo.derivative_status == "done"
    assert photo.thumbnail
    assert photo.web
    assert photo.derivatives_generated_at is not None


@pytest.mark.django_db
def test_generate_photo_derivatives_skips_deleted_photo():
    generate_photo_derivatives(999999)  # does not raise


@pytest.mark.django_db
def test_process_pending_photos_processes_only_pending(album):
    pending = Photo.objects.create(album=album, file=make_uploaded_image())
    already_done = Photo.objects.create(album=album, file=make_uploaded_image())
    already_done.derivative_status = "done"
    already_done.save()

    processed, error_count, error_messages = process_pending_photos()

    assert processed == 1
    assert error_count == 0
    assert error_messages == []
    pending.refresh_from_db()
    assert pending.derivative_status == "done"


@pytest.mark.django_db
def test_process_pending_photos_respects_limit(album):
    for _ in range(3):
        Photo.objects.create(album=album, file=make_uploaded_image())
    processed, _, _ = process_pending_photos(limit=2)
    assert processed == 2
