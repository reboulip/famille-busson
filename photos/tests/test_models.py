import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from photos.models import Album, AlbumGroupAccess, Photo

from .conftest import make_uploaded_image


@pytest.mark.django_db
def test_album_str_is_title():
    album = Album.objects.create(title="Été 2025")
    assert str(album) == "Été 2025"


@pytest.mark.django_db
def test_photo_str_is_caption_when_set(album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image(), caption="La plage")
    assert str(photo) == "La plage"


@pytest.mark.django_db
def test_photo_str_falls_back_to_filename(album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image(name="plage.png"))
    assert str(photo) == "plage.png"


@pytest.mark.django_db
def test_photo_default_derivative_status_is_pending(album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    assert photo.derivative_status == "pending"
    assert not photo.thumbnail
    assert not photo.web


@pytest.mark.django_db
def test_album_group_access_unique_constraint(album, group):
    AlbumGroupAccess.objects.create(album=album, group=group)
    with pytest.raises(IntegrityError):
        AlbumGroupAccess.objects.create(album=album, group=group)


@pytest.mark.django_db
def test_album_cover_from_another_album_is_rejected(album):
    other_album = Album.objects.create(title="Autre album")
    other_photo = Photo.objects.create(album=other_album, file=make_uploaded_image())
    album.cover = other_photo
    with pytest.raises(ValidationError):
        album.full_clean()


@pytest.mark.django_db
def test_album_cover_from_same_album_is_accepted(album):
    photo = Photo.objects.create(album=album, file=make_uploaded_image())
    album.cover = photo
    album.full_clean()  # does not raise
    album.save()
    assert album.cover_id == photo.pk


@pytest.mark.django_db
def test_photo_chronological_orders_taken_at_desc_nulls_last(album):
    from django.utils import timezone

    dated = Photo.objects.create(album=album, file=make_uploaded_image(), taken_at=timezone.now())
    undated = Photo.objects.create(album=album, file=make_uploaded_image())
    ordered = list(Photo.objects.chronological())
    assert ordered[0] == dated
    assert ordered[-1] == undated


@pytest.mark.django_db
def test_deleting_album_cascades_to_photos(album):
    Photo.objects.create(album=album, file=make_uploaded_image())
    album_pk = album.pk
    album.delete()
    assert not Photo.objects.filter(album_id=album_pk).exists()
