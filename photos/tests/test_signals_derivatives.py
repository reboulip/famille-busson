import pytest

from photos.models import Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_creating_a_photo_enqueues_derivative_generation(album, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        photo = Photo.objects.create(album=album, file=make_uploaded_image())

    photo.refresh_from_db()
    assert photo.derivative_status == "done"
    assert photo.thumbnail


@pytest.mark.django_db
def test_updating_a_photo_does_not_re_enqueue(album, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        photo = Photo.objects.create(album=album, file=make_uploaded_image())
    photo.refresh_from_db()
    generated_at = photo.derivatives_generated_at

    with django_capture_on_commit_callbacks(execute=True):
        photo.caption = "Légende mise à jour"
        photo.save()

    photo.refresh_from_db()
    assert photo.derivatives_generated_at == generated_at
