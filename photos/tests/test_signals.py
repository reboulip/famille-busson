import pytest

from photos.models import Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_replacing_file_resets_derivative_fields(album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    photo.thumbnail = make_uploaded_image(name="thumb.png")
    photo.derivative_status = "done"
    photo.save()

    photo.file = make_uploaded_image(name="replacement.png")
    photo.save()

    photo.refresh_from_db()
    assert photo.derivative_status == "pending"
    assert not photo.thumbnail
    assert not photo.web


@pytest.mark.django_db
def test_saving_without_changing_file_keeps_derivative_fields(album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    photo.thumbnail = make_uploaded_image(name="thumb.png")
    photo.derivative_status = "done"
    photo.save()

    photo.caption = "Légende mise à jour"
    photo.save()

    photo.refresh_from_db()
    assert photo.derivative_status == "done"
    assert photo.thumbnail
